from django.contrib import admin
from .models import Category, Supplier, Product, StockMovement

# just for the list in admin page

# Register your models here.
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ["name", "email", "phone", "lead_time_days", "is_active"]
    search_fields = ["name", "email"]
    list_filter = ["is_active"]

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["sku", "name", "category", "quantity", "reorder_level", "low_stock"]
    search_fields = ["sku", "name"]
    list_filter = ["category", "is_active", "unit"]
    list_select_related = ["category", "supplier"]
    readonly_fields = ["created_at", "updated_at"]

    @admin.display(boolean=True, description="Low stock")
    def low_stock(self, obj):
        return obj.is_low_stock

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ["created_at", "product", "movement_type", "quantity", "created_by"]
    list_filter = ["movement_type", "created_at"]
    search_fields = ["product__sku", "reference"]
    list_select_related = ["product", "created_by"]
    autocomplete_fields = ["product"]
    readonly_fields = ["created_by"]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)