import unittest
from unittest.mock import patch


class TestHandledException(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch.dict('os.environ', {
            'DB_HOST': 'localhost',
            'DB_DATABASE': 'test_db',
            'DB_USERNAME': 'test_user',
            'DB_PASSWORD': '',
            'FLASK_RELEASE': 'test-release',
            'FLASK_DSN': '',
            'FLASK_ENVIRONMENT': 'local',
            'BACKEND_URL_RUBYONRAILS': 'http://localhost',
            'FLASK_REDISHOST': 'localhost',
            'FLASK_REDISPORT': '6379',
            'STATSIG_SERVER_KEY': '',
        }), patch('dotenv.load_dotenv'), patch('sentry_sdk.init'), \
                patch('statsig.statsig.initialize'), \
                patch('sqlalchemy.create_engine'):
            from ..main import app
        cls.app = app

    @patch('src.main.sentry_sdk.capture_exception')
    def test_handled_does_not_capture_type_error(self, capture_exception):
        with self.app.test_client() as client:
            response = client.get('/handled')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_data(as_text=True), 'failed')
        capture_exception.assert_not_called()
