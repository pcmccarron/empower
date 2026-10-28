import unittest
from datetime import datetime, timedelta
from unittest.mock import patch


class TestApplyPromoCode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch.dict('os.environ', {
            'DB_HOST': 'localhost',
            'DB_DATABASE': 'test',
            'DB_USERNAME': 'test',
            'DB_PASSWORD': '',
            'FLASK_RELEASE': 'test',
            'FLASK_DSN': '',
            'FLASK_ENVIRONMENT': 'local',
            'BACKEND_URL_RUBYONRAILS': 'http://localhost',
            'STATSIG_SERVER_KEY': '',
            'FLASK_REDISHOST': 'localhost',
            'FLASK_REDISPORT': '6379',
        }), patch('dotenv.load_dotenv'), patch('sentry_sdk.init'), \
                patch('statsig.statsig.initialize'), patch('sqlalchemy.create_engine'):
            from .. import main
        cls.main = main

    def setUp(self):
        self.client = self.main.app.test_client()
        self.get_promo_code = self.enterContext(
            patch.object(self.main, 'get_promo_code')
        )
        self.capture_exception = self.enterContext(
            patch.object(self.main.sentry_sdk, 'capture_exception')
        )

    def test_invalid_request_bodies_return_400(self):
        bodies = [
            b'', b'not-json', b'   ', b'{"value":', b'\xff',
            b'null', b'[]', b'"SAVE10"', b'123', b'true',
            b'{}', b'{"value": null}', b'{"value": 10}',
            b'{"value": []}', b'{"value": {}}', b'{"value": false}',
            b'{"value": ""}', b'{"value": "   "}',
        ]
        for body in bodies:
            with self.subTest(body=body):
                response = self.client.post(
                    '/apply-promo-code', data=body, content_type='application/json'
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data, b'')
        self.get_promo_code.assert_not_called()
        self.capture_exception.assert_not_called()

    def test_valid_code_is_trimmed_and_returns_discount(self):
        self.get_promo_code.return_value = {
            'code': 'SAVE10',
            'percent_discount': 10,
            'max_dollar_savings': 20,
            'expires_at': datetime.now() + timedelta(days=1),
        }
        response = self.client.post('/apply-promo-code', json={'value': ' SAVE10 '})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {
            'success': True,
            'promo_code': {
                'code': 'SAVE10',
                'percent_discount': 10,
                'max_dollar_savings': 20,
            },
        })
        self.get_promo_code.assert_called_once_with('SAVE10')
        self.capture_exception.assert_not_called()

    def test_unknown_code_returns_404(self):
        self.get_promo_code.return_value = None
        response = self.client.post('/apply-promo-code', json={'value': 'UNKNOWN'})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()['error']['code'], 'not_found')
        self.capture_exception.assert_not_called()

    def test_json_without_json_content_type_is_still_accepted(self):
        self.get_promo_code.return_value = None
        response = self.client.post('/apply-promo-code', data='{"value": "UNKNOWN"}')
        self.assertEqual(response.status_code, 404)
        self.get_promo_code.assert_called_once_with('UNKNOWN')
        self.capture_exception.assert_not_called()

    def test_expired_code_returns_410(self):
        self.get_promo_code.return_value = {
            'expires_at': datetime.now() - timedelta(days=1),
        }
        response = self.client.post('/apply-promo-code', json={'value': 'EXPIRED'})
        self.assertEqual(response.status_code, 410)
        self.assertEqual(response.get_json()['error']['code'], 'expired')
        self.capture_exception.assert_not_called()

    def test_database_failure_is_still_reported(self):
        error = RuntimeError('Database unavailable')
        self.get_promo_code.side_effect = error
        response = self.client.post('/apply-promo-code', json={'value': 'SAVE10'})
        self.assertEqual(response.status_code, 500)
        self.capture_exception.assert_called_once_with(error)
