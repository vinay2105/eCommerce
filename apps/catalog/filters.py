from django.db.models import Q
from rest_framework.exceptions import ValidationError
from rest_framework.filters import BaseFilterBackend

from .serializers import ProductFilterSerializer


class ProductFilterBackend(BaseFilterBackend):
    supported_parameters = {
        "search",
        "category",
        "min_price",
        "max_price",
        "ordering",
        "page",
        "page_size",
        "format",
    }

    def filter_queryset(self, request, queryset, view):
        unknown = set(request.query_params) - self.supported_parameters
        if unknown:
            raise ValidationError(
                {
                    "query_params": (
                        f"Unsupported parameter(s): {', '.join(sorted(unknown))}."
                    )
                }
            )

        serializer = ProductFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        filters = serializer.validated_data

        search = filters.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )
        if category := filters.get("category"):
            queryset = queryset.filter(
                category__slug=category, category__is_active=True
            )
        if (min_price := filters.get("min_price")) is not None:
            queryset = queryset.filter(price__gte=min_price)
        if (max_price := filters.get("max_price")) is not None:
            queryset = queryset.filter(price__lte=max_price)
        if min_price is not None and max_price is not None:
            if min_price > max_price:
                raise ValidationError(
                    {"max_price": "Must be greater than or equal to min_price."}
                )
        return queryset.order_by(filters.get("ordering", "name"), "id")
