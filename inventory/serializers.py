from rest_framework import serializers
from .models import Category, Supplier, Product, StockMovement

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description", "created_at"]
        read_only_fields = ["id", "created_at"]

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ["id", "name", "email", "phone", "address", "lead_time_days",
                  "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "sku", "name", "description", "category", "supplier",
                  "unit", "cost_price", "sale_price", "quantity", "reorder_level",
                  "reorder_quantity", "is_active", "created_at", "updated_at",
                  "is_low_stock", "category_name", "stock_value", "profit_margin",
                  "opening_quantity"]
        read_only_fields = ["id", "quantity", "created_at", "updated_at"]

    category_name = serializers.CharField(source="category.name", read_only=True)

    is_low_stock = serializers.ReadOnlyField()
    # need this for Float -> Decimal for JSON
    stock_value = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    profit_margin = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    # since quantity is read only, we need this for opening stock
    opening_quantity = serializers.IntegerField(write_only=True, required=False, default=0, min_value=0)

# for GET
class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = ["id", "product", "movement_type", "quantity", "unit_cost", "reference",
                  "note", "created_by", "created_at", "product_sku", "movement_type_display",
                  "signed_quantity"]
        read_only_fields = ["id", "product", "movement_type", "quantity", "unit_cost", 
                            "reference", "note", "created_by", "created_at"]

    # get sku from fk product.sku
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    movement_type_display = serializers.CharField(source="get_movement_type_display", read_only=True)

# for POST
class StockMovementCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = ["id", "product", "movement_type", "quantity", "unit_cost", "reference",
                  "note", "created_by", "created_at"]
        read_only_fields = ["id", "created_by", "created_at"]