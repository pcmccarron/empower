import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch


class TestCheckout(unittest.TestCase):
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
            'FLASK_REDISHOST': 'localhost',
            'FLASK_REDISPORT': '6379',
            'STATSIG_SERVER_KEY': '',
        }), patch('sqlalchemy.create_engine'), patch('sentry_sdk.init'), patch('statsig.statsig.initialize'):
            from .. import main
            cls.main = main

    def setUp(self):
        self.inventory = self.enterContext(patch.object(self.main, 'get_inventory'))
        self.decrement = self.enterContext(patch.object(self.main, 'decrement_inventory'))
        self.enterContext(patch.object(self.main, 'evaluate_statsig_flags'))
        self.inventory.return_value = [SimpleNamespace(id=7, productid=3, count=10)]
        self.order = {
            'cart': {
                'items': [{'id': 3, 'title': 'Plant Mood'}],
                'quantities': {'3': 2},
                'total': 310,
            },
            'form': {},
        }

    def test_checkout_with_inventory_succeeds(self):
        for validate_inventory in (None, 'true'):
            with self.subTest(validate_inventory=validate_inventory):
                if validate_inventory is not None:
                    self.order['validate_inventory'] = validate_inventory
                self.decrement.reset_mock()
                response = self.main.app.test_client().post('/checkout?v2=true', json=self.order)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(json.loads(response.data), {'status': 'success'})
                self.decrement.assert_called_once_with(7, 2)

    def test_empty_cart_is_rejected(self):
        self.order['cart'].update(items=[], quantities={}, total=0)

        with self.main.app.test_request_context('/checkout', json=self.order):
            with self.assertRaisesRegex(Exception, 'Error validating enough inventory') as error:
                self.main.checkout()

        self.assertEqual(str(error.exception.__cause__), 'Invalid checkout request: cart is empty')
        self.decrement.assert_not_called()

    def test_out_of_stock_cart_fails_without_decrementing_inventory(self):
        self.inventory.return_value = []
        response = self.main.app.test_client().post('/checkout', json=self.order)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), {'status': 'failed'})
        self.decrement.assert_not_called()

    def test_partially_available_cart_reports_out_of_stock_items(self):
        self.order['cart']['items'].append({'id': 4, 'title': 'Plant Friendly'})
        self.order['cart']['quantities']['4'] = 1
        response = self.main.app.test_client().post('/checkout', json=self.order)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), {
            'status': 'partial',
            'out_of_stock': ['Plant Friendly'],
        })
        self.decrement.assert_called_once_with(7, 2)

    def test_inventory_validation_can_be_disabled(self):
        self.order['validate_inventory'] = 'false'
        response = self.main.app.test_client().post('/checkout', json=self.order)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), {'status': 'success'})
        self.decrement.assert_not_called()
