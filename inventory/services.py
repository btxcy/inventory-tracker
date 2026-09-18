from .models import Product, StockMovement, MOVEMENT_DIRECTION
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