from django.test import TestCase

from api_logs.models import APIRequestLog
from api_logs.tests.factories import APIRequestLogFactory


class APIRequestLogModelTest(TestCase):
    def test_factory_creates_instance(self):
        """Test that the factory creates an API request log instance."""
        log = APIRequestLogFactory()

        assert isinstance(log, APIRequestLog)
        assert log.method
        assert log.url
        assert log.status in [choice[0] for choice in APIRequestLog.STATUS_CHOICES]
        assert log.created_at is not None
        assert log.updated_at is not None

    def test_str_representation(self):
        """Test the string representation of API request log."""
        log = APIRequestLogFactory(
            method="GET",
            url="https://api.example.com/users/123",
            status=APIRequestLog.STATUS_SUCCESS,
        )

        expected = "GET 123 - success"
        assert str(log) == expected

    def test_str_representation_with_unknown_endpoint(self):
        """Test string representation when URL is empty or None."""
        log = APIRequestLogFactory(
            method="POST",
            url="",
            status=APIRequestLog.STATUS_ERROR,
        )

        expected = "POST unknown - error"
        assert str(log) == expected

    def test_status_choices(self):
        """Test all status choices are valid."""
        expected_statuses = ["pending", "success", "error", "timeout"]
        actual_statuses = [choice[0] for choice in APIRequestLog.STATUS_CHOICES]

        assert set(actual_statuses) == set(expected_statuses)

    def test_default_values(self):
        """Test default values for API request log fields."""
        log = APIRequestLog.objects.create(
            method="GET",
            url="https://api.example.com",
        )

        assert log.status == APIRequestLog.STATUS_PENDING
        assert log.request_headers == {}
        assert log.request_params == {}
        assert log.request_body == {}
        assert log.response_headers == {}
        assert log.response_body == {}
        assert log.response_status_code is None
        assert log.duration_ms is None
        assert log.error_message == ""

    def test_is_successful_property_with_success_status_and_200_response(self):
        """Test is_successful property returns True for successful requests."""
        log = APIRequestLogFactory(
            status=APIRequestLog.STATUS_SUCCESS,
            response_status_code=200,
        )

        assert log.is_successful is True

    def test_is_successful_property_with_success_status_and_201_response(self):
        """Test is_successful property returns True for 201 responses."""
        log = APIRequestLogFactory(
            status=APIRequestLog.STATUS_SUCCESS,
            response_status_code=201,
        )

        assert log.is_successful is True

    def test_is_successful_property_with_success_status_and_299_response(self):
        """Test is_successful property returns True for 299 responses."""
        log = APIRequestLogFactory(
            status=APIRequestLog.STATUS_SUCCESS,
            response_status_code=299,
        )

        assert log.is_successful is True

    def test_is_successful_property_with_error_status(self):
        """Test is_successful property returns False for error status."""
        log = APIRequestLogFactory(
            status=APIRequestLog.STATUS_ERROR,
            response_status_code=200,
        )

        assert log.is_successful is False

    def test_is_successful_property_with_300_response(self):
        """Test is_successful property returns False for 300+ responses."""
        log = APIRequestLogFactory(
            status=APIRequestLog.STATUS_SUCCESS,
            response_status_code=300,
        )

        assert log.is_successful is False

    def test_is_successful_property_with_400_response(self):
        """Test is_successful property returns False for 400 responses."""
        log = APIRequestLogFactory(
            status=APIRequestLog.STATUS_SUCCESS,
            response_status_code=400,
        )

        assert log.is_successful is False

    def test_is_successful_property_with_500_response(self):
        """Test is_successful property returns False for 500 responses."""
        log = APIRequestLogFactory(
            status=APIRequestLog.STATUS_SUCCESS,
            response_status_code=500,
        )

        assert log.is_successful is False

    def test_is_successful_property_with_no_response_code(self):
        """Test is_successful property returns False when response_status_code is None."""  # noqa: E501
        log = APIRequestLogFactory(
            status=APIRequestLog.STATUS_SUCCESS,
            response_status_code=None,
        )

        assert log.is_successful is False

    def test_duration_seconds_property(self):
        """Test duration_seconds property converts milliseconds to seconds."""
        log = APIRequestLogFactory(duration_ms=2500)

        assert log.duration_seconds == 2.5  # 2500ms / 1000  # noqa: PLR2004

    def test_duration_seconds_property_with_none(self):
        """Test duration_seconds property returns None when duration_ms is None."""
        log = APIRequestLogFactory(duration_ms=None)

        assert log.duration_seconds is None

    def test_ordering_by_created_at_descending(self):
        """Test that logs are ordered by created_at in descending order."""
        log1 = APIRequestLogFactory()
        log2 = APIRequestLogFactory()

        logs = APIRequestLog.objects.all()

        # log2 should come first as it was created later
        assert logs.first().id == log2.id
        assert logs.last().id == log1.id

    def test_verbose_names(self):
        """Test model verbose names."""
        meta = APIRequestLog._meta  # noqa: SLF001

        assert meta.verbose_name == "API Request Log"
        assert meta.verbose_name_plural == "API Request Logs"

    def test_field_constraints(self):
        """Test field constraints and types."""
        log = APIRequestLogFactory()

        # Test method field max length
        assert len(log.method) <= 10  # CharField max_length from model  # noqa: PLR2004

        # Test url field max length
        assert len(log.url) <= 500  # URLField max_length from model  # noqa: PLR2004

        # Test status field choices
        assert log.status in [choice[0] for choice in APIRequestLog.STATUS_CHOICES]

    def test_json_fields_are_dicts(self):
        """Test that JSON fields properly store and retrieve dict data."""
        test_data = {"key": "value", "number": 123}

        log = APIRequestLogFactory(
            request_headers=test_data,
            request_params=test_data,
            request_body=test_data,
            response_headers=test_data,
            response_body=test_data,
        )

        # Refresh from database to ensure proper serialization
        log.refresh_from_db()

        assert log.request_headers == test_data
        assert log.request_params == test_data
        assert log.request_body == test_data
        assert log.response_headers == test_data
        assert log.response_body == test_data
