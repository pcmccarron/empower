import os
import unittest
from unittest.mock import patch


with patch.dict(os.environ, {
    'FLASK_RELEASE': 'test-release',
    'FLASK_DSN': '',
    'FLASK_ENVIRONMENT': 'local',
    'BACKEND_URL_RUBYONRAILS': 'http://test-backend',
    'RUN_SLOW_PROFILE': 'false',
    'STATSIG_SERVER_KEY': 'test-key',
    'FLASK_REDISHOST': 'localhost',
    'FLASK_REDISPORT': '6379',
    'DB_HOST': 'localhost',
    'DB_DATABASE': 'test-db',
    'DB_USERNAME': 'test-user',
    'DB_PASSWORD': 'test-password',
}):
    with patch('sentry_sdk.init'), patch('statsig.statsig.initialize'):
        from ..main import app


class TestUnhandledEndpoint(unittest.TestCase):
    def test_unhandled_endpoint_returns_successful_response(self):
        response = app.test_client().get('/unhandled')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {})


if __name__ == '__main__':
    unittest.main()
