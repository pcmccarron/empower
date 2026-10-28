import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch


class TestCheckout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch.dict(os.environ, {
            "DB_HOST": "localhost",
            "DB_DATABASE": "test_db",
            "DB_USERNAME": "test_user",
            "DB_PASSWORD": "",
            "FLASK_RELEASE": "test",
            "FLASK_DSN": "",
            "FLASK_ENVIRONMENT": "local",
            "BACKEND_URL_RUBYONRAILS": "http://localhost",
            "FLASK_REDISHOST": "localhost",
            "FLASK_REDISPORT": "6379",
            "STATSIG_SERVER_KEY": "",
        }), patch("sentry_sdk.init"), patch("statsig.statsig.initialize"):
            from .. import main
        cls.main = main

    def setUp(self):
        self.client = self.main.app.test_client()
        self.order = {
            "cart": {
                "items": [{"id": 1, "title": "Plant"}],
                "quantities": {"1": 2},
                "total": 50,
            },
            "form": {},
        }
        self.inventory = self.enterContext(patch.object(self.main, "get_inventory"))
        self.inventory.return_value = [SimpleNamespace(productid=1, id=10, count=2)]
        self.decrement = self.enterContext(patch.object(self.main, "decrement_inventory"))
        self.enterContext(patch.object(self.main, "evaluate_statsig_flags"))
        self.enterContext(patch.object(self.main.sentry_sdk.metrics, "distribution"))

    def test_checkout_with_inventory(self):
        response = self.client.post("/checkout", json=self.order)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(force=True), {"status": "success"})
        self.inventory.assert_called_once_with(self.order["cart"])
        self.decrement.assert_called_once_with(10, 2)

    def test_checkout_without_enough_inventory(self):
        for inventory in ([], [SimpleNamespace(productid=1, id=10, count=1)]):
            with self.subTest(inventory=inventory):
                self.inventory.return_value = inventory
                response = self.client.post("/checkout", json=self.order)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.get_json(force=True), {"status": "failed"})
                self.decrement.assert_not_called()

    def test_checkout_with_partial_inventory(self):
        self.order["cart"]["items"].append({"id": 2, "title": "Fern"})
        self.order["cart"]["quantities"]["2"] = 1
        response = self.client.post("/checkout", json=self.order)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(force=True), {
            "status": "partial", "out_of_stock": ["Fern"],
        })
        self.decrement.assert_called_once_with(10, 2)

    def test_checkout_with_empty_cart(self):
        self.order["cart"]["items"] = []
        self.order["cart"]["quantities"] = {}
        self.inventory.return_value = []
        with self.main.app.test_request_context("/checkout", json=self.order):
            with self.assertRaisesRegex(Exception, "Error validating enough inventory") as error:
                self.main.checkout()

        self.assertEqual(str(error.exception.__cause__), "Invalid checkout request: cart is empty")
        self.decrement.assert_not_called()

    def test_checkout_without_inventory_validation(self):
        self.order["validate_inventory"] = "false"
        self.inventory.return_value = []
        response = self.client.post("/checkout", json=self.order)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(force=True), {"status": "success"})
        self.decrement.assert_not_called()
