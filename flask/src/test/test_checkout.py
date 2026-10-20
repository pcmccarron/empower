import json
import os
import unittest
from contextlib import nullcontext
from unittest.mock import Mock, patch


with patch.dict(os.environ, {
    "FLASK_RELEASE": "test",
    "FLASK_DSN": "",
    "FLASK_ENVIRONMENT": "local",
    "BACKEND_URL_RUBYONRAILS": "http://localhost",
    "FLASK_REDISHOST": "localhost",
    "FLASK_REDISPORT": "6379",
    "STATSIG_SERVER_KEY": "test",
    "RUN_SLOW_PROFILE": "false",
    "DB_HOST": "localhost",
    "DB_DATABASE": "test",
    "DB_USERNAME": "test",
    "DB_PASSWORD": "test",
}):
    with patch("sentry_sdk.init"), patch("statsig.statsig.initialize"), patch("redis.Redis"):
        from .. import main


class TestCheckout(unittest.TestCase):
    def test_checkout_with_inventory_returns_success(self):
        inventory_item = Mock(id=42, productid=3, count=5)
        order = {
            "cart": {
                "items": [{"id": 3, "title": "Plant Mood"}],
                "quantities": {"3": 1},
                "total": 155,
            },
            "form": {},
        }

        with (
            patch.object(main, "evaluate_statsig_flags"),
            patch.object(main, "get_inventory", return_value=[inventory_item]),
            patch.object(main, "decrement_inventory") as decrement_inventory,
            patch.object(main.sentry_sdk, "start_span", return_value=nullcontext()),
            patch.object(main.sentry_sdk.metrics, "distribution"),
        ):
            response = main.app.test_client().post("/checkout", json=order)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), {"status": "success"})
        decrement_inventory.assert_called_once_with(42, 1)


if __name__ == "__main__":
    unittest.main()
