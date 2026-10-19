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
        }), patch('dotenv.load_dotenv'), patch('sentry_sdk.init'), patch('statsig.statsig.initialize'):
            from .. import main
        cls.main = main

    def setUp(self):
        self.client = self.main.app.test_client()
        self.order = {
            'cart': {
                'quantities': {'1': 2, '2': 1},
                'items': [
                    {'id': 1, 'title': 'Fern'},
                    {'id': 2, 'title': 'Palm'},
                ],
                'total': 30,
            },
            'form': {'paymentMethod': 'card'},
        }
        self.inventory = self.enterContext(
            patch.object(self.main, 'get_inventory', return_value=[
                SimpleNamespace(id=10, productid=1, count=5),
                SimpleNamespace(id=20, productid=2, count=3),
            ])
        )
        self.decrement = self.enterContext(patch.object(self.main, 'decrement_inventory'))
        self.enterContext(patch.object(self.main, 'evaluate_statsig_flags'))
        self.revenue = self.enterContext(
            patch.object(self.main.sentry_sdk.metrics, 'distribution')
        )

    def checkout(self):
        return self.client.post('/checkout', json=self.order)

    def test_checkout_with_sufficient_inventory(self):
        response = self.checkout()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(force=True), {'status': 'success'})
        self.inventory.assert_called_once_with(self.order['cart'])
        self.assertEqual(self.decrement.call_count, 2)
        self.decrement.assert_any_call(10, 2)
        self.decrement.assert_any_call(20, 1)
        self.revenue.assert_called_once_with('checkout.captured.revenue', 30, unit='none')

    def test_checkout_with_empty_cart(self):
        self.order['cart']['quantities'] = {}
        self.order['cart']['items'] = []
        self.inventory.return_value = []

        with self.main.app.test_request_context('/checkout', json=self.order):
            with self.assertRaisesRegex(Exception, 'Error validating enough inventory for product') as error:
                self.main.checkout()

        self.assertEqual(str(error.exception.__cause__), 'Invalid checkout request: cart is empty')
        self.decrement.assert_not_called()
        self.revenue.assert_not_called()

    def test_checkout_with_no_inventory(self):
        self.inventory.return_value = []

        response = self.checkout()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(force=True), {'status': 'failed'})
        self.decrement.assert_not_called()
        self.revenue.assert_not_called()

    def test_checkout_with_partial_inventory(self):
        self.inventory.return_value[1].count = 0

        response = self.checkout()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(force=True), {'status': 'partial', 'out_of_stock': ['Palm']})
        self.decrement.assert_called_once_with(10, 2)
        self.revenue.assert_not_called()

    def test_checkout_without_inventory_validation(self):
        self.order['validate_inventory'] = 'false'
        self.order['cart']['quantities'] = {}
        self.inventory.return_value = []

        response = self.checkout()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(force=True), {'status': 'success'})
        self.decrement.assert_not_called()
