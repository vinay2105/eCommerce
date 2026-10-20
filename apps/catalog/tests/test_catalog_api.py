from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.catalog.models import Category, Product


class CatalogDocumentationTests(SimpleTestCase):
    def test_openapi_schema_and_swagger_page_are_available(self):
        client = APIClient()
        schema = client.get("/api/schema/", HTTP_HOST="localhost")
        docs = client.get("/api/docs/", HTTP_HOST="localhost")

        self.assertEqual(schema.status_code, 200)
        schema_document = schema.json()
        self.assertTrue(schema_document["openapi"].startswith("3.0."))
        self.assertIn("/api/v1/products/", schema_document["paths"])
        self.assertEqual(docs.status_code, 200)
        self.assertContains(docs, "SwaggerUIBundle")


class CatalogAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name="Books", slug="books")
        self.inactive_category = Category.objects.create(
            name="Hidden", slug="hidden", is_active=False
        )
        self.first_product = self.create_product(
            name="Amber Book", slug="amber-book", sku="BOOK-001", price="12.50"
        )
        self.second_product = self.create_product(
            name="Blue Book", slug="blue-book", sku="BOOK-002", price="8.25"
        )
        self.inactive_product = self.create_product(
            name="Hidden Book",
            slug="hidden-book",
            sku="BOOK-003",
            category=self.inactive_category,
            is_active=True,
        )
        self.unpublished_product = self.create_product(
            name="Draft Book",
            slug="draft-book",
            sku="BOOK-004",
            is_active=False,
        )

    def create_product(self, **overrides):
        values = {
            "name": "Example Book",
            "slug": "example-book",
            "description": "Catalog test item",
            "category": self.category,
            "price": Decimal("10.00"),
            "sku": "EXAMPLE-001",
            "stock_quantity": 5,
        }
        values.update(overrides)
        return Product.objects.create(**values)

    def make_staff(self):
        staff = get_user_model().objects.create_user(
            email="staff@example.com",
            password="Sensible-Staff-Password-984!",
            is_staff=True,
        )
        self.client.force_authenticate(staff)
        return staff

    def test_public_lists_only_active_products_with_stable_shape(self):
        response = self.client.get(reverse("product-list"), HTTP_HOST="localhost")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(
            set(response.data["results"][0]),
            {
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
            },
        )
        self.assertEqual(response.data["results"][0]["category"]["slug"], "books")

    def test_product_detail_hides_inactive_product_and_category(self):
        active = self.client.get(
            reverse("product-detail", kwargs={"slug": self.first_product.slug}),
            HTTP_HOST="localhost",
        )
        inactive_product = self.client.get(
            reverse("product-detail", kwargs={"slug": self.unpublished_product.slug}),
            HTTP_HOST="localhost",
        )
        inactive_category = self.client.get(
            reverse("product-detail", kwargs={"slug": self.inactive_product.slug}),
            HTTP_HOST="localhost",
        )

        self.assertEqual(active.status_code, 200)
        self.assertEqual(inactive_product.status_code, 404)
        self.assertEqual(inactive_category.status_code, 404)

    def test_categories_are_publicly_limited_to_active_categories(self):
        response = self.client.get(reverse("category-list"), HTTP_HOST="localhost")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["slug"] for item in response.data["results"]], ["books"])

    def test_search_category_price_and_ordering_filters(self):
        response = self.client.get(
            reverse("product-list"),
            {
                "search": "blue",
                "category": "books",
                "min_price": "8.00",
                "ordering": "-price",
            },
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["slug"] for item in response.data["results"]], ["blue-book"]
        )

    def test_invalid_and_unknown_query_parameters_return_400(self):
        invalid_price = self.client.get(
            reverse("product-list"), {"min_price": "NaN"}, HTTP_HOST="localhost"
        )
        invalid_range = self.client.get(
            reverse("product-list"),
            {"min_price": "20.00", "max_price": "10.00"},
            HTTP_HOST="localhost",
        )
        unknown = self.client.get(
            reverse("product-list"), {"include_inactive": "true"}, HTTP_HOST="localhost"
        )
        invalid_page_size = self.client.get(
            reverse("product-list"), {"page_size": "0"}, HTTP_HOST="localhost"
        )

        self.assertEqual(invalid_price.status_code, 400)
        self.assertEqual(invalid_range.status_code, 400)
        self.assertEqual(unknown.status_code, 400)
        self.assertEqual(invalid_page_size.status_code, 400)

    def test_pagination_limits_page_size_and_rejects_out_of_range_page(self):
        for index in range(25):
            self.create_product(
                name=f"Extra Book {index}",
                slug=f"extra-book-{index}",
                sku=f"EXTRA-{index:03d}",
            )

        first_page = self.client.get(
            reverse("product-list"), {"page_size": "5"}, HTTP_HOST="localhost"
        )
        oversized = self.client.get(
            reverse("product-list"), {"page_size": "1000"}, HTTP_HOST="localhost"
        )
        missing_page = self.client.get(
            reverse("product-list"), {"page": "999"}, HTTP_HOST="localhost"
        )

        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(len(first_page.data["results"]), 5)
        self.assertEqual(len(oversized.data["results"]), 27)
        self.assertEqual(missing_page.status_code, 404)

    def test_only_staff_can_create_categories_and_products(self):
        anonymous = self.client.post(
            reverse("product-list"), {}, format="json", HTTP_HOST="localhost"
        )
        customer = get_user_model().objects.create_user(
            email="customer@example.com", password="Sensible-Customer-Password-984!"
        )
        self.client.force_authenticate(customer)
        customer_write = self.client.post(
            reverse("category-list"),
            {"name": "Games", "slug": "games"},
            format="json",
            HTTP_HOST="localhost",
        )

        self.assertEqual(anonymous.status_code, 403)
        self.assertEqual(customer_write.status_code, 403)

        self.make_staff()
        category = self.client.post(
            reverse("category-list"),
            {"name": "Games", "slug": "games", "is_active": True},
            format="json",
            HTTP_HOST="localhost",
        )
        product = self.client.post(
            reverse("product-list"),
            {
                "name": "Game Box",
                "slug": "game-box",
                "description": "A game",
                "category_id": self.category.pk,
                "price": "19.99",
                "sku": "GAME-001",
                "stock_quantity": 4,
                "is_active": True,
            },
            format="json",
            HTTP_HOST="localhost",
        )

        self.assertEqual(category.status_code, 201)
        self.assertEqual(product.status_code, 201)
        self.assertEqual(product.data["category"]["slug"], "books")

    def test_customers_cannot_change_product_fields_and_invalid_category_is_rejected(
        self,
    ):
        customer = get_user_model().objects.create_user(
            email="customer@example.com", password="Sensible-Customer-Password-984!"
        )
        self.client.force_authenticate(customer)
        response = self.client.patch(
            reverse("product-detail", kwargs={"slug": self.first_product.slug}),
            {
                "price": "0.01",
                "sku": "CHANGED",
                "is_active": False,
                "stock_quantity": 0,
            },
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(response.status_code, 403)

        self.make_staff()
        invalid_category = self.client.post(
            reverse("product-list"),
            {
                "name": "Bad Category Product",
                "slug": "bad-category-product",
                "category_id": self.inactive_category.pk,
                "price": "5.00",
                "sku": "BAD-CATEGORY-1",
                "stock_quantity": 1,
            },
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(invalid_category.status_code, 400)

    def test_product_list_uses_a_constant_number_of_queries(self):
        for index in range(10):
            self.create_product(
                name=f"Query Book {index}",
                slug=f"query-book-{index}",
                sku=f"QUERY-{index:03d}",
            )

        with self.assertNumQueries(2):
            response = self.client.get(reverse("product-list"), HTTP_HOST="localhost")

        self.assertEqual(response.status_code, 200)
