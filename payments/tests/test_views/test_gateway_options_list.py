from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from core.users.tests.factories import UserFactory
from payments.models import Payment
from payments.tests.factories import GatewayOptionFactory


class GatewayOptionsListAPIViewTest(TestCase):
    """Test suite for GatewayOptionsListAPIView GET endpoint."""

    def setUp(self):
        """Set up test client and common test data."""
        self.client = APIClient()
        self.url = reverse("payments:gateway-options-list")

    def test_list_gateway_options_unauthenticated_success(self):
        """Test that unauthenticated users can access the endpoint."""
        GatewayOptionFactory(name="STRIPE")
        GatewayOptionFactory(name="PAYPAL")

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2  # noqa: PLR2004

    def test_list_gateway_options_authenticated_success(self):
        """Test that authenticated users can access the endpoint."""
        user = UserFactory()
        self.client.force_authenticate(user=user)
        GatewayOptionFactory(name="STRIPE")
        GatewayOptionFactory(name="PAYPAL")
        GatewayOptionFactory(name="RAZORPAY")

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 3  # noqa: PLR2004

    def test_list_gateway_options_only_active(self):
        """Test that only active gateway options are returned."""
        # Create active gateway options
        active_gateway_1 = GatewayOptionFactory(name=Payment.REFERENCE_STRIPE)

        # Create inactive gateway options
        GatewayOptionFactory(name="INACTIVE_GATEWAY_1", inactive=True)
        GatewayOptionFactory(name="INACTIVE_GATEWAY_2", inactive=True)

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

        # Verify only active gateway is returned
        assert response.data[0]["id"] == active_gateway_1.id
        assert response.data[0]["name"] == Payment.REFERENCE_STRIPE

    def test_list_gateway_options_response_structure(self):
        """Test that the response contains expected fields."""
        gateway = GatewayOptionFactory()

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) > 0

        first_gateway = response.data[0]
        expected_fields = ["id", "name"]

        for field in expected_fields:
            assert field in first_gateway, f"Field '{field}' missing from response"

        # Verify field values
        assert first_gateway["id"] == gateway.id
        assert first_gateway["name"] == gateway.name

    def test_list_gateway_options_empty(self):
        """Test response when no active gateway options exist."""
        # Create only inactive gateways
        GatewayOptionFactory(name="INACTIVE", inactive=True)

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0
        assert response.data == []

    def test_list_gateway_options_multiple(self):
        """Test listing multiple active gateway options."""
        # Create multiple active gateways with different names
        gateway_1 = GatewayOptionFactory(name=Payment.REFERENCE_STRIPE)
        gateway_2 = GatewayOptionFactory(name="PAYPAL")
        gateway_3 = GatewayOptionFactory(name="RAZORPAY")

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 3  # noqa: PLR2004

        # Verify all gateways are returned
        gateway_ids = {gateway["id"] for gateway in response.data}
        assert gateway_1.id in gateway_ids
        assert gateway_2.id in gateway_ids
        assert gateway_3.id in gateway_ids

    def test_list_gateway_options_only_get_allowed(self):
        """Test that only GET method is allowed."""
        # POST method should not be allowed
        response = self.client.post(self.url, {})
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        # PUT method should not be allowed
        response = self.client.put(self.url, {})
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        # PATCH method should not be allowed
        response = self.client.patch(self.url, {})
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        # DELETE method should not be allowed
        response = self.client.delete(self.url)
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_list_gateway_options_mixed_active_inactive(self):
        """Test filtering with a mix of active and inactive gateway options."""
        # Create a mix of active and inactive gateways
        active_1 = GatewayOptionFactory(name="STRIPE")
        active_2 = GatewayOptionFactory(name="PAYPAL")
        GatewayOptionFactory(name="INACTIVE_1", inactive=True)
        active_3 = GatewayOptionFactory(name="RAZORPAY")
        GatewayOptionFactory(name="INACTIVE_2", inactive=True)

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 3  # noqa: PLR2004

        # Verify only active gateways are returned
        gateway_ids = {gateway["id"] for gateway in response.data}
        assert active_1.id in gateway_ids
        assert active_2.id in gateway_ids
        assert active_3.id in gateway_ids

        # Verify response contains correct names
        gateway_names = {gateway["name"] for gateway in response.data}
        assert "STRIPE" in gateway_names
        assert "PAYPAL" in gateway_names
        assert "RAZORPAY" in gateway_names
        assert "INACTIVE_1" not in gateway_names
        assert "INACTIVE_2" not in gateway_names
