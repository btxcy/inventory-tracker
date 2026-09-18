from django.core.management.base import BaseCommand
from django.db import transaction
from inventory.models import Category, Product, Supplier
from ._seed_data import SEED_CATEGORIES, SEED_SUPPLIERS, SEED_PRODUCTS
from django.core.management import call_command
from inventory.services import record_movement

class Command(BaseCommand):
    help = "Create demo inventory data."

    def handle(self, *args, **options):
        self.stdout.write("Starting database seeding...")

        categories = {}
        suppliers = {}

        with transaction.atomic():

            # clean all data first
            call_command("clean_all")

            # seed categories
            for category in SEED_CATEGORIES:
                category_obj, _ = Category.objects.get_or_create(
                    name = category["name"],
                    defaults = {
                        "slug": category["slug"],
                        "description": category["description"],
                    },
                )
                categories[category_obj.name] = category_obj

            # seed suppliers
            for supplier in SEED_SUPPLIERS:
                supplier_obj, _ = Supplier.objects.get_or_create(
                    name = supplier["name"],
                    defaults = {
                        "email": supplier["email"],
                        "phone": supplier["phone"],
                        "lead_time_days": supplier["lead_time_days"],
                    }
                )
                suppliers[supplier_obj.name] = supplier_obj

            # seed products
            for product in SEED_PRODUCTS:
                product_obj, created = Product.objects.get_or_create(
                    sku = product["sku"],
                    defaults = {
                        "name": product["name"],
                        "category": categories[product["category"]],
                        "supplier": suppliers[product["supplier"]],
                        "unit": product["unit"],
                        "cost_price": product["cost_price"],
                        "sale_price": product["sale_price"],
                        "reorder_level": product["reorder_level"],
                        "reorder_quantity": product["reorder_quantity"],
                    }
                )

                # for movement recording when any movement occurs
                if created:
                    record_movement(
                        product = product_obj,
                        movement_type = "PURCHASE",
                        quantity = product["opening_stock"],
                        reference = "Opening Stock",
                        note = "from seed",
                    )

        self.stdout.write(self.style.SUCCESS(f"Seeded {len(SEED_PRODUCTS)} products"))