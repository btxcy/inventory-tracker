from django.db.models import F
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from rest_framework.response import Response
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from .models import Category, Supplier, Product, StockMovement
from .serializers import CategorySerializer, SupplierSerializer, ProductSerializer, StockMovementCreateSerializer, StockMovementSerializer
from .services import record_movement, create_product, StockError

# Create your views here.
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by("-name")
    serializer_class = CategorySerializer

class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all().order_by("-name")
    serializer_class = SupplierSerializer

class ProductViewSet(viewsets.ModelViewSet):
    # select the related data back
    queryset = Product.objects.select_related("category", "supplier").filter(is_active=True).order_by("-sku")
    serializer_class = ProductSerializer

    filterset_fields = ["category", "supplier", "is_active", "unit"]
    search_fields = ["sku", "name"]
    ordering_fields = ["sku", "name", "quantity", "cost_price"]

    # another new page
    @action(detail=False)
    def low_stock(self, request):
        queryset = self.get_queryset().filter(quantity__lte=F("reorder_level"), is_active=True)
        page = self.paginate_queryset(queryset)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        return Response(self.get_serializer(queryset, many=True).data)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = None
        if request.user.is_authenticated:
            user = request.user
        try:
            data = serializer.validated_data
            quantity = data.pop("opening_quantity", 0)
            created_product = create_product(**data, quantity=quantity, user=user)
        except StockError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        output = ProductSerializer(created_product)
        return Response(output.data, status=status.HTTP_201_CREATED)

# not adding put and delete
class StockMovementViewSet(mixins.ListModelMixin,
                           mixins.RetrieveModelMixin,
                           mixins.CreateModelMixin,
                           viewsets.GenericViewSet):

    queryset = StockMovement.objects.select_related("product", "created_by")

    def get_serializer_class(self):
        if self.action == "create":
            return StockMovementCreateSerializer
        return StockMovementSerializer

    # recreate create method to make it go through record movement
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # user authentication
        user = None
        if request.user.is_authenticated:
            user = request.user
        try:
            movement = record_movement(**serializer.validated_data, user=user)
        except StockError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        output = StockMovementSerializer(movement)
        return Response(output.data, status=status.HTTP_201_CREATED)


@login_required
def dashboard(request):
    return render(request, "dashboard.html")

@login_required
def movements(request):
    return render(request, "movements.html")

@login_required
def destroy_product(request):
    return render(request, "destroy.html")

@login_required
def create_new_product(request):
    return render(request, "new_product.html")