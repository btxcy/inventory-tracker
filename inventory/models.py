from django.db import models
from django.conf import settings
from decimal import Decimal

# Create your models here.

# some enums

class Unit(models.TextChoices):
    EACH = "EACH", "Each"
    KG = "KG", "Kilogram"
    LITRE = "LITRE", "Litre"
    BOX = "BOX", "Box"

class MovementType(models.TextChoices):
    PURCHASE = "PURCHASE", "Purchase"
    RETURN_IN = "RETURN_IN", "Customer Return"
    ADJUSTMENT_IN = "ADJUSTMENT_IN", "Adjustment (In)"
    SALE = "SALE", "Sale"
    DAMAGE = "DAMAGE", "Damage"
    ADJUSTMENT_OUT = "ADJUSTMENT_OUT", "Adjustment (Out)"

MOVEMENT_DIRECTION = {
    MovementType.PURCHASE: 1,
    MovementType.RETURN_IN: 1,
    MovementType.ADJUSTMENT_IN: 1,
    MovementType.SALE: -1,
    MovementType.DAMAGE: -1,
    MovementType.ADJUSTMENT_OUT: -1,
}

# models

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        ordering = ["name"]

class Supplier(models.Model):
    name = models.CharField(max_length=150, db_index=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    lead_time_days = models.PositiveIntegerField(default=7)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        ordering = ["name"]

class Product(models.Model):
    sku = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200, db_index=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="supplied_products"
    )
    unit = models.CharField(max_length=10, choices=Unit.choices, default=Unit.EACH)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=10)
    reorder_quantity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_low_stock(self):
        return self.quantity <= self.reorder_level

    @property
    def profit_margin(self):
        if not self.sale_price:
            return Decimal("0.00")
        profit = self.sale_price - self.cost_price
        return (profit / self.sale_price * 100).quantize(Decimal("0.01"))

    @property
    def stock_value(self):
        return self.quantity * self.cost_price

    def __str__(self):
        return f"{self.sku} - {self.name}"

    class Meta:
        ordering = ["sku"]

class StockMovement(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="movements",
    )
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    quantity = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    reference = models.CharField(max_length=100, blank=True)
    note = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movements",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    @property
    def signed_quantity(self):
        return self.quantity * MOVEMENT_DIRECTION[self.movement_type]

    def __str__(self):
        return f"{self.get_movement_type_display()} {self.quantity} x {self.product.sku}"
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["product", "-created_at"])]
