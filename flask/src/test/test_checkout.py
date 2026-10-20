import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch


class TestCheckout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch.dict(os.environ, {
            "DB_HOST": "localhost",
            "DB_DATABASE": "test",
            "DB_USERNAME": "test",
            "DB_PASSWORD": "",
            "FLASK_RELEASE": "test",
            "FLASK_DSN": "",
            "FLASK_ENVIRONMENT": "local",
            "BACKEND_URL_RUBYONRAILS": "http://localhost",
            "FLASK_REDISHOST": "localhost",
            "FLASK_REDISPORT": "6379",
            "STATSIG_SERVER_KEY": "",
        }), patch("dotenv.load_dotenv"), patch("sentry_sdk.init"), patch(
            "statsig.statsig.initialize"
        ), patch("sqlalchemy.create_engine"):
            from .. import main
        cls.main = main

    def setUp(self):
        config = patch.dict(self.main.app.config, TESTING=True)
        config.start()
        self.addCleanup(config.stop)
        for name in ("get_inventory", "decrement_inventory", "evaluate_statsig_flags"):
            patcher = patch.object(self.main, name)
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)
        metrics = patch.object(self.main.sentry_sdk.metrics, "distribution")
        self.revenue = metrics.start()
        self.addCleanup(metrics.stop)
        self.client = self.main.app.test_client()
        self.order = {
            "cart": {
                "quantities": {"1": 2},
                "items": [{"id": 1, "title": "Plant"}],
                "total": 20,
            },
            "form": {},
        }

    def test_checkout_success(self):
        self.get_inventory.return_value = [
            SimpleNamespace(id=10, productid=1, count=2)
        ]
        response = self.client.post("/checkout", json=self.order)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), {"status": "success"})
        self.decrement_inventory.assert_called_once_with(10, 2)
        self.revenue.assert_called_once_with(
            "checkout.captured.revenue", 20, unit="none"
        )

    def test_checkout_out_of_stock(self):
        self.get_inventory.return_value = []
        response = self.client.post("/checkout", json=self.order)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), {"status": "failed"})
        self.decrement_inventory.assert_not_called()
        self.revenue.assert_not_called()

    def test_checkout_partial(self):
        self.order["cart"]["quantities"]["2"] = 1
        self.order["cart"]["items"].append({"id": 2, "title": "Planter"})
        self.get_inventory.return_value = [
            SimpleNamespace(id=10, productid=1, count=2)
        ]
        response = self.client.post("/checkout", json=self.order)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), {
            "status": "partial", "out_of_stock": ["Planter"]
        })
        self.decrement_inventory.assert_called_once_with(10, 2)
        self.revenue.assert_not_called()

    def test_checkout_empty_cart(self):
        self.order["cart"]["quantities"] = {}
        self.order["cart"]["items"] = []
        self.get_inventory.return_value = []
        with self.assertRaisesRegex(
            Exception, "Error validating enough inventory for product"
        ) as error:
            self.client.post("/checkout", json=self.order)
        self.assertEqual(
            str(error.exception.__cause__), "Invalid checkout request: cart is empty"
        )
        self.decrement_inventory.assert_not_called()
        self.revenue.assert_not_called()

    def test_checkout_without_inventory_validation(self):
        self.order["validate_inventory"] = "false"
        self.get_inventory.return_value = []
        response = self.client.post("/checkout", json=self.order)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), {"status": "success"})
        self.decrement_inventory.assert_not_called()
