from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAdminUser

from .filters import ProductFilterBackend
from .models import Category, Product
from .pagination import CatalogPagination
from .serializers import (
    CategorySerializer,
    ProductReadSerializer,
    ProductWriteSerializer,
)


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    lookup_field = "slug"
    pagination_class = CatalogPagination

    def get_queryset(self):
        queryset = Category.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_active=True)
        return queryset

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return (AllowAny(),)
        return (IsAdminUser(),)


class ProductViewSet(viewsets.ModelViewSet):
    lookup_field = "slug"
    pagination_class = CatalogPagination
    filter_backends = (ProductFilterBackend,)

    def get_queryset(self):
        queryset = Product.objects.select_related("category")
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_active=True, category__is_active=True)
        return queryset

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return ProductReadSerializer
        return ProductWriteSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return (AllowAny(),)
        return (IsAdminUser(),)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        return self._read_response(product, 201)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        product = self.get_object()
        serializer = self.get_serializer(product, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        return self._read_response(product, 200)

    def _read_response(self, product, response_status):
        from rest_framework.response import Response

        return Response(
            ProductReadSerializer(product, context=self.get_serializer_context()).data,
            status=response_status,
        )
