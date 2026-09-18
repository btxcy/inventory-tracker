from django.core.management.base import BaseCommand
from django.db import transaction
from inventory.models import Category, Product, Supplier, StockMovement

class Command(BaseCommand):
    help = "Clean all datas."

    def handle(self, *args, **options):
        self.stdout.write("Starting deleting all data...")

        with transaction.atomic():
            StockMovement.objects.all().delete()
            Product.objects.all().delete()
            Category.objects.all().delete()
            Supplier.objects.all().delete()

        self.stdout.write("Done cleaning.")
