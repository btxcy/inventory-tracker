from math import cos

from .models import MovementType, Product, StockMovement, MOVEMENT_DIRECTION, Supplier, Category
from django.db import transaction
from django.db.models import F

# exceptions 
class StockError(Exception):
    pass

class InvalidMovementType(StockError):
    def __init__(self, movement_type):
        self.movement_type = movement_type
        super().__init__(f"Unknown movement type: {self.movement_type}")

class InvalidQuantity(StockError):
    def __init__(self, quantity):
        self.quantity = quantity
        super().__init__(f"Invalid Quantity: {self.quantity}")

class InsufficientStock(StockError):
    def __init__(self, product, available, quantity):
        self.product = product
        self.available = available
        self.quantity = quantity
        super().__init__(f"Insufficient stock for {self.product}: requested {self.quantity}, available {self.available}")

class InvalidProduct(StockError):
    def __init__(self, product):
        self.product = product
        super().__init__(f"Invalid Product {self.product}.")

class AlreadyExist(StockError):
    def __init__(self, product):
        self.product = product
        super().__init__(f"Already exist in Storage {self.product.sku} - {self.product.name}.")

# services 

# whenever stock moves, need to use this
def record_movement(*, product, movement_type, quantity, user=None,
                    unit_cost=None, reference="", note=""):
    if quantity <= 0:
        raise InvalidQuantity(quantity)

    try:
        direction = MOVEMENT_DIRECTION[movement_type]
    except KeyError:
        raise InvalidMovementType(movement_type)

    with transaction.atomic():
        product = Product.objects.select_for_update().get(pk=product.pk)

        if direction == -1:
            if product.quantity < quantity:
                raise InsufficientStock(product=product, available=product.quantity,
                                    quantity=quantity)

        movement = StockMovement.objects.create(
            product = product,
            movement_type = movement_type,
            quantity = quantity,
            unit_cost = unit_cost,
            reference = reference,
            note = note,
            created_by = user,
        )

        Product.objects.filter(pk=product.pk).update(
            # dont read numbers to python, ask db update itself
            quantity = F("quantity") + direction * quantity
        )

        product.refresh_from_db()

    return movement

def create_product(*, sku, name, description="", category, supplier, unit, cost_price,
                   sale_price, reorder_level, reorder_quantity, quantity=0, user=None):

    if sku is None or name is None:
        raise InvalidProduct(name)

    with transaction.atomic():

        product = None
        # do have check already, but we want to print pretty message
        exist = Product.objects.filter(sku=sku).first()
        if exist:
            raise AlreadyExist(exist)
        else:
            product = Product.objects.create(
                sku = sku,
                name = name,
                description = description,
                category = category,
                supplier = supplier,
                unit = unit,
                cost_price = cost_price,
                sale_price = sale_price,
                reorder_level = reorder_level,
                reorder_quantity = reorder_quantity,
            )

        if quantity > 0:
            record_movement(
                product = product,
                movement_type = MovementType.PURCHASE,
                quantity = quantity,
                unit_cost = cost_price,
                reference = "Opening Stock",
                user = user,
            )

    product.refresh_from_db()
    return product