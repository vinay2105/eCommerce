from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination


class CatalogPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_page_size(self, request):
        requested_size = request.query_params.get(self.page_size_query_param)
        if requested_size is None:
            return self.page_size
        try:
            requested_size = int(requested_size)
        except (TypeError, ValueError):
            raise ValidationError({"page_size": "Must be a positive integer."})
        if requested_size < 1:
            raise ValidationError({"page_size": "Must be a positive integer."})
        return min(requested_size, self.max_page_size)
