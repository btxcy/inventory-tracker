from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APITestCase
from django.db import IntegrityError, transaction
from django.contrib.auth import get_user_model
from .models import Category, Product, StockMovement
from unittest.mock import patch
from .services import StockError, create_product, record_movement, InsufficientStock, InvalidQuantity, InvalidMovementType, AlreadyExist

# Create your tests here.

class RecordMovementTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="TestCat", slug="testcat")
        self.product = Product.objects.create(
            sku = "T-01",
            name = "Test01",
            category = self.category,
            description = "Test01 Product",
            cost_price = "1.00",
            sale_price = "2399.99",
            reorder_level = 10,
        )

    def test_purchase_increases_quantity(self):
        record_movement(
            product = self.product,
            movement_type = "PURCHASE",
            quantity = 10,
            unit_cost = "20.00",
            reference = "Nothing",
        )
        self.product.refresh_from_db()

        self.assertEqual(self.product.quantity, 10)

        self.assertEqual(self.product.movements.count(), 1)
        movement = self.product.movements.first()
        self.assertEqual(movement.movement_type, "PURCHASE")
        self.assertEqual(movement.quantity, 10)
        self.assertEqual(movement.signed_quantity, 10)

    def test_sell_quantity(self):
        record_movement(
            product = self.product,
            movement_type = "PURCHASE",
            quantity = 10,
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 10)

        record_movement(
            product = self.product,
            movement_type = "SALE",
            quantity = 5,
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 5)

    def test_insufficient_stock(self):
        with self.assertRaises(InsufficientStock):
            record_movement(
                product = self.product, 
                movement_type = "SALE", 
                quantity = 5
            )

    def test_quantity_always_matches_ledger_sum(self):
        record_movement(
            product = self.product,
            movement_type = "PURCHASE",
            quantity = 999,
        )
        record_movement(
            product = self.product,
            movement_type = "SALE",
            quantity = 777,
        )
        record_movement(
            product = self.product,
            movement_type = "PURCHASE",
            quantity = 111,
        )
        self.product.refresh_from_db()
        ledger = 0
        for item in self.product.movements.all():
            ledger += item.signed_quantity
        self.assertEqual(self.product.quantity, ledger)

    def test_failed_movement_does_not_save_movement(self):
        record_movement(
            product = self.product,
            movement_type = "PURCHASE",
            quantity = 10,
        )
        before = StockMovement.objects.count()

        # since this raise the insufficient error, we dont save
        with self.assertRaises(InsufficientStock):
            record_movement(
                product = self.product, 
                movement_type = "SALE", 
                quantity = 999,
            )

        self.assertEqual(StockMovement.objects.count(), before)
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 10)

    def test_zero_quantity_raises(self):
        with self.assertRaises(InvalidQuantity):
            record_movement(
                product = self.product,
                movement_type = "SALE",
                quantity = 0,
            )

    def test_unknown_movement_type(self):
        with self.assertRaises(InvalidMovementType):
            record_movement(
                product = self.product,
                movement_type = "TELEPORT",
                quantity = 10,
            )

    def test_database_rejects_negative_quantity(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Product.objects.filter(pk=self.product.pk).update(quantity=-5)

class ProductAPITests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("tester01", password="password")
        self.category = Category.objects.create(name="TestCat", slug="testcat")
        self.product2 = Product.objects.create(
            sku = "T-02",
            name = "Test02",
            category = self.category,
            description = "Test02 Product",
            cost_price = "5.00",
            sale_price = "8899.99",
            quantity = 300,
            reorder_level = 10,
        )

        self.product3 = Product.objects.create(
            sku = "T-03",
            name = "Test03",
            category = self.category,
            description = "Test03 Product",
            cost_price = "5.00",
            sale_price = "1000.99",
            quantity = 100,
            reorder_level = 200,
        )

    def test_unauthenticated_request_is_forbidden(self):
        response = self.client.get("/api/products/")
        self.assertEqual(response.status_code, 403)

    def test_authenticated_request_success(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/products/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)

    def test_low_stock(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/products/low_stock/")
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["sku"], "T-03")

    def test_cannot_set_quantity_on_create(self):
        self.client.force_authenticate(user=self.user)
        data = {
            "sku": "T-04",
            "name": "Taxi",
            "category": self.category.pk,
            "cost_price": "1.00",
            "sale_price": "2.00",
            "quantity": 9999,
        }
        response = self.client.post("/api/products/", data=data, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["quantity"], 0) # quantity sets to 0

    def test_delete_is_soft(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(f"/api/products/{self.product3.pk}/")

        self.assertEqual(response.status_code, 204)
        product = Product.objects.get(pk=self.product3.pk)
        self.assertEqual(product.is_active, False)
        # check if there is only one product left
        listing = self.client.get("/api/products/")
        self.assertEqual(listing.data["count"], 1)

class StockMovementAPITest(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("tester01", password="password")
        self.category = Category.objects.create(name="TestCat", slug="testcat")
        self.product6 = Product.objects.create(
            sku = "T-06",
            name = "Test06",
            category = self.category,
            description = "Test06 Product",
            cost_price = "13.00",
            sale_price = "1824.99",
            quantity = 1,
            reorder_level = 10,
        )

        self.product7 = Product.objects.create(
            sku = "T-07",
            name = "Test07",
            category = self.category,
            description = "Test07 Product",
            cost_price = "58.00",
            sale_price = "79890.99",
            quantity = 800,
            reorder_level = 1000,
        )

    def test_stockmovement_post_success(self):
        self.client.force_authenticate(user=self.user)
        data = {
            "product": self.product7.pk,
            "movement_type": "PURCHASE",
            "quantity": 5,
            "unit_cost": "30.00",
            "reference": "Test T-07",
        }
        response = self.client.post("/api/movements/", data=data, format="json")
        self.assertEqual(response.status_code, 201)
        self.product7.refresh_from_db()
        self.assertEqual(self.product7.quantity, 805)

    def test_stockmovement_post_not_enough_stock(self):
        self.client.force_authenticate(user=self.user)
        data = {
            "product": self.product6.pk,
            "movement_type": "SALE",
            "quantity": 5,
            "reference": "Test T-06 SALE",
        }
        response = self.client.post("/api/movements/", data=data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Insufficient", response.data["detail"])

    def test_stockmovement_cannot_put(self):
        self.client.force_authenticate(user=self.user)
        movement = record_movement(
            product = self.product7,
            movement_type = "SALE",
            quantity = 5,
        )
        response = self.client.put(
            f"/api/movements/{movement.pk}/", 
            {"product": self.product7.pk,
            "movement_type": "SALE",
            "quantity": 1}, 
            format="json"
        )
        self.assertEqual(response.status_code, 405)

class CreateProductTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="TestCat", slug="testcat")

    def test_minimal_fields_use_model_defaults(self):
        product = create_product(
            sku="T-10",
            name="Test10",
            category=self.category,
            cost_price="2000.00",
            sale_price="2999.00",
        )
        self.assertEqual(product.sku, "T-10")
        self.assertEqual(product.quantity, 0)
        self.assertEqual(product.unit, "EACH")  
        self.assertEqual(product.reorder_level, 10)
        self.assertEqual(product.reorder_quantity, 0)
        self.assertTrue(product.is_active)
        self.assertEqual(product.movements.count(), 0)
        self.assertEqual(product.supplier, None)

    def test_opening_quantity_creates_ledger_row(self):
        # if quantity > 0 we record in the ledger #96
        product = create_product(
            sku="T-11",
            name="Test11",
            category=self.category,
            cost_price="12335.00",
            sale_price="29923.00",
            quantity=30,
        )
        self.assertEqual(product.sku, "T-11")
        self.assertEqual(product.quantity, 30)
        self.assertEqual(product.movements.count(), 1)
        movement = product.movements.first()
        self.assertEqual(movement.movement_type, "PURCHASE")
        self.assertEqual(movement.unit_cost, Decimal("12335.00"))

        ledger = sum(m.signed_quantity for m in product.movements.all())
        self.assertEqual(product.quantity, ledger)

    def test_duplicate_sku_raises(self):
        create_product(sku="T-01", name="TEST-5G", category=self.category, 
                       cost_price=Decimal("10.99"), sale_price=Decimal("15.99"))

        # both T-01
        with self.assertRaises(AlreadyExist):
            create_product(sku="T-01", name="TEST-10G", category=self.category,
                            cost_price=Decimal("17.99"), sale_price=Decimal("19.99"))

    # claude - test if stock movement incorrect then rollback
    def test_failed_opening_movement_rolls_back_product(self):
        with patch("inventory.services.record_movement",
                   side_effect=StockError("roll-back")):
            with self.assertRaises(StockError):
                create_product(
                    sku="T-12",
                    name="Test12",
                    category=self.category,
                    cost_price="10.00",
                    sale_price="20.00",
                    quantity=5,
                )
        self.assertFalse(Product.objects.filter(sku="T-12").exists())
