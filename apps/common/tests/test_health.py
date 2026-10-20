from unittest.mock import patch

from django.db import DatabaseError
from django.test import SimpleTestCase
from django.urls import reverse


class HealthEndpointTests(SimpleTestCase):
    def test_liveness_does_not_require_database(self):
        with patch("apps.common.views.connections") as connections:
            response = self.client.get(reverse("health-live"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        connections.__getitem__.assert_not_called()

    def test_readiness_returns_ok_when_database_connects(self):
        with patch("apps.common.views.connections") as connections:
            response = self.client.get(reverse("health-ready"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        connections.__getitem__.return_value.ensure_connection.assert_called_once()

    def test_readiness_returns_generic_error_when_database_is_unavailable(self):
        with patch("apps.common.views.connections") as connections:
            connections.__getitem__.return_value.ensure_connection.side_effect = (
                DatabaseError("private connection details")
            )
            response = self.client.get(reverse("health-ready"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unavailable"})
        self.assertNotIn("private connection details", response.content.decode())
