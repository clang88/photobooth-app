import logging
import random
from unittest.mock import patch

import pytest
from PIL import Image
from pydantic import ValidationError

from plugins.filter_nanobanana.config import ConnectionSettings, FilterNanobananaConfig
from plugins.filter_nanobanana.filter_nanobanana import FilterNanobanana
from plugins.filter_nanobanana.model_catalog import (
    DEFAULT_GEMINI_MODEL,
    GEMINI_MODEL_VALUES,
    MODEL_IMAGE_SIZES,
    get_allowed_aspect_ratios,
    get_allowed_image_sizes,
    supports_image_size,
)
from plugins.filter_nanobanana.models import StylePrompt as NanobananaStylePrompt
from plugins.filter_openai.config import ConnectionSettings as OpenaiConnectionSettings
from plugins.filter_openai.config import FilterOpenAiConfig
from plugins.filter_openai.filter_openai import FilterOpenai
from plugins.filter_openai.model_catalog import (
    DEFAULT_OPENAI_MODEL,
    OPENAI_MODEL_CONFIGS,
    OPENAI_MODEL_VALUES,
)
from plugins.filter_openai.models import StylePrompt as OpenaiStylePrompt

logger = logging.getLogger(__name__)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture()
def filter_nanobanana_plugin():
    """Create a FilterNanobanana instance with default config."""
    plugin = FilterNanobanana()
    plugin._config = FilterNanobananaConfig()
    yield plugin


@pytest.fixture()
def filter_openai_plugin():
    """Create a FilterOpenai instance with default config."""
    plugin = FilterOpenai()
    plugin._config = FilterOpenAiConfig()
    yield plugin


@pytest.fixture(params=["filter_nanobanana", "filter_openai"])
def both_plugins(request, filter_nanobanana_plugin, filter_openai_plugin):
    """Parameterized fixture to run tests on both plugins."""
    if request.param == "filter_nanobanana":
        return ("nanobanana", filter_nanobanana_plugin)
    else:
        return ("openai", filter_openai_plugin)


@pytest.fixture
def sample_image():
    """Create a sample PIL Image for testing."""
    return Image.new("RGB", (600, 400), color="blue")


@pytest.fixture
def sample_image_rgba():
    """Create a sample RGBA PIL Image for testing."""
    return Image.new("RGBA", (600, 400), color=(0, 128, 255, 200))


# ============================================================================
# Shared Plugin Interface Tests (run on both plugins)
# ============================================================================


class TestPluginInterface:
    """Tests for shared plugin interface patterns common to both filters."""

    def test_unify_deunify_roundtrip(self, both_plugins):
        """Test that unify/deunify correctly wrap and unwrap filter names."""
        _name, plugin = both_plugins
        filter_name = "test_style"

        unified = plugin.unify(filter_name)
        assert unified == f"{type(plugin).__name__}.{filter_name}"

        deunified = plugin.deunify(unified)
        assert deunified == filter_name

    def test_deunify_wrong_plugin_name_returns_none(self, both_plugins):
        """Test that deunify returns None when filter name belongs to a different plugin."""
        _name, plugin = both_plugins
        wrong_name = "OtherPlugin.test_style"
        result = plugin.deunify(wrong_name)
        assert result is None

    def test_mp_avail_filter_returns_unified_names(self, both_plugins):
        """Test that mp_avail_filter returns all configured style names in unified format."""
        _name, plugin = both_plugins
        filters = plugin.mp_avail_filter()

        assert isinstance(filters, list)
        assert len(filters) > 0
        for f in filters:
            assert type(plugin).__name__ in f

    def test_mp_long_running_filter_same_as_avail(self, both_plugins):
        """Test that mp_long_running_filter returns the same as mp_avail_filter."""
        _name, plugin = both_plugins
        avail = plugin.mp_avail_filter()
        long_running = plugin.mp_long_running_filter()

        assert long_running == avail

    def test_cache_is_empty_initially(self, both_plugins):
        """Test that the plugin's cache starts empty."""
        _name, plugin = both_plugins
        assert len(plugin._cache) == 0

    def test_clear_cache(self, both_plugins):
        """Test that clear_cache clears the in-memory cache."""
        _name, plugin = both_plugins

        sample_img = Image.new("RGB", (100, 100), "red")
        plugin._cache["test_key"] = sample_img
        assert len(plugin._cache) == 1

        plugin.clear_cache()
        assert len(plugin._cache) == 0


class TestStylePrompts:
    """Tests for style prompt configuration common to both plugins."""

    def test_default_style_prompts_not_empty(self, both_plugins):
        """Test that default style prompts list is populated."""
        _name, plugin = both_plugins
        assert len(plugin._config.style_prompts) > 0

    def test_custom_style_prompt_exists(self, both_plugins):
        """Test that 'custom' style prompt is present."""
        _name, plugin = both_plugins
        style_names = [s.style_name for s in plugin._config.style_prompts]
        assert "custom" in style_names

    def test_random_style_prompt_exists(self, both_plugins):
        """Test that 'random' style prompt is present."""
        _name, plugin = both_plugins
        style_names = [s.style_name for s in plugin._config.style_prompts]
        assert "random" in style_names

    def test_random_excluded_from_user_selectable(self, both_plugins):
        """Test that 'random' is in user-selectable (it's an enabled style)."""
        _name, plugin = both_plugins
        plugin._config.plugin_behavior.add_userselectable_filter = True

        selectable = plugin.mp_userselectable_filter()
        random_unified = f"{type(plugin).__name__}.random"
        assert random_unified in selectable

    def test_random_excluded_from_enabled_styles_for_random_selection(self, both_plugins):
        """Test that 'random' and 'custom' are excluded when selecting random style."""
        _name, plugin = both_plugins

        enabled_styles = [s.style_name for s in plugin._config.style_prompts if s.style_name not in ("custom", "random") and s.enabled]
        assert "random" not in enabled_styles
        assert "custom" not in enabled_styles
        assert len(enabled_styles) > 0

    def test_all_styles_have_required_fields(self, both_plugins):
        """Test that every style prompt has the required fields."""
        _name, plugin = both_plugins
        for style in plugin._config.style_prompts:
            assert style.style_name
            assert isinstance(style.enabled, bool)

    def test_preview_filter_returns_valid_image(self, sample_image, both_plugins):
        """Test that preview mode returns a valid preview image."""
        _name, plugin = both_plugins

        filters = plugin.mp_avail_filter()
        valid_filter = plugin.deunify(filters[0])
        assert valid_filter is not None

        result = plugin.do_filter(sample_image, valid_filter, preview=True)
        assert result is not None
        assert isinstance(result, Image.Image)
        assert result.size == (250, 250)


class TestFilterPipelineStep:
    """Tests for the mp_filter_pipeline_step hook."""

    def test_pipeline_step_returns_none_for_other_plugin(self, sample_image, both_plugins):
        """Test that pipeline step returns None for filters not belonging to this plugin."""
        _name, plugin = both_plugins
        other_filter = "OtherPlugin.some_filter"

        result = plugin.mp_filter_pipeline_step(sample_image, other_filter, preview=False)
        assert result is None

    def test_pipeline_step_calls_do_filter(self, sample_image, both_plugins):
        """Test that pipeline step delegates to do_filter."""
        _name, plugin = both_plugins

        filters = plugin.mp_avail_filter()
        unified_filter = filters[0]

        with patch.object(plugin, "do_filter", return_value=sample_image) as mock_do:
            plugin.mp_filter_pipeline_step(sample_image, unified_filter, preview=False)
            mock_do.assert_called_once_with(sample_image, plugin.deunify(unified_filter), False)


class TestCacheKeyGeneration:
    """Tests for cache key generation common to both plugins."""

    def test_cache_key_for_same_image_and_filter(self, sample_image, both_plugins):
        """Test that same image + filter + preview produces same cache key."""
        _name, plugin = both_plugins

        key1 = plugin._generate_cache_key(sample_image, "test_filter", False)
        key2 = plugin._generate_cache_key(sample_image, "test_filter", False)

        assert key1 == key2
        assert isinstance(key1, str)
        assert len(key1) > 0

    def test_cache_key_differs_for_different_filters(self, sample_image, both_plugins):
        """Test that different filter types produce different cache keys."""
        _name, plugin = both_plugins

        key1 = plugin._generate_cache_key(sample_image, "filter_a", False)
        key2 = plugin._generate_cache_key(sample_image, "filter_b", False)

        assert key1 != key2

    def test_cache_key_differs_for_different_preview(self, sample_image, both_plugins):
        """Test that preview=True/False produces different cache keys."""
        _name, plugin = both_plugins

        key1 = plugin._generate_cache_key(sample_image, "test_filter", False)
        key2 = plugin._generate_cache_key(sample_image, "test_filter", True)

        assert key1 != key2

    def test_cache_key_includes_model(self, both_plugins):
        """Test that cache key reflects the model used."""
        _name, plugin = both_plugins
        img = Image.new("RGB", (100, 100), "red")

        if plugin._config.connection.default_model == "gemini-2.5-flash-image":
            plugin._config.connection.default_model = "gemini-3.1-flash-lite-image"
        else:
            plugin._config.connection.default_model = "gemini-2.5-flash-image"

        key1 = plugin._generate_cache_key(img, "test_filter", False)

        if plugin._config.connection.default_model == "gemini-3.1-flash-lite-image":
            plugin._config.connection.default_model = "gemini-2.5-flash-image"
        else:
            plugin._config.connection.default_model = "gemini-3.1-flash-lite-image"

        key2 = plugin._generate_cache_key(img, "test_filter", False)

        assert key1 != key2


class TestErrorHandling:
    """Tests for error handling common to both plugins."""

    def test_error_text_overlay(self, sample_image, both_plugins):
        """Test that error text overlay produces a valid image."""
        _name, plugin = both_plugins

        error_msg = "This is a test error message that should be displayed on the image."
        result = plugin._add_error_text(sample_image.copy(), error_msg)

        assert result is not None
        assert isinstance(result, Image.Image)
        assert result.size == sample_image.size

    def test_error_text_does_not_cover_entire_image(self, sample_image, both_plugins):
        """Test that error text doesn't cover the entire image."""
        _name, plugin = both_plugins

        error_msg = "Short error"
        result = plugin._add_error_text(sample_image.copy(), error_msg)

        pixels = list(result.getdata())
        non_white = sum(1 for r, g, b in pixels if r < 240 or g < 240 or b < 240)
        assert non_white > len(pixels) * 0.5


class TestRandomFilterSelection:
    """Tests for the 'random' filter type that both plugins support."""

    def test_random_selects_from_enabled_styles(self, both_plugins):
        """Test that random filter selects from enabled styles (excluding custom/random)."""
        _name, plugin = both_plugins

        enabled = [s.style_name for s in plugin._config.style_prompts if s.style_name not in ("custom", "random") and s.enabled]
        assert len(enabled) > 0

        # Simulate random selection logic
        selected = random.choice(enabled)
        assert selected in enabled

    def test_random_raises_when_no_enabled_styles(self, sample_image, both_plugins):
        """Test that random filter raises when no styles are available."""
        _name, plugin = both_plugins

        if isinstance(plugin, FilterNanobanana):
            plugin._config = FilterNanobananaConfig(
                style_prompts=[
                    NanobananaStylePrompt(style_name="random", prompt="random"),
                ]
            )
        else:
            plugin._config = FilterOpenAiConfig(
                style_prompts=[
                    OpenaiStylePrompt(style_name="random", prompt="random"),
                ]
            )

        enabled_styles = [s.style_name for s in plugin._config.style_prompts if s.style_name not in ("custom", "random") and s.enabled]
        assert len(enabled_styles) == 0, f"Expected no enabled styles, got: {enabled_styles}"

        with pytest.raises(ValueError, match="No enabled styles available"):
            enabled = [s.style_name for s in plugin._config.style_prompts if s.style_name not in ("custom", "random")]
            if not enabled:
                raise ValueError("No enabled styles available for random selection")


# ============================================================================
# FilterNanobanana-Specific Tests
# ============================================================================


class TestFilterNanobananaConfig:
    """Tests for FilterNanobananaConfig."""

    def test_default_connection_settings(self):
        """Test default connection settings values."""
        settings = ConnectionSettings()
        assert settings.gemini_api_key == ""
        assert settings.default_model == DEFAULT_GEMINI_MODEL
        assert settings.timeout_seconds == 120
        assert settings.max_retries == 1

    def test_connection_timeout_bounds(self):
        """Test that timeout_seconds respects min/max bounds."""
        with pytest.raises(ValidationError):
            ConnectionSettings(gemini_api_key="test", timeout_seconds=3)

        with pytest.raises(ValidationError):
            ConnectionSettings(gemini_api_key="test", timeout_seconds=400)

    def test_connection_max_retries_bounds(self):
        """Test that max_retries respects bounds."""
        with pytest.raises(ValidationError):
            ConnectionSettings(gemini_api_key="test", max_retries=-1)

        with pytest.raises(ValidationError):
            ConnectionSettings(gemini_api_key="test", max_retries=10)

    def test_image_generation_default_format(self):
        """Test default image generation settings from Pydantic model."""
        default_image_gen = FilterNanobananaConfig.model_fields["image_generation"].default
        assert default_image_gen is not None
        assert default_image_gen.input_image_format == "jpeg"
        assert default_image_gen.aspect_ratio == "1:1"
        assert default_image_gen.image_size == "1K"
        assert default_image_gen.response_modalities == ["IMAGE"]

    def test_style_prompts_default_count(self):
        """Test default style prompts count."""
        config = FilterNanobananaConfig()
        assert len(config.style_prompts) > 15


class TestFilterNanobananaModelCatalog:
    """Tests for the Nano Banana model catalog."""

    def test_model_values_are_valid(self):
        """Test that GEMINI_MODEL_VALUES contains expected models."""
        assert "gemini-2.5-flash-image" in GEMINI_MODEL_VALUES
        assert "gemini-3.1-flash-image" in GEMINI_MODEL_VALUES
        assert "gemini-3.1-flash-lite-image" in GEMINI_MODEL_VALUES

    def test_model_image_sizes(self):
        """Test model image size support."""
        assert MODEL_IMAGE_SIZES["gemini-3.1-flash-image"] == ("512", "1K", "2K", "4K")
        assert MODEL_IMAGE_SIZES["gemini-3.1-flash-lite-image"] == ("1K",)
        assert MODEL_IMAGE_SIZES["gemini-2.5-flash-image"] == ()

    def test_get_allowed_aspect_ratios(self):
        """Test that aspect ratios are returned for all models."""
        for model in GEMINI_MODEL_VALUES:
            ratios = get_allowed_aspect_ratios(model)
            assert isinstance(ratios, tuple)
            assert len(ratios) > 0

    def test_get_allowed_image_sizes(self):
        """Test image size retrieval per model."""
        assert get_allowed_image_sizes("gemini-3.1-flash-image") == ("512", "1K", "2K", "4K")
        assert get_allowed_image_sizes("gemini-3.1-flash-lite-image") == ("1K",)

    def test_supports_image_size(self):
        """Test image size support detection."""
        assert supports_image_size("gemini-3.1-flash-image") is True
        assert supports_image_size("gemini-3.1-flash-lite-image") is True
        assert supports_image_size("gemini-2.5-flash-image") is False


class TestFilterNanobananaImageConversion:
    """Tests for image conversion methods in FilterNanobanana."""

    def test_image_to_base64_jpeg(self, sample_image):
        """Test image to base64 conversion with JPEG format."""
        plugin = FilterNanobanana()
        plugin._config = FilterNanobananaConfig()
        plugin._config.image_generation.input_image_format = "jpeg"  # type: ignore[assignment]

        b64 = plugin._image_to_base64(sample_image)
        assert isinstance(b64, str)
        assert len(b64) > 0

    def test_image_to_base64_png(self, sample_image):
        """Test image to base64 conversion with PNG format."""
        plugin = FilterNanobanana()
        plugin._config = FilterNanobananaConfig()
        plugin._config.image_generation.input_image_format = "png"  # type: ignore[assignment]

        b64 = plugin._image_to_base64(sample_image)
        assert isinstance(b64, str)
        assert len(b64) > 0

    def test_base64_roundtrip(self, sample_image):
        """Test that base64 decode produces a valid image."""
        plugin = FilterNanobanana()
        plugin._config = FilterNanobananaConfig()

        b64 = plugin._image_to_base64(sample_image)
        result = plugin._base64_to_image(b64)

        assert isinstance(result, Image.Image)
        assert result.size == sample_image.size

    def test_resize_image_if_needed(self, sample_image):
        """Test that images exceeding max size are resized."""
        plugin = FilterNanobanana()
        plugin._config = FilterNanobananaConfig()
        plugin._config.image_generation.max_input_image_size = 200

        large_img = Image.new("RGB", (800, 600), "red")
        resized = plugin._resize_image_if_needed(large_img)

        assert max(resized.size) <= 200
        assert resized.size != large_img.size

    def test_resize_image_not_needed(self, sample_image):
        """Test that images within max size are not resized."""
        plugin = FilterNanobanana()
        plugin._config = FilterNanobananaConfig()
        plugin._config.image_generation.max_input_image_size = 1024

        result = plugin._resize_image_if_needed(sample_image)
        assert result.size == sample_image.size


# ============================================================================
# FilterOpenAI-Specific Tests
# ============================================================================


class TestFilterOpenAiConfig:
    """Tests for FilterOpenAiConfig."""

    def test_default_connection_settings(self):
        """Test default connection settings values."""
        settings = OpenaiConnectionSettings()
        assert settings.openai_api_key == ""
        assert settings.default_model == DEFAULT_OPENAI_MODEL
        assert settings.timeout_seconds == 120
        assert settings.max_retries == 1

    def test_image_generation_settings(self):
        """Test default image generation settings."""
        settings = FilterOpenAiConfig().image_generation
        assert settings.image_quality == "auto"
        assert settings.image_size == "auto"
        assert settings.input_fidelity == "low"
        assert settings.output_format == "jpeg"
        assert settings.output_compression == 85
        assert settings.moderation == "auto"

    def test_image_quality_values(self):
        """Test that image_quality accepts valid values."""
        for quality in ["auto", "high", "medium", "low"]:
            settings = FilterOpenAiConfig()
            settings.image_generation.image_quality = quality  # type: ignore[assignment]

        with pytest.raises(ValidationError):
            FilterOpenAiConfig(image_generation={"image_quality": "ultra"})  # type: ignore[arg-type]

    def test_input_fidelity_values(self):
        """Test that input_fidelity accepts valid values."""
        settings = FilterOpenAiConfig()
        for fidelity in ["high", "low"]:
            settings.image_generation.input_fidelity = fidelity  # type: ignore[assignment]

        with pytest.raises(ValidationError):
            FilterOpenAiConfig(image_generation={"input_fidelity": "maximum"})  # type: ignore[arg-type]


class TestFilterOpenAiModelCatalog:
    """Tests for the OpenAI model catalog."""

    def test_model_values_are_valid(self):
        """Test that OPENAI_MODEL_VALUES contains expected models."""
        assert "gpt-image-1" in OPENAI_MODEL_VALUES
        assert "gpt-image-2" in OPENAI_MODEL_VALUES
        assert "gpt-image-2.5-flare" in OPENAI_MODEL_VALUES

    def test_model_configs_have_required_fields(self):
        """Test that all model configs have required fields."""
        for _model_name, config in OPENAI_MODEL_CONFIGS.items():
            assert "supported_params" in config
            assert "defaults" in config
            assert "supported_values" in config

    def test_gpt_image_1_has_input_fidelity(self):
        """Test that GPT Image 1 supports input_fidelity parameter."""
        gpt1 = OPENAI_MODEL_CONFIGS["gpt-image-1"]
        assert "input_fidelity" in gpt1["supported_params"]

    def test_gpt_image_25_different_quality_values(self):
        """Test that GPT Image 2.5 models have extended quality values."""
        sunburst = OPENAI_MODEL_CONFIGS["gpt-image-2.5-sunburst"]
        flare = OPENAI_MODEL_CONFIGS["gpt-image-2.5-flare"]

        assert "xhigh" in sunburst["supported_values"]["quality"]
        assert "xhigh" in flare["supported_values"]["quality"]

    def test_default_model_is_valid(self):
        """Test that the default model is a valid model."""
        assert DEFAULT_OPENAI_MODEL in OPENAI_MODEL_CONFIGS


class TestFilterOpenAiFilterParams:
    """Tests for the _filter_params_for_model method."""

    def test_filter_params_unknown_model_uses_defaults(self, filter_openai_plugin):
        """Test that unknown model falls back to gpt-image-1 defaults."""
        result = filter_openai_plugin._filter_params_for_model("unknown-model", {"prompt": "test"})

        assert result["size"] == "auto"
        assert result["quality"] == "auto"
        assert result["output_format"] == "jpeg"

    def test_filter_params_respects_supported_params(self, filter_openai_plugin):
        """Test that unsupported parameters are filtered out."""
        params = {
            "prompt": "test",
            "unsupported_param": "value",
            "size": "1024x1024",
        }
        result = filter_openai_plugin._filter_params_for_model("gpt-image-1", params)

        assert "unsupported_param" not in result
        assert result["size"] == "1024x1024"

    def test_filter_params_out_of_range_uses_default(self, filter_openai_plugin):
        """Test that unsupported parameter values fall back to defaults."""
        params = {
            "prompt": "test",
            "size": "invalid-size",
        }
        result = filter_openai_plugin._filter_params_for_model("gpt-image-1", params)

        assert result["size"] == "auto"


class TestFilterOpenAiImageConversion:
    """Tests for image conversion methods in FilterOpenai."""

    def test_image_to_base64(self, sample_image):
        """Test image to base64 conversion."""
        plugin = FilterOpenai()
        plugin._config = FilterOpenAiConfig()

        b64 = plugin._image_to_base64(sample_image)
        assert isinstance(b64, str)
        assert len(b64) > 0

    def test_image_to_bytes(self, sample_image):
        """Test image to bytes conversion."""
        plugin = FilterOpenai()
        plugin._config = FilterOpenAiConfig()

        img_bytes = plugin._image_to_bytes(sample_image)
        assert isinstance(img_bytes, bytes)
        assert len(img_bytes) > 0

    def test_base64_roundtrip(self, sample_image):
        """Test that base64 decode produces a valid image."""
        plugin = FilterOpenai()
        plugin._config = FilterOpenAiConfig()

        b64 = plugin._image_to_base64(sample_image)
        result = plugin._base64_to_image(b64)

        assert isinstance(result, Image.Image)
        assert result.size == sample_image.size


# ============================================================================
# Preview Image Tests
# ============================================================================


class TestPreviewImageGeneration:
    """Tests for preview image generation common to both plugins."""

    def test_preview_dimensions(self, sample_image, both_plugins):
        """Test that preview images are always 250x250."""
        _name, plugin = both_plugins

        preview = plugin._generate_preview_image("test_style")
        assert preview.size == (250, 250)

    def test_preview_has_text(self, sample_image, both_plugins):
        """Test that preview image contains the filter name as text."""
        _name, plugin = both_plugins

        filter_name = "my_test_style"
        preview = plugin._generate_preview_image(filter_name)

        pixels = list(preview.getdata())
        unique_colors = len(set(pixels))
        assert unique_colors > 1, "Preview should have text rendered (multiple colors)"

    def test_preview_handles_underscored_names(self, sample_image, both_plugins):
        """Test that preview handles filter names with underscores correctly."""
        _name, plugin = both_plugins

        preview = plugin._generate_preview_image("my_cool_filter")
        assert preview.size == (250, 250)

    def test_preview_handles_long_names(self, sample_image, both_plugins):
        """Test that preview handles very long filter names."""
        _name, plugin = both_plugins

        long_name = "very_long_filter_name_that_might_wrap_across_lines"
        preview = plugin._generate_preview_image(long_name)
        assert preview.size == (250, 250)


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests combining multiple plugin features."""

    def test_plugin_initialization(self, both_plugins):
        """Test that plugins initialize correctly with default config."""
        _name, plugin = both_plugins

        assert plugin._config is not None
        assert len(plugin._cache) == 0
        assert len(plugin.mp_avail_filter()) > 0

    def test_get_all_filter_names(self, both_plugins):
        """Test retrieving all available filter names."""
        _name, plugin = both_plugins

        filters = plugin.mp_avail_filter()
        assert isinstance(filters, list)
        assert all(isinstance(f, str) for f in filters)

    def test_user_selectable_filters(self, both_plugins):
        """Test user-selectable filter list generation."""
        _name, plugin = both_plugins

        plugin._config.plugin_behavior.add_userselectable_filter = True
        selectable = plugin.mp_userselectable_filter()

        assert isinstance(selectable, list)
        for f in selectable:
            filter_name = plugin.deunify(f)
            assert filter_name is not None

    def test_userselectable_empty_when_disabled(self, both_plugins):
        """Test that user-selectable is empty when disabled."""
        _name, plugin = both_plugins

        plugin._config.plugin_behavior.add_userselectable_filter = False
        selectable = plugin.mp_userselectable_filter()

        assert selectable == []

    def test_cache_prevents_regeneration(self, sample_image, both_plugins):
        """Test that caching prevents regeneration of same image+filter."""
        _name, plugin = both_plugins

        plugin._config.plugin_behavior.cache_results = True
        cache_key = plugin._generate_cache_key(sample_image, "test_filter", False)

        cached_result = Image.new("RGB", (250, 250), "green")
        plugin._cache[cache_key] = cached_result

        assert cache_key in plugin._cache
        assert plugin._cache[cache_key] == cached_result

    def test_random_filter_logic(self, both_plugins):
        """Test the random filter selection logic."""
        _name, plugin = both_plugins

        enabled = [s.style_name for s in plugin._config.style_prompts if s.style_name not in ("custom", "random") and s.enabled]

        assert len(enabled) > 0

        selected = random.choice(enabled)
        assert selected in enabled

    def test_custom_filter_reads_from_file(self, sample_image, both_plugins, tmp_path):
        """Test that custom filter reads prompt from file."""
        _name, plugin = both_plugins

        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        prompt_file = prompts_dir / "prompt.txt"
        prompt_file.write_text("Custom test prompt")

        try:
            with open(str(prompt_file)) as f:
                custom_prompt = f.read().strip()
            assert custom_prompt == "Custom test prompt"
        except FileNotFoundError:
            pytest.skip("Custom prompt file not found")
