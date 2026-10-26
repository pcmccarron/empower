import importlib
import json
import os
import unittest
from unittest.mock import Mock, patch


class TestGetProducts(unittest.TestCase):
    def test_reviews_are_loaded_in_one_query_and_attached_to_products(self):
        with patch.dict(os.environ, {
            "DB_HOST": "localhost",
            "DB_DATABASE": "test_db",
            "DB_USERNAME": "test_user",
            "DB_PASSWORD": "test_password",
            "FLASK_ENVIRONMENT": "local",
        }):
            db_module = importlib.import_module("..db", package=__package__)

        class Product(dict):
            @property
            def id(self):
                return self["id"]

        products = [Product(id=1, name="First"), Product(id=2, name="Second")]
        reviews = [
            {"id": 10, "productId": 1, "rating": 5},
            {"id": 20, "productId": 2, "rating": 4},
        ]
        connection = Mock()
        connection.execute.side_effect = [
            Mock(fetchall=Mock(return_value=products)),
            Mock(fetchall=Mock(return_value=reviews)),
        ]

        with patch.object(db_module, "db", Mock(connect=Mock(return_value=connection))), \
                patch.object(db_module, "weighter", return_value=1):
            result = json.loads(db_module.get_products())

        self.assertEqual(result, [
            {"id": 1, "name": "First", "reviews": [reviews[0]]},
            {"id": 2, "name": "Second", "reviews": [reviews[1]]},
        ])
        self.assertEqual(connection.execute.call_count, 2)
        self.assertEqual(connection.execute.call_args_list[1].kwargs["product_ids"], [1, 2])


if __name__ == "__main__":
    unittest.main()
