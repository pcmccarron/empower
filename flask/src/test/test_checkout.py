import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch


class TestCheckout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch.dict(os.environ, {
            "FLASK_RELEASE": "test",
            "FLASK_DSN": "",
            "FLASK_ENVIRONMENT": "local",
            "BACKEND_URL_RUBYONRAILS": "http://localhost",
            "FLASK_REDISHOST": "localhost",
            "FLASK_REDISPORT": "6379",
            "STATSIG_SERVER_KEY": "",
            "DB_HOST": "localhost",
            "DB_DATABASE": "test",
            "DB_USERNAME": "test",
            "DB_PASSWORD": "",
        }), patch("dotenv.load_dotenv"), patch("sentry_sdk.init"), \
                patch("statsig.statsig.initialize"), patch("sqlalchemy.create_engine"):
            from .. import main
        cls.main = main

    def setUp(self):
        self.client = self.main.app.test_client()
        self.cart = {
            "quantities": {"1": 2},
            "items": [{"id": 1, "title": "Plant"}],
            "total": 20,
        }
        self.inventory = self.enterContext(patch.object(self.main, "get_inventory"))
        self.inventory.return_value = [SimpleNamespace(id=10, productid=1, count=2)]
        self.decrement = self.enterContext(patch.object(self.main, "decrement_inventory"))
        self.enterContext(patch.object(self.main, "evaluate_statsig_flags"))
        self.metrics = self.enterContext(patch.object(self.main.sentry_sdk, "metrics", create=True))

    def checkout(self, **options):
        return self.client.post("/checkout", json={
            "cart": self.cart,
            "form": {},
            **options,
        })

    def test_checkout_decrements_inventory(self):
        for options in ({}, {"validate_inventory": "true"}):
            with self.subTest(options=options):
                self.decrement.reset_mock()
                response = self.checkout(**options)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(json.loads(response.data), {"status": "success"})
                self.decrement.assert_called_once_with(10, 2)

    def test_checkout_out_of_stock(self):
        self.inventory.return_value = []
        response = self.checkout()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), {"status": "failed"})
        self.decrement.assert_not_called()
        self.metrics.distribution.assert_not_called()

    def test_checkout_partially_in_stock(self):
        self.cart["quantities"]["2"] = 1
        self.cart["items"].append({"id": 2, "title": "Planter"})
        response = self.checkout()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), {
            "status": "partial", "out_of_stock": ["Planter"],
        })
        self.decrement.assert_called_once_with(10, 2)

    def test_checkout_empty_cart(self):
        self.cart["quantities"] = {}
        with self.main.app.test_request_context("/checkout", json={
            "cart": self.cart, "form": {},
        }):
            with self.assertRaisesRegex(Exception, "Error validating enough inventory") as error:
                self.main.checkout()
        self.assertEqual(str(error.exception.__cause__), "Invalid checkout request: cart is empty")
        self.decrement.assert_not_called()

    def test_checkout_without_inventory_validation(self):
        response = self.checkout(validate_inventory="false")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), {"status": "success"})
        self.decrement.assert_not_called()
