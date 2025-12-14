import base64
from io import BytesIO
from unittest.mock import Mock
from unittest.mock import patch

import pytest
import requests
from django.test import TestCase
from PIL import Image as PILImage

from instagram.utils import generate_blur_data_url_from_image_url


class TestGenerateBlurDataUrlFromImageUrl(TestCase):
    """Tests for the generate_blur_data_url_from_image_url utility function."""

    @patch("instagram.utils.requests.get")
    def test_generate_blur_data_url_success(self, mock_get):
        """Test successful blur data URL generation with a valid image URL."""
        # Create a test image
        img = PILImage.new("RGB", (100, 100), color="red")
        img_buffer = BytesIO()
        img.save(img_buffer, format="JPEG")
        img_buffer.seek(0)

        # Mock the requests.get response
        mock_response = Mock()
        mock_response.content = img_buffer.read()
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Call the function
        result = generate_blur_data_url_from_image_url("https://example.com/image.jpg")

        # Verify the result is a base64 string
        assert isinstance(result, str)
        assert len(result) > 0

        # Verify it's valid base64
        decoded = base64.b64decode(result)
        assert len(decoded) > 0

        # Verify requests.get was called with correct URL and timeout
        mock_get.assert_called_once_with("https://example.com/image.jpg", timeout=30)

    @patch("instagram.utils.requests.get")
    def test_generate_blur_data_url_custom_resize_percentage(self, mock_get):
        """Test blur data URL generation with custom resize percentage."""
        # Create a test image
        img = PILImage.new("RGB", (100, 100), color="blue")
        img_buffer = BytesIO()
        img.save(img_buffer, format="JPEG")
        img_buffer.seek(0)

        # Mock the requests.get response
        mock_response = Mock()
        mock_response.content = img_buffer.read()
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Call the function with custom resize percentage
        result = generate_blur_data_url_from_image_url(
            "https://example.com/image.jpg",
            resize_percentage=0.05,
        )

        # Verify the result is a base64 string
        assert isinstance(result, str)
        assert len(result) > 0

    @patch("instagram.utils.requests.get")
    def test_generate_blur_data_url_network_error(self, mock_get):
        """Test handling of network errors when fetching image."""
        # Mock a network error
        mock_get.side_effect = requests.exceptions.ConnectionError("Network error")

        # Verify the function raises the exception
        with pytest.raises(requests.exceptions.ConnectionError):
            generate_blur_data_url_from_image_url("https://example.com/image.jpg")

    @patch("instagram.utils.requests.get")
    def test_generate_blur_data_url_http_error(self, mock_get):
        """Test handling of HTTP errors (404, 500, etc.)."""
        # Mock an HTTP error
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Not Found",
        )
        mock_get.return_value = mock_response

        # Verify the function raises the exception
        with pytest.raises(requests.exceptions.HTTPError):
            generate_blur_data_url_from_image_url("https://example.com/image.jpg")

    @patch("instagram.utils.requests.get")
    def test_generate_blur_data_url_invalid_image_data(self, mock_get):
        """Test handling of invalid image data."""
        # Mock response with invalid image data
        mock_response = Mock()
        mock_response.content = b"not an image"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Verify the function raises an exception (PIL raises UnidentifiedImageError)
        with pytest.raises(Exception, match=r".*"):  # PIL will raise an exception
            generate_blur_data_url_from_image_url("https://example.com/image.jpg")

    @patch("instagram.utils.requests.get")
    def test_generate_blur_data_url_returns_valid_base64(self, mock_get):
        """Test that the returned string is valid base64 and can be decoded."""
        # Create a test image
        img = PILImage.new("RGB", (200, 200), color="green")
        img_buffer = BytesIO()
        img.save(img_buffer, format="PNG")
        img_buffer.seek(0)

        # Mock the requests.get response
        mock_response = Mock()
        mock_response.content = img_buffer.read()
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Call the function
        result = generate_blur_data_url_from_image_url("https://example.com/image.png")

        # Verify it's valid base64
        decoded = base64.b64decode(result)
        assert len(decoded) > 0

        # Verify the decoded data is a valid image
        decoded_img = PILImage.open(BytesIO(decoded))
        assert decoded_img.size == (4, 4)  # 200 * 0.02 = 4

    @patch("instagram.utils.requests.get")
    def test_generate_blur_data_url_different_image_formats(self, mock_get):
        """Test blur data URL generation with different image formats."""
        for img_format in ["JPEG", "PNG", "GIF"]:
            # Create a test image
            img = PILImage.new("RGB", (100, 100), color="yellow")
            img_buffer = BytesIO()
            img.save(img_buffer, format=img_format)
            img_buffer.seek(0)

            # Mock the requests.get response
            mock_response = Mock()
            mock_response.content = img_buffer.read()
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            # Call the function
            result = generate_blur_data_url_from_image_url(
                f"https://example.com/image.{img_format.lower()}",
            )

            # Verify the result is a base64 string
            assert isinstance(result, str)
            assert len(result) > 0
