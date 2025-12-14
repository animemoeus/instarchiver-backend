from decimal import Decimal
from unittest.mock import MagicMock
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from core.users.tests.factories import UserFactory
from instagram.tests.factories import InstagramUserFactory
from payments.models import Payment
from payments.tests.factories import PaymentFactory


class PaymentListCreateAPIViewListTest(TestCase):
    """Test suite for PaymentListCreateAPIView GET (list) endpoint."""

    def setUp(self):
        """Set up test client and common test data."""
        self.client = APIClient()
        self.url = reverse("payments:payment-list-create")
        self.user = UserFactory()

    def test_list_payments_unauthenticated(self):
        """Test that unauthenticated users cannot list payments."""
        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_payments_authenticated_success(self):
        """Test successful retrieval of payments for authenticated user."""
        self.client.force_authenticate(user=self.user)
        PaymentFactory.create_batch(3, user=self.user)

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert len(response.data["results"]) == 3  # noqa: PLR2004

    def test_list_payments_only_shows_user_payments(self):
        """Test that users only see their own payments."""
        other_user = UserFactory()
        self.client.force_authenticate(user=self.user)

        # Create payments for both users
        PaymentFactory.create_batch(2, user=self.user)
        PaymentFactory.create_batch(3, user=other_user)

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 2  # noqa: PLR2004

        # Verify all payments belong to the authenticated user
        for payment in response.data["results"]:
            assert payment["user"]["id"] == self.user.id

    def test_list_payments_empty(self):
        """Test response when user has no payments."""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert len(response.data["results"]) == 0

    def test_list_payments_ordering(self):
        """Test that payments are ordered by created_at descending."""
        self.client.force_authenticate(user=self.user)
        PaymentFactory.create_batch(5, user=self.user)

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]

        # Most recent payment should be first
        created_at_values = [payment["created_at"] for payment in results]
        assert created_at_values == sorted(created_at_values, reverse=True)

    def test_list_payments_pagination(self):
        """Test that pagination works correctly with cursor pagination."""
        self.client.force_authenticate(user=self.user)
        PaymentFactory.create_batch(15, user=self.user)

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert "next" in response.data
        assert "previous" in response.data

    def test_list_payments_response_structure(self):
        """Test that the response contains expected fields."""
        self.client.force_authenticate(user=self.user)
        PaymentFactory(user=self.user)

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results) > 0

        first_payment = results[0]
        expected_fields = [
            "id",
            "amount",
            "status",
            "created_at",
            "user",
            "reference_type",
        ]

        for field in expected_fields:
            assert field in first_payment, f"Field '{field}' missing from response"

    def test_list_payments_different_statuses(self):
        """Test listing payments with different statuses."""
        self.client.force_authenticate(user=self.user)

        PaymentFactory(user=self.user, paid=True)
        PaymentFactory(user=self.user, processing=True)
        PaymentFactory(user=self.user, failed=True)

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results) == 3  # noqa: PLR2004

        statuses = {payment["status"] for payment in results}
        assert Payment.STATUS_PAID in statuses
        assert Payment.STATUS_PROCESSING in statuses
        assert Payment.STATUS_FAILED in statuses


class PaymentListCreateAPIViewCreateTest(TestCase):
    """Test suite for PaymentListCreateAPIView POST (create) endpoint."""

    def setUp(self):
        """Set up test client and common test data."""
        self.client = APIClient()
        self.url = reverse("payments:payment-list-create")
        self.user = UserFactory()
        self.instagram_user = InstagramUserFactory()

    def test_create_payment_unauthenticated(self):
        """Test that unauthenticated users cannot create payments."""
        data = {
            "using": Payment.REFERENCE_STRIPE,
            "type": Payment.TYPE_INSTAGRAM_USER_STORY_CREDIT,
            "target": str(self.instagram_user.uuid),
            "quantity": 10,
        }

        response = self.client.post(self.url, data)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("payments.gateways.stripe.stripe.checkout.Session.create")
    @patch("payments.gateways.stripe.StripeSetting.get_solo")
    def test_create_payment_success(self, mock_get_solo, mock_stripe_create):
        """Test successful payment creation."""
        self.client.force_authenticate(user=self.user)

        # Mock StripeSetting
        mock_setting = MagicMock()
        mock_setting.api_key = "sk_test_123"
        mock_get_solo.return_value = mock_setting

        # Mock Stripe checkout session
        mock_session = MagicMock()
        mock_session.id = "cs_test_123"
        mock_session.url = "https://checkout.stripe.com/test"
        mock_session.amount_total = 1000
        mock_session.to_dict.return_value = {
            "id": "cs_test_123",
            "object": "checkout.session",
            "payment_status": "unpaid",
            "amount_total": 1000,
            "currency": "usd",
        }
        mock_stripe_create.return_value = mock_session

        data = {
            "using": Payment.REFERENCE_STRIPE,
            "type": Payment.TYPE_INSTAGRAM_USER_STORY_CREDIT,
            "target": str(self.instagram_user.uuid),
            "quantity": 10,
        }

        response = self.client.post(self.url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert "id" in response.data
        assert "url" in response.data
        assert "reference" in response.data
        assert "amount" in response.data
        assert response.data["url"] == "https://checkout.stripe.com/test"
        assert response.data["reference"] == "cs_test_123"

        # Verify payment was created in database
        payment = Payment.objects.get(reference="cs_test_123")
        assert payment.user == self.user
        assert payment.reference_type == Payment.REFERENCE_STRIPE
        assert payment.status == Payment.STATUS_UNPAID
        assert payment.type == Payment.TYPE_INSTAGRAM_USER_STORY_CREDIT

    @patch("payments.gateways.stripe.stripe.checkout.Session.create")
    @patch("payments.gateways.stripe.StripeSetting.get_solo")
    def test_create_payment_profile_credit_type(
        self,
        mock_get_solo,
        mock_stripe_create,
    ):
        """Test creating payment with profile credit type."""
        self.client.force_authenticate(user=self.user)

        # Mock StripeSetting
        mock_setting = MagicMock()
        mock_setting.api_key = "sk_test_123"
        mock_get_solo.return_value = mock_setting

        # Mock Stripe checkout session
        mock_session = MagicMock()
        mock_session.id = "cs_test_456"
        mock_session.url = "https://checkout.stripe.com/test"
        mock_session.amount_total = 500
        mock_session.to_dict.return_value = {
            "id": "cs_test_456",
            "object": "checkout.session",
            "payment_status": "unpaid",
            "amount_total": 500,
            "currency": "usd",
        }
        mock_stripe_create.return_value = mock_session

        data = {
            "using": Payment.REFERENCE_STRIPE,
            "type": Payment.TYPE_INSTAGRAM_USER_PROFILE_CREDIT,
            "target": str(self.instagram_user.uuid),
            "quantity": 5,
        }

        response = self.client.post(self.url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED

        # Verify payment type
        payment = Payment.objects.get(reference="cs_test_456")
        assert payment.type == Payment.TYPE_INSTAGRAM_USER_PROFILE_CREDIT

    def test_create_payment_missing_required_fields(self):
        """Test that missing required fields returns validation error."""
        self.client.force_authenticate(user=self.user)

        data = {
            "using": Payment.REFERENCE_STRIPE,
            # Missing type, target, quantity
        }

        response = self.client.post(self.url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "type" in response.data
        assert "target" in response.data
        assert "quantity" in response.data

    def test_create_payment_invalid_using_choice(self):
        """Test that invalid 'using' choice returns validation error."""
        self.client.force_authenticate(user=self.user)

        data = {
            "using": "INVALID_GATEWAY",
            "type": Payment.TYPE_INSTAGRAM_USER_STORY_CREDIT,
            "target": str(self.instagram_user.uuid),
            "quantity": 10,
        }

        response = self.client.post(self.url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "using" in response.data

    def test_create_payment_invalid_type_choice(self):
        """Test that invalid 'type' choice returns validation error."""
        self.client.force_authenticate(user=self.user)

        data = {
            "using": Payment.REFERENCE_STRIPE,
            "type": "INVALID_TYPE",
            "target": str(self.instagram_user.uuid),
            "quantity": 10,
        }

        response = self.client.post(self.url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "type" in response.data

    def test_create_payment_invalid_quantity(self):
        """Test that quantity less than 1 returns validation error."""
        self.client.force_authenticate(user=self.user)

        data = {
            "using": Payment.REFERENCE_STRIPE,
            "type": Payment.TYPE_INSTAGRAM_USER_STORY_CREDIT,
            "target": str(self.instagram_user.uuid),
            "quantity": 0,
        }

        response = self.client.post(self.url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "quantity" in response.data

    def test_create_payment_nonexistent_instagram_user(self):
        """Test that nonexistent Instagram user returns validation error."""
        self.client.force_authenticate(user=self.user)

        data = {
            "using": Payment.REFERENCE_STRIPE,
            "type": Payment.TYPE_INSTAGRAM_USER_STORY_CREDIT,
            "target": "00000000-0000-0000-0000-000000000000",
            "quantity": 10,
        }

        response = self.client.post(self.url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "target" in response.data
        assert "Instagram user not found" in str(response.data["target"])

    @patch("payments.gateways.stripe.StripeSetting.get_solo")
    def test_create_payment_gateway_error(self, mock_get_solo):
        """Test that gateway errors are handled gracefully."""
        self.client.force_authenticate(user=self.user)

        # Mock StripeSetting with no API key to trigger ValueError
        mock_setting = MagicMock()
        mock_setting.api_key = None
        mock_get_solo.return_value = mock_setting

        data = {
            "using": Payment.REFERENCE_STRIPE,
            "type": Payment.TYPE_INSTAGRAM_USER_STORY_CREDIT,
            "target": str(self.instagram_user.uuid),
            "quantity": 10,
        }

        response = self.client.post(self.url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

    @patch("payments.gateways.stripe.stripe.checkout.Session.create")
    @patch("payments.gateways.stripe.StripeSetting.get_solo")
    def test_create_payment_stripe_api_exception(
        self,
        mock_get_solo,
        mock_stripe_create,
    ):
        """Test that Stripe API exceptions are handled gracefully."""
        self.client.force_authenticate(user=self.user)

        # Mock StripeSetting
        mock_setting = MagicMock()
        mock_setting.api_key = "sk_test_123"
        mock_get_solo.return_value = mock_setting

        # Mock Stripe to raise an exception
        mock_stripe_create.side_effect = Exception("Stripe API error")

        data = {
            "using": Payment.REFERENCE_STRIPE,
            "type": Payment.TYPE_INSTAGRAM_USER_STORY_CREDIT,
            "target": str(self.instagram_user.uuid),
            "quantity": 10,
        }

        response = self.client.post(self.url, data, format="json")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "error" in response.data
        assert response.data["error"] == "Failed to create payment"

    @patch("payments.gateways.stripe.stripe.checkout.Session.create")
    @patch("payments.gateways.stripe.StripeSetting.get_solo")
    def test_create_payment_amount_calculation(self, mock_get_solo, mock_stripe_create):
        """Test that payment amount is correctly calculated from Stripe response."""
        self.client.force_authenticate(user=self.user)

        # Mock StripeSetting
        mock_setting = MagicMock()
        mock_setting.api_key = "sk_test_123"
        mock_get_solo.return_value = mock_setting

        # Mock Stripe checkout session with specific amount
        mock_session = MagicMock()
        mock_session.id = "cs_test_789"
        mock_session.url = "https://checkout.stripe.com/test"
        mock_session.amount_total = 2500  # $25.00 in cents
        mock_session.to_dict.return_value = {
            "id": "cs_test_789",
            "object": "checkout.session",
            "payment_status": "unpaid",
            "amount_total": 2500,
            "currency": "usd",
        }
        mock_stripe_create.return_value = mock_session

        data = {
            "using": Payment.REFERENCE_STRIPE,
            "type": Payment.TYPE_INSTAGRAM_USER_STORY_CREDIT,
            "target": str(self.instagram_user.uuid),
            "quantity": 25,
        }

        response = self.client.post(self.url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED

        # Verify amount is correctly converted from cents to dollars
        payment = Payment.objects.get(reference="cs_test_789")
        assert payment.amount == Decimal("25.00")
        assert Decimal(response.data["amount"]) == Decimal("25.00")

    @patch("payments.gateways.stripe.stripe.checkout.Session.create")
    @patch("payments.gateways.stripe.StripeSetting.get_solo")
    def test_create_payment_stores_raw_data(self, mock_get_solo, mock_stripe_create):
        """Test that raw Stripe session data is stored."""
        self.client.force_authenticate(user=self.user)

        # Mock StripeSetting
        mock_setting = MagicMock()
        mock_setting.api_key = "sk_test_123"
        mock_get_solo.return_value = mock_setting

        # Mock Stripe checkout session
        raw_session_data = {
            "id": "cs_test_raw",
            "object": "checkout.session",
            "payment_status": "unpaid",
            "amount_total": 1000,
            "currency": "usd",
            "mode": "payment",
            "customer_email": "test@example.com",
        }
        mock_session = MagicMock()
        mock_session.id = "cs_test_raw"
        mock_session.url = "https://checkout.stripe.com/test"
        mock_session.amount_total = 1000
        mock_session.to_dict.return_value = raw_session_data
        mock_stripe_create.return_value = mock_session

        data = {
            "using": Payment.REFERENCE_STRIPE,
            "type": Payment.TYPE_INSTAGRAM_USER_STORY_CREDIT,
            "target": str(self.instagram_user.uuid),
            "quantity": 10,
        }

        response = self.client.post(self.url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED

        # Verify raw_data is stored
        payment = Payment.objects.get(reference="cs_test_raw")
        assert payment.raw_data == raw_session_data
        assert payment.raw_data["customer_email"] == "test@example.com"

    def test_create_payment_only_accepts_post_method(self):
        """Test that the create endpoint only accepts POST requests."""
        self.client.force_authenticate(user=self.user)

        # PUT method should not be allowed for creation
        response = self.client.put(self.url, {})
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        # PATCH method should not be allowed
        response = self.client.patch(self.url, {})
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        # DELETE method should not be allowed
        response = self.client.delete(self.url)
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
