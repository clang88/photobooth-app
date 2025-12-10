import logging
import pytest
from unittest.mock import Mock, patch, MagicMock
from PIL import Image

from photobooth.plugins.filter_ai.config import FilterAiConfig
from photobooth.plugins.filter_ai.filter_ai import FilterAi

logger = logging.getLogger(__name__)


@pytest.fixture()
def filter_ai_plugin():
    """Setup AI filter plugin for testing."""
    plugin = FilterAi()
    plugin._config = FilterAiConfig()
    # Configure for testing
    plugin._config.add_userselectable_filter = True
    plugin._config.enable_fallback_on_error = True
    plugin._config.cache_results = False  # Disable caching for tests
    return plugin


@pytest.fixture()
def test_image():
    """Create a test image for processing."""
    return Image.new('RGB', (100, 100), color='red')


def test_mp_avail_filter(filter_ai_plugin):
    """Test that all available filters are returned."""
    filters = filter_ai_plugin.mp_avail_filter()
    
    assert len(filters) > 0
    assert any("style_transfer" in f for f in filters)
    assert any("enhance" in f for f in filters)


def test_mp_userselectable_filter_enabled(filter_ai_plugin):
    """Test user selectable filters when enabled."""
    filters = filter_ai_plugin.mp_userselectable_filter()
    
    assert len(filters) > 0
    assert isinstance(filters, list)


def test_mp_userselectable_filter_disabled(filter_ai_plugin):
    """Test user selectable filters when disabled."""
    filter_ai_plugin._config.add_userselectable_filter = False
    filters = filter_ai_plugin.mp_userselectable_filter()
    
    assert filters == []


def test_unify_deunify(filter_ai_plugin):
    """Test filter name unify/deunify functionality."""
    original_name = "style_transfer"
    unified = filter_ai_plugin.unify(original_name)
    deunified = filter_ai_plugin.deunify(unified)
    
    assert "FilterAi" in unified
    assert deunified == original_name


def test_cache_key_generation(filter_ai_plugin, test_image):
    """Test cache key generation."""
    key1 = filter_ai_plugin._generate_cache_key(test_image, "style_transfer", False)
    key2 = filter_ai_plugin._generate_cache_key(test_image, "style_transfer", False)
    key3 = filter_ai_plugin._generate_cache_key(test_image, "enhance", False)
    
    # Same parameters should generate same key
    assert key1 == key2
    # Different filter should generate different key
    assert key1 != key3


def test_fallback_on_error(filter_ai_plugin, test_image):
    """Test fallback to original image on error."""
    filter_ai_plugin._config.ai_provider = "invalid_provider"
    
    # Should return original image on error when fallback is enabled
    result = filter_ai_plugin.mp_filter_pipeline_step(
        test_image, 
        filter_ai_plugin.unify("style_transfer"), 
        False
    )
    
    assert result is test_image


@patch('photobooth.plugins.filter_ai.filter_ai.requests.post')
def test_openai_filter_success(mock_post, filter_ai_plugin, test_image):
    """Test successful OpenAI filter application."""
    # Mock successful API response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [{"b64_json": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="}]
    }
    mock_post.return_value = mock_response
    
    filter_ai_plugin._config.ai_provider = "openai"
    filter_ai_plugin._config.openai_api_key = "test_key"
    
    result = filter_ai_plugin.do_filter(test_image, "style_transfer", False)
    
    assert isinstance(result, Image.Image)
    mock_post.assert_called_once()


def test_missing_api_key_error(filter_ai_plugin, test_image):
    """Test error when API key is missing."""
    filter_ai_plugin._config.ai_provider = "openai"
    filter_ai_plugin._config.openai_api_key = ""  # No API key
    filter_ai_plugin._config.enable_fallback_on_error = False
    
    with pytest.raises(ValueError, match="OpenAI API key not configured"):
        filter_ai_plugin.do_filter(test_image, "style_transfer", False)


def test_cache_functionality(filter_ai_plugin, test_image):
    """Test image caching functionality."""
    filter_ai_plugin._config.cache_results = True
    
    # Clear cache first
    filter_ai_plugin.clear_cache()
    assert len(filter_ai_plugin._cache) == 0
    
    # Mock a result to cache
    test_result = Image.new('RGB', (50, 50), color='blue')
    cache_key = filter_ai_plugin._generate_cache_key(test_image, "enhance", False)
    filter_ai_plugin._cache[cache_key] = test_result
    
    # Verify cache has content
    assert len(filter_ai_plugin._cache) == 1
    
    # Clear cache again
    filter_ai_plugin.clear_cache()
    assert len(filter_ai_plugin._cache) == 0


def test_base64_conversion(filter_ai_plugin, test_image):
    """Test image to base64 conversion and back."""
    # Convert to base64
    b64_string = filter_ai_plugin._image_to_base64(test_image)
    assert isinstance(b64_string, str)
    assert len(b64_string) > 0
    
    # Convert back to image
    converted_image = filter_ai_plugin._base64_to_image(b64_string)
    assert isinstance(converted_image, Image.Image)
    assert converted_image.size == test_image.size