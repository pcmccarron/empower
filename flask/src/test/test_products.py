import importlib
import json
import os
import unittest
from unittest.mock import Mock, patch


class Row(dict):
    def __getattr__(self, name):
        return self[name]


class TestGetProducts(unittest.TestCase):
    @patch.dict(os.environ, {
        "DB_HOST": "localhost",
        "DB_DATABASE": "test_db",
        "DB_USERNAME": "test_user",
        "DB_PASSWORD": "test_password",
        "FLASK_ENVIRONMENT": "local",
    })
    def test_get_products_fetches_reviews_in_one_batch(self):
        database = importlib.import_module("src.db")
        products = [Row(id=1, title="First"), Row(id=2, title="Second")]
        reviews = [
            Row(id=10, productid=1, rating=5),
            Row(id=20, productid=2, rating=4),
        ]
        connection = Mock()
        connection.execute.side_effect = [
            Mock(fetchall=Mock(return_value=products)),
            Mock(fetchall=Mock(return_value=reviews)),
        ]

        with patch.object(database.db, "connect", return_value=connection), \
                patch.object(database, "weighter", return_value=1):
            result = json.loads(database.get_products())

        self.assertEqual(connection.execute.call_count, 2)
        query_args, query_params = connection.execute.call_args
        self.assertIn("productId = ANY(:product_ids)", str(query_args[0]))
        self.assertEqual(query_params, {"product_ids": [1, 2]})
        self.assertEqual(result, [
            {"id": 1, "title": "First", "reviews": [{"id": 10, "productid": 1, "rating": 5}]},
            {"id": 2, "title": "Second", "reviews": [{"id": 20, "productid": 2, "rating": 4}]},
        ])


if __name__ == "__main__":
    unittest.main()
