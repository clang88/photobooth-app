import logging
from unittest.mock import Mock, patch

import pytest
from PIL import Image

from photobooth.plugins.filter_openai.config import FilterOpenAiConfig
from photobooth.plugins.filter_openai.filter_openai import FilterOpenai

logger = logging.getLogger(__name__)


@pytest.fixture()
def filter_openai_plugin():
    """Setup AI filter plugin for testing."""
    plugin = FilterOpenai()
    plugin._config = FilterOpenAiConfig()
    # Configure for testing
    plugin._config.add_userselectable_filter = True
    plugin._config.enable_fallback_on_error = True
    plugin._config.cache_results = False  # Disable caching for tests
    return plugin


@pytest.fixture()
def test_image():
    """Create a test image for processing."""
    return Image.new("RGB", (100, 100), color="red")


def test_mp_avail_filter(filter_openai_plugin):
    """Test that all available filters are returned."""
    filters = filter_openai_plugin.mp_avail_filter()

    assert len(filters) > 0
    assert any("style_transfer" in f for f in filters)
    assert any("enhance" in f for f in filters)


def test_mp_userselectable_filter_enabled(filter_openai_plugin):
    """Test user selectable filters when enabled."""
    filters = filter_openai_plugin.mp_userselectable_filter()

    assert len(filters) > 0
    assert isinstance(filters, list)


def test_mp_userselectable_filter_disabled(filter_openai_plugin):
    """Test user selectable filters when disabled."""
    filter_openai_plugin._config.add_userselectable_filter = False
    filters = filter_openai_plugin.mp_userselectable_filter()

    assert filters == []


def test_unify_deunify(filter_openai_plugin):
    """Test filter name unify/deunify functionality."""
    original_name = "style_transfer"
    unified = filter_openai_plugin.unify(original_name)
    deunified = filter_openai_plugin.deunify(unified)

    assert "FilterOpenai" in unified
    assert deunified == original_name


def test_cache_key_generation(filter_openai_plugin, test_image):
    """Test cache key generation."""
    key1 = filter_openai_plugin._generate_cache_key(test_image, "style_transfer", False)
    key2 = filter_openai_plugin._generate_cache_key(test_image, "style_transfer", False)
    key3 = filter_openai_plugin._generate_cache_key(test_image, "enhance", False)

    # Same parameters should generate same key
    assert key1 == key2
    # Different filter should generate different key
    assert key1 != key3


def test_fallback_on_error(filter_openai_plugin, test_image):
    """Test fallback to original image on error."""
    # Force an error by setting invalid API key
    filter_openai_plugin._config.openai_api_key = ""
    filter_openai_plugin._config.enable_fallback_on_error = True

    # Should return original image on error when fallback is enabled
    result = filter_openai_plugin.mp_filter_pipeline_step(test_image, filter_openai_plugin.unify("style_transfer"), False)

    assert result is test_image


@patch("photobooth.plugins.filter_openai.filter_openai.requests.post")
def test_openai_filter_success(mock_post, filter_openai_plugin, test_image):
    """Test successful OpenAI filter application."""
    # Mock successful API response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [{"b64_json": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="}]
    }
    mock_post.return_value = mock_response

    filter_openai_plugin._config.openai_api_key = "test_key"
    # Enable style_transfer for this test
    for style in filter_openai_plugin._config.style_prompts:
        if style.style_name == "style_transfer":
            style.enabled = True
            break

    result = filter_openai_plugin.do_filter(test_image, "style_transfer", False)

    assert isinstance(result, Image.Image)
    mock_post.assert_called_once()


def test_missing_api_key_error(filter_openai_plugin, test_image):
    """Test error when API key is missing."""
    filter_openai_plugin._config.openai_api_key = ""  # No API key
    filter_openai_plugin._config.enable_fallback_on_error = False

    with pytest.raises(ValueError, match="OpenAI API key not configured"):
        filter_openai_plugin.do_filter(test_image, "style_transfer", False)


def test_cache_functionality(filter_openai_plugin, test_image):
    """Test image caching functionality."""
    filter_openai_plugin._config.cache_results = True

    # Clear cache first
    filter_openai_plugin.clear_cache()
    assert len(filter_openai_plugin._cache) == 0

    # Mock a result to cache
    test_result = Image.new("RGB", (50, 50), color="blue")
    cache_key = filter_openai_plugin._generate_cache_key(test_image, "enhance", False)
    filter_openai_plugin._cache[cache_key] = test_result

    # Verify cache has content
    assert len(filter_openai_plugin._cache) == 1

    # Clear cache again
    filter_openai_plugin.clear_cache()
    assert len(filter_openai_plugin._cache) == 0


def test_base64_conversion(filter_openai_plugin, test_image):
    """Test image to base64 conversion and back."""
    # Convert to base64
    b64_string = filter_openai_plugin._image_to_base64(test_image)
    assert isinstance(b64_string, str)
    assert len(b64_string) > 0

    # Convert back to image
    converted_image = filter_openai_plugin._base64_to_image(b64_string)
    assert isinstance(converted_image, Image.Image)
    assert converted_image.size == test_image.size


def test_custom_prompt_functionality(filter_openai_plugin):
    """Test custom style configuration through style_prompts."""
    # Test adding a custom style prompt
    from photobooth.plugins.filter_openai.models import StylePrompt

    custom_style = StylePrompt(style_name="test_custom", prompt="test custom prompt", enabled=True)
    filter_openai_plugin._config.style_prompts.append(custom_style)

    # Verify the custom style is available
    assert any(style.style_name == "test_custom" for style in filter_openai_plugin._config.style_prompts)

    # Verify custom is in available filters
    filters = filter_openai_plugin.mp_avail_filter()
    assert any("custom" in f for f in filters)


@patch("photobooth.plugins.filter_openai.filter_openai.requests.post")
def test_custom_filter_with_api_call(mock_post, filter_openai_plugin, test_image):
    """Test custom filter functionality with mocked API call."""
    # Mock successful API response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [{"b64_json": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="}]
    }
    mock_post.return_value = mock_response

    filter_openai_plugin._config.openai_api_key = "test_key"
    # Add a custom style to test with
    from photobooth.plugins.filter_openai.models import StylePrompt

    custom_style = StylePrompt(style_name="custom", prompt="my custom test prompt", enabled=True)
    filter_openai_plugin._config.style_prompts.append(custom_style)

    result = filter_openai_plugin.do_filter(test_image, "custom", False)

    assert isinstance(result, Image.Image)
    mock_post.assert_called_once()

    # Verify custom prompt was used in the API call
    call_args = mock_post.call_args
    files_sent = call_args[1]["files"]
    assert files_sent["prompt"][1] == "my custom test prompt"


def test_configurable_parameters(filter_openai_plugin):
    """Test that all new configurable parameters are properly set."""
    # Test default values for parameters that exist in config
    assert filter_openai_plugin._config.input_fidelity == "high"  # Value from loaded config file
    assert filter_openai_plugin._config.output_compression == 85
    assert filter_openai_plugin._config.image_quality == "auto"
    assert filter_openai_plugin._config.image_size == "auto"
    assert filter_openai_plugin._config.timeout_seconds == 300  # Value from loaded config file
    assert filter_openai_plugin._config.enable_fallback_on_error is True
    assert filter_openai_plugin._config.cache_results is False  # Value from loaded config file

    # Test configuration changes
    filter_openai_plugin._config.input_fidelity = "high"
    assert filter_openai_plugin._config.input_fidelity == "high"

    filter_openai_plugin._config.output_compression = 95
    assert filter_openai_plugin._config.output_compression == 95

    # Test that configuration changes are persistent
    assert filter_openai_plugin._config.input_fidelity == "high"
    assert filter_openai_plugin._config.output_compression == 95
