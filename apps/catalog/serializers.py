from decimal import Decimal

from rest_framework import serializers

from .models import Category, Product


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class CategorySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug")
        read_only_fields = fields


class ProductReadSerializer(serializers.ModelSerializer):
    category = CategorySummarySerializer(read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "category",
            "price",
            "sku",
            "stock_quantity",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ProductWriteSerializer(serializers.ModelSerializer):
    category_id = serializers.PrimaryKeyRelatedField(
        source="category", queryset=Category.objects.filter(is_active=True)
    )
    price = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0.00")
    )
    stock_quantity = serializers.IntegerField(min_value=0)

    class Meta:
        model = Product
        fields = (
            "name",
            "slug",
            "description",
            "category_id",
            "price",
            "sku",
            "stock_quantity",
            "is_active",
        )


class ProductFilterSerializer(serializers.Serializer):
    search = serializers.CharField(required=False, max_length=100, allow_blank=True)
    category = serializers.SlugField(required=False)
    min_price = serializers.DecimalField(
        required=False, max_digits=10, decimal_places=2, min_value=Decimal("0.00")
    )
    max_price = serializers.DecimalField(
        required=False, max_digits=10, decimal_places=2, min_value=Decimal("0.00")
    )
    ordering = serializers.ChoiceField(
        required=False,
        choices=("name", "-name", "price", "-price", "created_at", "-created_at"),
    )
