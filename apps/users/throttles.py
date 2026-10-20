from rest_framework.throttling import AnonRateThrottle


class LoginThrottle(AnonRateThrottle):
    scope = "login"


class RegistrationThrottle(AnonRateThrottle):
    scope = "registration"


class PasswordResetThrottle(AnonRateThrottle):
    scope = "password_reset"
