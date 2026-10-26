import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch


class TestCheckout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with (
            patch.dict('os.environ', {
                'FLASK_RELEASE': 'test',
                'FLASK_DSN': '',
                'FLASK_ENVIRONMENT': 'local',
                'BACKEND_URL_RUBYONRAILS': 'http://localhost',
                'FLASK_REDISHOST': 'localhost',
                'FLASK_REDISPORT': '6379',
                'STATSIG_SERVER_KEY': '',
                'DB_HOST': 'localhost',
                'DB_DATABASE': 'test',
                'DB_USERNAME': 'test',
                'DB_PASSWORD': '',
            }),
            patch('dotenv.load_dotenv'),
            patch('sqlalchemy.create_engine'),
            patch('sentry_sdk.init'),
            patch('statsig.statsig.initialize'),
            patch('redis.Redis'),
        ):
            from .. import main
            cls.main = main

    def setUp(self):
        self.client = self.main.app.test_client()
        self.inventory = self.enterContext(patch.object(self.main, 'get_inventory'))
        self.decrement = self.enterContext(patch.object(self.main, 'decrement_inventory'))
        self.enterContext(patch.object(self.main, 'evaluate_statsig_flags'))
        self.order = {
            'cart': {
                'items': [{'id': 3, 'title': 'Plant Mood'}],
                'quantities': {'3': 1},
                'total': 155,
            },
            'form': {},
        }

    def test_in_stock_checkout(self):
        self.inventory.return_value = [SimpleNamespace(id=7, productid=3, count=5)]

        for validation in (None, 'true'):
            with self.subTest(validate_inventory=validation):
                if validation is not None:
                    self.order['validate_inventory'] = validation
                self.decrement.reset_mock()

                response = self.client.post('/checkout?v2=true', json=self.order)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(json.loads(response.data), {'status': 'success'})
                self.decrement.assert_called_once_with(7, 1)

    def test_out_of_stock_checkout(self):
        self.inventory.return_value = [SimpleNamespace(id=7, productid=3, count=0)]

        response = self.client.post('/checkout?v2=true', json=self.order)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), {'status': 'failed'})
        self.decrement.assert_not_called()

    def test_empty_cart_still_rejected(self):
        self.order['cart'] = {'items': [], 'quantities': {}, 'total': 0}
        self.inventory.return_value = []

        with self.main.app.test_request_context('/checkout?v2=true', json=self.order):
            with self.assertRaisesRegex(Exception, 'Error validating enough inventory') as error:
                self.main.checkout()

        self.assertEqual(str(error.exception.__cause__), 'Invalid checkout request: cart is empty')
        self.decrement.assert_not_called()

    def test_inventory_validation_can_be_disabled(self):
        self.order['validate_inventory'] = 'false'
        self.inventory.return_value = []

        response = self.client.post('/checkout?v2=true', json=self.order)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), {'status': 'success'})
        self.decrement.assert_not_called()
