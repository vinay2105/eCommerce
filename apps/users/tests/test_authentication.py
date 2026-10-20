from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.template.loader import get_template
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

User = get_user_model()


class AuthenticationBoundaryTests(SimpleTestCase):
    def test_me_rejects_anonymous_requests(self):
        client = APIClient(enforce_csrf_checks=True)
        response = client.get("/api/v1/auth/me/", HTTP_HOST="localhost")
        self.assertEqual(response.status_code, 403)

    def test_login_requires_a_csrf_token(self):
        client = APIClient(enforce_csrf_checks=True)
        response = client.post(
            "/api/v1/auth/login/",
            {"email": "person@example.com", "password": "password"},
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(response.status_code, 403)

    def test_authentication_throttle_rates_are_configured(self):
        rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
        self.assertEqual(rates["login"], "10/hour")
        self.assertEqual(rates["registration"], "10/hour")
        self.assertEqual(rates["password_reset"], "5/hour")

    def test_password_reset_email_templates_are_available(self):
        get_template("registration/password_reset_email.txt")
        get_template("registration/password_reset_subject.txt")


@override_settings(
    MAILERS={"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}}
)
class AuthenticationAPITests(TestCase):
    password = "Sensible-Phase1-Password-984!"

    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)

    def csrf_headers(self):
        response = self.client.get("/api/v1/auth/csrf/", HTTP_HOST="localhost")
        self.assertEqual(response.status_code, 200)
        return {"HTTP_X_CSRFTOKEN": self.client.cookies["csrftoken"].value}

    def register(self, email="person@example.com", password=None, **extra):
        headers = self.csrf_headers()
        return self.client.post(
            "/api/v1/auth/register/",
            {
                "email": email,
                "password": password or self.password,
                **extra,
            },
            format="json",
            HTTP_HOST="localhost",
            **headers,
        )

    def login(self, email="person@example.com", password=None):
        headers = self.csrf_headers()
        return self.client.post(
            "/api/v1/auth/login/",
            {"email": email, "password": password or self.password},
            format="json",
            HTTP_HOST="localhost",
            **headers,
        )

    def test_registration_normalizes_email_and_rejects_duplicate_case(self):
        response = self.register("Person@Example.COM")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["email"], "person@example.com")

        duplicate = self.register("PERSON@example.com")
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(User.objects.count(), 1)

    def test_registration_requires_csrf_and_valid_password(self):
        response = self.client.post(
            "/api/v1/auth/register/",
            {"email": "person@example.com", "password": self.password},
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(response.status_code, 403)

        response = self.register(password="short")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.exists())

    def test_login_me_and_logout(self):
        self.register()
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("token", response.json())

        me = self.client.get("/api/v1/auth/me/", HTTP_HOST="localhost")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["email"], "person@example.com")

        logout = self.client.post(
            "/api/v1/auth/logout/",
            format="json",
            HTTP_HOST="localhost",
            **self.csrf_headers(),
        )
        self.assertEqual(logout.status_code, 204)
        self.assertNotEqual(
            self.client.get("/api/v1/auth/me/", HTTP_HOST="localhost").status_code,
            200,
        )

    def test_invalid_credentials_and_inactive_user_are_rejected(self):
        self.register()
        invalid = self.login(password="incorrect password")
        self.assertEqual(invalid.status_code, 400)

        user = User.objects.get(email="person@example.com")
        user.is_active = False
        user.save(update_fields=("is_active",))
        inactive = self.login()
        self.assertEqual(inactive.status_code, 400)

    def test_me_only_changes_the_authenticated_users_profile(self):
        self.register()
        other = User.objects.create_user(
            email="other@example.com", password=self.password, first_name="Other"
        )
        self.login()

        response = self.client.patch(
            "/api/v1/auth/me/",
            {"id": str(other.pk), "first_name": "Updated"},
            format="json",
            HTTP_HOST="localhost",
            **self.csrf_headers(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["id"], str(User.objects.get(email="person@example.com").pk)
        )
        other.refresh_from_db()
        self.assertEqual(other.first_name, "Other")

    def test_password_change_checks_current_password_and_keeps_session(self):
        self.register()
        self.login()
        response = self.client.post(
            "/api/v1/auth/password/change/",
            {
                "current_password": self.password,
                "new_password": "Another-Sensible-Password-982!",
            },
            format="json",
            HTTP_HOST="localhost",
            **self.csrf_headers(),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.client.get("/api/v1/auth/me/", HTTP_HOST="localhost").status_code, 200
        )

    def test_password_reset_is_non_enumerating_and_resets_password(self):
        self.register()
        headers = self.csrf_headers()
        known = self.client.post(
            "/api/v1/auth/password/reset/",
            {"email": "person@example.com"},
            format="json",
            HTTP_HOST="localhost",
            **headers,
        )
        unknown = self.client.post(
            "/api/v1/auth/password/reset/",
            {"email": "missing@example.com"},
            format="json",
            HTTP_HOST="localhost",
            **headers,
        )
        self.assertEqual(known.status_code, 200)
        self.assertEqual(known.json(), unknown.json())
        self.assertEqual(len(mail.outbox), 1)

        lines = mail.outbox[0].body.splitlines()
        uid = next(
            line.removeprefix("uid: ") for line in lines if line.startswith("uid: ")
        )
        token = next(
            line.removeprefix("token: ") for line in lines if line.startswith("token: ")
        )
        reset = self.client.post(
            "/api/v1/auth/password-reset/confirm/",
            {
                "uid": uid,
                "token": token,
                "new_password": "Reset-Sensible-Password-983!",
            },
            format="json",
            HTTP_HOST="localhost",
            **self.csrf_headers(),
        )
        self.assertEqual(reset.status_code, 200)
        self.client.post(
            "/api/v1/auth/logout/",
            format="json",
            HTTP_HOST="localhost",
            **self.csrf_headers(),
        )
        self.assertEqual(
            self.login(password="Reset-Sensible-Password-983!").status_code, 200
        )
