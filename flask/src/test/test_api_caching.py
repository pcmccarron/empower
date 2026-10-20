import os
import unittest
from unittest.mock import patch

from statsig import statsig

with patch.dict(os.environ, {
    "FLASK_RELEASE": "test-release",
    "FLASK_DSN": "",
    "FLASK_ENVIRONMENT": "local",
    "BACKEND_URL_RUBYONRAILS": "http://test-backend",
    "FLASK_REDISHOST": "localhost",
    "FLASK_REDISPORT": "6379",
    "STATSIG_SERVER_KEY": "test-key",
    "DB_HOST": "localhost",
    "DB_DATABASE": "test-db",
    "DB_USERNAME": "test-user",
    "DB_PASSWORD": "test-password",
}), patch.object(statsig, "initialize"):
    from .. import main


class TestApiResponseCaching(unittest.TestCase):
    def call_api_with_status(self, status_code):
        response = main.requests.Response()
        response.status_code = status_code
        response.url = "http://test-backend/api"

        with (
            main.app.test_request_context("/products"),
            patch.object(main.redis_client, "get", return_value=None),
            patch.object(main.requests, "get", return_value=response),
            patch.object(main.sentry_sdk, "capture_exception") as capture_exception,
        ):
            result = main.get_api_response_with_caching("13", 0)

        return result, capture_exception

    def test_forbidden_backend_response_is_not_captured(self):
        result, capture_exception = self.call_api_with_status(403)

        self.assertEqual(result, "13")
        capture_exception.assert_not_called()

    def test_other_backend_http_errors_are_captured(self):
        result, capture_exception = self.call_api_with_status(500)

        self.assertEqual(result, "13")
        capture_exception.assert_called_once()
