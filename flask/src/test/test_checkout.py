import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import Mock, patch


class TestCheckout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch.dict('os.environ', {
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
        }), patch('dotenv.load_dotenv'), patch('sqlalchemy.create_engine'), \
                patch('sentry_sdk.init'), patch('statsig.statsig.initialize'):
            from .. import main
        cls.main = main

    def setUp(self):
        self.client = self.main.app.test_client()
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.dict(self.main.app.config, TESTING=True))
        self.inventory = stack.enter_context(
            patch.object(self.main, 'get_inventory')
        )
        self.decrement = stack.enter_context(
            patch.object(self.main, 'decrement_inventory')
        )
        stack.enter_context(patch.object(self.main, 'evaluate_statsig_flags'))
        self.metrics = stack.enter_context(
            patch.object(self.main.sentry_sdk, 'metrics', Mock())
        )
        self.order = {
            'cart': {
                'quantities': {'1': 2},
                'items': [{'id': 1, 'title': 'Plant'}],
                'total': 20,
            },
            'form': {},
        }
        self.inventory.return_value = [
            SimpleNamespace(id=10, productid=1, count=3)
        ]

    def test_checkout_success(self):
        response = self.client.post('/checkout', json=self.order)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(force=True), {'status': 'success'})
        self.inventory.assert_called_once_with(self.order['cart'])
        self.decrement.assert_called_once_with(10, 2)
        self.metrics.distribution.assert_called_once_with(
            'checkout.captured.revenue', 20, unit='none'
        )

    def test_empty_cart(self):
        self.order['cart']['quantities'] = {}
        self.order['cart']['items'] = []
        self.inventory.return_value = []

        with self.assertRaisesRegex(
            Exception, 'Error validating enough inventory for product'
        ) as raised:
            self.client.post('/checkout', json=self.order)

        self.assertEqual(
            str(raised.exception.__cause__),
            'Invalid checkout request: cart is empty',
        )
        self.decrement.assert_not_called()
        self.metrics.distribution.assert_not_called()

    def test_out_of_stock(self):
        for inventory in ([], [SimpleNamespace(id=10, productid=1, count=1)]):
            with self.subTest(inventory=inventory):
                self.inventory.return_value = inventory
                response = self.client.post('/checkout', json=self.order)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.get_json(force=True), {'status': 'failed'})
                self.decrement.assert_not_called()
                self.metrics.distribution.assert_not_called()

    def test_partial_checkout(self):
        self.order['cart']['quantities']['2'] = 1
        self.order['cart']['items'].append({'id': 2, 'title': 'Fern'})

        response = self.client.post('/checkout', json=self.order)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(force=True), {
            'status': 'partial', 'out_of_stock': ['Fern'],
        })
        self.decrement.assert_called_once_with(10, 2)
        self.metrics.distribution.assert_not_called()

    def test_validation_disabled(self):
        self.order['validate_inventory'] = 'false'
        self.order['cart']['quantities'] = {}
        self.inventory.return_value = []

        response = self.client.post('/checkout', json=self.order)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(force=True), {'status': 'success'})
        self.decrement.assert_not_called()
