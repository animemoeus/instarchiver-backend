from django.test import TestCase

from settings.models import OpenAISetting
from settings.tests.factories import OpenAISettingFactory


class OpenAISettingModelTest(TestCase):
    def test_factory_creates_instance(self):
        """Test that the factory creates an OpenAI setting instance."""
        setting = OpenAISettingFactory()

        assert isinstance(setting, OpenAISetting)
        assert setting.api_key
        assert setting.model_name
        assert setting.created_at is not None
        assert setting.updated_at is not None

    def test_singleton_behavior(self):
        """Test that OpenAI setting maintains singleton behavior."""
        # Clear any existing instances first
        OpenAISetting.objects.all().delete()

        setting1 = OpenAISettingFactory()
        # Since it's a singleton model, getting another instance should return the same one  # noqa: E501
        setting2 = OpenAISetting.get_solo()

        # Both should reference the same instance
        assert setting1.id == setting2.id
        assert OpenAISetting.objects.count() == 1

    def test_str_representation(self):
        """Test the string representation of OpenAI setting."""
        setting = OpenAISettingFactory()

        assert str(setting) == "OpenAI Settings"

    def test_default_values(self):
        """Test default values for OpenAI setting fields."""
        setting = OpenAISetting.objects.create()

        assert setting.api_key == ""
        assert setting.model_name == ""
        assert setting.created_at is not None
        assert setting.updated_at is not None

    def test_field_lengths(self):
        """Test field length constraints."""
        setting = OpenAISettingFactory()

        # Test api_key max length (from model definition)
        assert len(setting.api_key) <= 255  # noqa: PLR2004

        # Test model_name max length (from model definition)
        assert len(setting.model_name) <= 100  # noqa: PLR2004

    def test_factory_generates_realistic_data(self):
        """Test that factory generates realistic OpenAI data."""
        setting = OpenAISettingFactory()

        # Check that model_name is one of the expected values
        expected_models = (
            "gpt-4",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
            "gpt-4o",
            "gpt-4o-mini",
        )
        assert setting.model_name in expected_models

        # Check that api_key looks like a reasonable length for an API key
        assert len(setting.api_key) > 20  # noqa: PLR2004
