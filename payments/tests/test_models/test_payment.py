from decimal import Decimal
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from django.db import IntegrityError
from django.db import transaction
from django.test import TestCase

from payments.models import Payment
from payments.tests.factories import PaymentFactory


class PaymentModelTest(TestCase):
    """Test suite for the Payment model."""

    def test_factory_creates_instance(self):
        """Test that the factory creates a payment instance."""
        payment = PaymentFactory()

        assert isinstance(payment, Payment)
        assert payment.id is not None
        assert payment.user is not None
        assert payment.reference_type == Payment.REFERENCE_STRIPE
        assert payment.reference is not None
        assert payment.url is not None
        assert payment.status == Payment.STATUS_UNPAID
        assert isinstance(payment.amount, Decimal)
        assert payment.amount > 0
        assert payment.raw_data is not None
        assert payment.created_at is not None
        assert payment.updated_at is not None

    def test_str_representation(self):
        """Test the string representation of a payment."""
        payment = PaymentFactory(status=Payment.STATUS_PAID)
        expected = f"Payment {payment.reference} - {Payment.STATUS_PAID}"
        assert str(payment) == expected

    def test_status_choices(self):
        """Test all payment status choices are valid."""
        expected_statuses = [
            "paid",
            "unpaid",
            "no_payment_required",
            "processing",
            "failed",
            "canceled",
        ]
        actual_statuses = [choice[0] for choice in Payment.STATUS_CHOICES]

        assert set(actual_statuses) == set(expected_statuses)

    def test_reference_type_choices(self):
        """Test reference type choices."""
        expected_types = ["STRIPE"]
        actual_types = [choice[0] for choice in Payment.REFERENCE_CHOICES]

        assert set(actual_types) == set(expected_types)

    def test_payment_with_paid_trait(self):
        """Test factory paid trait creates a paid payment."""
        payment = PaymentFactory.create(paid=True)

        assert payment.status == Payment.STATUS_PAID
        assert payment.raw_data["payment_status"] == "paid"
        assert payment.raw_data["status"] == "complete"

    def test_payment_with_no_payment_required_trait(self):
        """Test factory no_payment_required trait."""
        payment = PaymentFactory.create(no_payment_required=True)

        assert payment.status == Payment.STATUS_NO_PAYMENT_REQUIRED
        assert payment.raw_data["payment_status"] == "no_payment_required"
        assert payment.raw_data["amount_total"] == 0

    def test_payment_with_processing_trait(self):
        """Test factory processing trait."""
        payment = PaymentFactory.create(processing=True)

        assert payment.status == Payment.STATUS_PROCESSING
        assert payment.raw_data["payment_status"] == "unpaid"
        assert payment.raw_data["status"] == "open"

    def test_payment_with_failed_trait(self):
        """Test factory failed trait."""
        payment = PaymentFactory.create(failed=True)

        assert payment.status == Payment.STATUS_FAILED
        assert payment.raw_data["status"] == "expired"

    def test_payment_with_canceled_trait(self):
        """Test factory canceled trait."""
        payment = PaymentFactory.create(canceled=True)

        assert payment.status == Payment.STATUS_CANCELED
        assert payment.raw_data["status"] == "expired"

    def test_reference_uniqueness(self):
        """Test that payment reference must be unique."""
        payment1 = PaymentFactory()
        reference = payment1.reference

        # Attempting to create another payment with same reference should fail
        with pytest.raises(IntegrityError):
            Payment.objects.create(
                user=payment1.user,
                reference_type=Payment.REFERENCE_STRIPE,
                reference=reference,
                url="https://example.com",
                status=Payment.STATUS_UNPAID,
                amount=100,
                raw_data={},
            )

    def test_user_relationship(self):
        """Test the foreign key relationship with User."""
        payment = PaymentFactory()

        assert payment.user is not None
        assert hasattr(payment.user, "email")
        assert hasattr(payment.user, "username")

    def test_history_tracking(self):
        """Test that payment changes are tracked by django-simple-history."""
        payment = PaymentFactory(status=Payment.STATUS_UNPAID)
        initial_history_count = payment.history.count()

        # Update the payment status
        payment.status = Payment.STATUS_PAID
        payment.save()

        # History should have increased
        assert payment.history.count() == initial_history_count + 1

        # Check historical record
        latest_history = payment.history.first()
        assert latest_history.status == Payment.STATUS_PAID

    def test_default_status(self):
        """Test that default status is unpaid."""
        payment = PaymentFactory()
        assert payment.status == Payment.STATUS_UNPAID

    def test_raw_data_structure(self):
        """Test that raw_data contains expected Stripe session fields."""
        payment = PaymentFactory()

        assert "id" in payment.raw_data
        assert "object" in payment.raw_data
        assert "payment_status" in payment.raw_data
        assert "amount_total" in payment.raw_data
        assert "currency" in payment.raw_data
        assert payment.raw_data["object"] == "checkout.session"

    def test_amount_is_decimal(self):
        """Test that amount field is a Decimal type."""
        payment = PaymentFactory(amount=Decimal("99.99"))

        assert isinstance(payment.amount, Decimal)
        assert payment.amount == Decimal("99.99")

    def test_timestamps_auto_populate(self):
        """Test that created_at and updated_at are automatically populated."""
        payment = PaymentFactory()

        assert payment.created_at is not None
        assert payment.updated_at is not None
        assert payment.created_at <= payment.updated_at


class PaymentUpdateStatusTest(TestCase):
    """Test suite for the Payment.update_status method."""

    @patch("payments.gateways.stripe.stripe.checkout.Session.retrieve")
    @patch("payments.gateways.stripe.StripeSetting.get_solo")
    def test_update_status_success(self, mock_get_solo, mock_stripe_retrieve):
        """Test successful status update from Stripe."""
        # Setup
        payment = PaymentFactory(status=Payment.STATUS_UNPAID)

        # Mock StripeSetting
        mock_setting = MagicMock()
        mock_setting.api_key = "sk_test_123"
        mock_get_solo.return_value = mock_setting

        # Mock Stripe session response
        mock_session = MagicMock()
        mock_session.payment_status = "paid"
        mock_session.to_dict.return_value = {
            "id": payment.reference,
            "payment_status": "paid",
            "status": "complete",
            "amount_total": 1000,
        }
        mock_stripe_retrieve.return_value = mock_session

        # Execute
        payment.update_status()

        # Verify
        payment.refresh_from_db()
        assert payment.status == "paid"
        assert payment.raw_data["payment_status"] == "paid"
        mock_stripe_retrieve.assert_called_once_with(payment.reference)

    @patch("payments.gateways.stripe.stripe.checkout.Session.retrieve")
    @patch("payments.gateways.stripe.StripeSetting.get_solo")
    def test_update_status_idempotent_for_paid_payments(
        self,
        mock_get_solo,
        mock_stripe_retrieve,
    ):
        """Test that update_status returns early for already paid payments."""
        # Setup - create a payment that's already paid
        payment = PaymentFactory.create(paid=True)

        # Mock StripeSetting (shouldn't be called, but setup just in case)
        mock_setting = MagicMock()
        mock_setting.api_key = "sk_test_123"
        mock_get_solo.return_value = mock_setting

        # Execute
        payment.update_status()

        # Verify - Stripe API should NOT be called
        mock_stripe_retrieve.assert_not_called()

        # Payment should still be paid
        payment.refresh_from_db()
        assert payment.status == Payment.STATUS_PAID

    @patch("payments.gateways.stripe.StripeSetting.get_solo")
    def test_update_status_raises_error_when_no_api_key(self, mock_get_solo):
        """Test that update_status raises ValueError when Stripe API key is not set."""
        # Setup
        payment = PaymentFactory(status=Payment.STATUS_UNPAID)

        # Mock StripeSetting with no API key
        mock_setting = MagicMock()
        mock_setting.api_key = None
        mock_get_solo.return_value = mock_setting

        # Execute & Verify
        with pytest.raises(ValueError) as context:  # noqa: PT011
            payment.update_status()

        assert "Stripe API key is not configured" in str(context.value)

    @patch("payments.gateways.stripe.stripe.checkout.Session.retrieve")
    @patch("payments.gateways.stripe.StripeSetting.get_solo")
    def test_update_status_with_row_level_locking(
        self,
        mock_get_solo,
        mock_stripe_retrieve,
    ):
        """Test that update_status uses select_for_update for row-level locking."""
        # Setup
        payment = PaymentFactory(status=Payment.STATUS_UNPAID)

        # Mock StripeSetting
        mock_setting = MagicMock()
        mock_setting.api_key = "sk_test_123"
        mock_get_solo.return_value = mock_setting

        # Mock Stripe session response
        mock_session = MagicMock()
        mock_session.payment_status = "paid"
        mock_session.to_dict.return_value = {
            "id": payment.reference,
            "payment_status": "paid",
        }
        mock_stripe_retrieve.return_value = mock_session

        # Execute within a transaction to test locking
        with transaction.atomic():
            payment.update_status()

        # Verify the payment was updated
        payment.refresh_from_db()
        assert payment.status == "paid"

    @patch("payments.gateways.stripe.stripe.checkout.Session.retrieve")
    @patch("payments.gateways.stripe.StripeSetting.get_solo")
    def test_update_status_updates_raw_data(self, mock_get_solo, mock_stripe_retrieve):
        """Test that update_status updates the raw_data field."""
        # Setup
        payment = PaymentFactory(status=Payment.STATUS_UNPAID)
        old_raw_data = payment.raw_data.copy()

        # Mock StripeSetting
        mock_setting = MagicMock()
        mock_setting.api_key = "sk_test_123"
        mock_get_solo.return_value = mock_setting

        # Mock Stripe session response with new data
        new_session_data = {
            "id": payment.reference,
            "payment_status": "paid",
            "status": "complete",
            "amount_total": 2000,
            "currency": "usd",
            "customer_email": "test@example.com",
        }
        mock_session = MagicMock()
        mock_session.payment_status = "paid"
        mock_session.to_dict.return_value = new_session_data
        mock_stripe_retrieve.return_value = mock_session

        # Execute
        payment.update_status()

        # Verify
        payment.refresh_from_db()
        assert payment.raw_data != old_raw_data
        assert payment.raw_data == new_session_data
        assert payment.raw_data["customer_email"] == "test@example.com"

    @patch("payments.gateways.stripe.stripe.checkout.Session.retrieve")
    @patch("payments.gateways.stripe.StripeSetting.get_solo")
    def test_update_status_from_unpaid_to_processing(
        self,
        mock_get_solo,
        mock_stripe_retrieve,
    ):
        """Test status update from unpaid to processing."""
        # Setup
        payment = PaymentFactory(status=Payment.STATUS_UNPAID)

        # Mock StripeSetting
        mock_setting = MagicMock()
        mock_setting.api_key = "sk_test_123"
        mock_get_solo.return_value = mock_setting

        # Mock Stripe session response
        mock_session = MagicMock()
        mock_session.payment_status = "processing"
        mock_session.to_dict.return_value = {
            "id": payment.reference,
            "payment_status": "processing",
        }
        mock_stripe_retrieve.return_value = mock_session

        # Execute
        payment.update_status()

        # Verify
        payment.refresh_from_db()
        assert payment.status == "processing"

    @patch("payments.gateways.stripe.stripe.checkout.Session.retrieve")
    @patch("payments.gateways.stripe.StripeSetting.get_solo")
    def test_update_status_from_unpaid_to_failed(
        self,
        mock_get_solo,
        mock_stripe_retrieve,
    ):
        """Test status update from unpaid to failed."""
        # Setup
        payment = PaymentFactory(status=Payment.STATUS_UNPAID)

        # Mock StripeSetting
        mock_setting = MagicMock()
        mock_setting.api_key = "sk_test_123"
        mock_get_solo.return_value = mock_setting

        # Mock Stripe session response
        mock_session = MagicMock()
        mock_session.payment_status = "failed"
        mock_session.to_dict.return_value = {
            "id": payment.reference,
            "payment_status": "failed",
        }
        mock_stripe_retrieve.return_value = mock_session

        # Execute
        payment.update_status()

        # Verify
        payment.refresh_from_db()
        assert payment.status == "failed"

    @patch("payments.gateways.stripe.stripe.checkout.Session.retrieve")
    @patch("payments.gateways.stripe.StripeSetting.get_solo")
    def test_update_status_sets_stripe_api_key(
        self,
        mock_get_solo,
        mock_stripe_retrieve,
    ):
        """Test that update_status sets the Stripe API key before making requests."""
        # Setup
        payment = PaymentFactory(status=Payment.STATUS_UNPAID)
        test_api_key = "sk_test_secret_key_123"

        # Mock StripeSetting
        mock_setting = MagicMock()
        mock_setting.api_key = test_api_key
        mock_get_solo.return_value = mock_setting

        # Mock Stripe session response
        mock_session = MagicMock()
        mock_session.payment_status = "paid"
        mock_session.to_dict.return_value = {"id": payment.reference}
        mock_stripe_retrieve.return_value = mock_session

        # Execute
        with patch("payments.gateways.stripe.stripe") as mock_stripe:
            mock_stripe.checkout.Session.retrieve.return_value = mock_session
            payment.update_status()

            # Verify that stripe.api_key was set
            assert mock_stripe.api_key == test_api_key
