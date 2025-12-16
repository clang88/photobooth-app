import base64
import hashlib
import io
import logging
from typing import cast, get_args

import requests
from PIL import Image

from photobooth.plugins import hookimpl
from photobooth.plugins.base_plugin import BaseFilter

from .config import FilterOpenAiConfig, ai_generation_type

logger = logging.getLogger(__name__)


# Model-specific parameter configuration
MODEL_CONFIG = {
    "dall-e-2": {
        "supported_params": {"model", "prompt", "n", "size", "response_format", "user"},
        "defaults": {
            "size": "1024x1024",
            "quality": "standard",  # Only standard supported
            "response_format": "b64_json",
        },
        "size_options": ["256x256", "512x512", "1024x1024"],
    },
    "gpt-image-1": {
        "supported_params": {
            "model",
            "prompt",
            "n",
            "size",
            "quality",
            "output_format",
            "background",
            "input_fidelity",
            "output_compression",
            "partial_images",
            "stream",
            "user",
        },
        "defaults": {"size": "auto", "quality": "auto", "output_format": "png", "input_fidelity": "low"},
        "size_options": ["1024x1024", "1536x1024", "1024x1536", "auto"],
    },
    "gpt-image-1-mini": {
        "supported_params": {
            "model",
            "prompt",
            "n",
            "size",
            "quality",
            "output_format",
            "background",
            "output_compression",
            "partial_images",
            "stream",
            "user",
        },
        "defaults": {"size": "auto", "quality": "auto", "output_format": "png"},
        "size_options": ["1024x1024", "1536x1024", "1024x1536", "auto"],
    },
    "gpt-image-1.5": {
        "supported_params": {
            "model",
            "prompt",
            "n",
            "size",
            "quality",
            "output_format",
            "background",
            "input_fidelity",
            "output_compression",
            "partial_images",
            "stream",
            "user",
        },
        "defaults": {"size": "auto", "quality": "auto", "output_format": "png", "input_fidelity": "low"},
        "size_options": ["1024x1024", "1536x1024", "1024x1536", "auto"],
    },
}


class FilterOpenai(BaseFilter[FilterOpenAiConfig]):
    def __init__(self):
        super().__init__()
        self._config: FilterOpenAiConfig = FilterOpenAiConfig()

        # Simple cache for generated images (in-memory)
        self._cache: dict[str, Image.Image] = {}

    @hookimpl
    def mp_avail_filter(self) -> list[str]:
        """Return all available AI filters."""
        return [self.unify(f) for f in get_args(ai_generation_type)]

    @hookimpl
    def mp_userselectable_filter(self) -> list[str]:
        """Return user-selectable AI filters based on configuration."""
        if self._config.add_userselectable_filter:
            return [self.unify(f) for f in self._config.userselectable_filter]
        else:
            return []

    @hookimpl
    def mp_filter_pipeline_step(self, image: Image.Image, plugin_filter: str, preview: bool) -> Image.Image | None:
        """Main filter processing step."""
        filter_name = self.deunify(plugin_filter)

        if filter_name:  # If this is our filter, process it
            try:
                return self.do_filter(image, cast(ai_generation_type, filter_name), preview)
            except Exception as exc:
                logger.error(f"AI filter '{filter_name}' failed: {exc}")
                if self._config.enable_fallback_on_error:
                    logger.info("Returning original image due to AI filter error")
                    return image
                else:
                    raise
        return None

    def do_filter(self, image: Image.Image, filter_type: ai_generation_type, preview: bool) -> Image.Image:
        """Apply AI filter to the image."""
        # Generate cache key
        cache_key = self._generate_cache_key(image, filter_type, preview)

        # Check cache first
        if self._config.cache_results and cache_key in self._cache:
            logger.debug(f"Using cached result for filter '{filter_type}'")
            return self._cache[cache_key]

        logger.info(f"Applying AI filter '{filter_type}'")

        try:
            # Apply the AI transformation
            result_image = self._apply_openai_filter(image, filter_type, preview)
            # Cache the result
            if self._config.cache_results:
                self._cache[cache_key] = result_image

            return result_image

        except Exception as exc:
            logger.error(f"Failed to apply AI filter '{filter_type}': {exc}")
            raise

    def _generate_cache_key(self, image: Image.Image, filter_type: ai_generation_type, preview: bool) -> str:
        """Generate a cache key for the image and filter combination."""
        # Create a hash of image data + filter settings
        img_bytes = io.BytesIO()
        image.save(img_bytes, format="PNG")
        img_hash = hashlib.md5(img_bytes.getvalue()).hexdigest()[:16]

        settings_hash = hashlib.md5(f"{filter_type}:{preview}".encode()).hexdigest()[:16]

        return f"{img_hash}_{settings_hash}"

    def _image_to_bytes(self, image: Image.Image, format: str = "png") -> bytes:
        buffer = io.BytesIO()
        image.save(buffer, format=format)
        return buffer.getvalue()

    def _image_to_base64(self, image: Image.Image, format: str = "jpeg") -> str:
        """Convert PIL Image to base64 string."""
        buffer = io.BytesIO()
        # Ensure image is in RGB mode
        if image.mode in ("RGBA", "LA", "P"):
            image = image.convert("RGB")
        image.save(buffer, format=format)
        b64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return b64_image

    def _base64_to_image(self, base64_str: str) -> Image.Image:
        """Convert base64 string to PIL Image."""
        image_data = base64.b64decode(base64_str)
        image = Image.open(io.BytesIO(image_data))
        return image

    def _filter_params_for_model(self, model: str, requested_params: dict) -> dict:
        """Filter parameters based on model capabilities and apply defaults."""
        model_config = MODEL_CONFIG.get(model)
        if not model_config:
            logger.warning(f"Unknown model '{model}', using dall-e-2 defaults")
            model_config = MODEL_CONFIG["dall-e-2"]

        supported_params = model_config["supported_params"]
        defaults = model_config["defaults"]

        # Start with model defaults
        filtered_params = defaults.copy()

        # Add supported requested parameters
        for param_name, param_value in requested_params.items():
            if param_name in supported_params:
                filtered_params[param_name] = param_value
            else:
                logger.debug(f"Parameter '{param_name}' not supported by model '{model}', skipping")

        return filtered_params

    def _apply_openai_filter(self, image: Image.Image, filter_type: ai_generation_type, preview: bool) -> Image.Image:
        """Apply filter using OpenAI DALL-E or GPT-Image-1."""
        if not self._config.openai_api_key:
            raise ValueError("OpenAI API key not configured")
        model = self._config.openai_model

        # For preview mode, for now we just return the normal image...
        if preview:
            return image

        # Get style prompt for this filter type
        if filter_type == "custom":
            style_prompt = self._config.custom_prompt
        else:
            style_prompt = "professional photography"  # default
            for style in self._config.style_prompts:
                if style.style_name == filter_type and style.enabled:
                    style_prompt = style.prompt
                    break
        prompt = f"{style_prompt}"

        # Convert image to bytes
        image_bytes = self._image_to_bytes(image)

        # Build requested parameters
        requested_params = {
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": self._config.image_size,
            "quality": self._config.image_quality,
            "input_fidelity": "high",
            "output_format": "jpeg",
            "response_format": "b64_json",  # For dall-e-2 compatibility
        }

        # Filter parameters based on model capabilities
        filtered_params = self._filter_params_for_model(model, requested_params)

        # Log what parameters we're actually using
        logger.info(f"Using model '{model}' with parameters: {filtered_params}")

        headers = {"Authorization": f"Bearer {self._config.openai_api_key}"}

        # Convert parameters to files format for multipart request
        files = {key: (None, value) for key, value in filtered_params.items()}

        # Add the image file
        files["image"] = ("image", image_bytes, "image/png")

        try:
            response = requests.post("https://api.openai.com/v1/images/edits", headers=headers, files=files, timeout=self._config.timeout_seconds)

            if response.status_code != 200:
                raise RuntimeError(f"OpenAI API error: {response.status_code} - {response.text}")

            result = response.json()
            if "data" not in result or not result["data"]:
                raise RuntimeError("No image data received from OpenAI")

            # Handle response format differences
            if "b64_json" in result["data"][0]:
                # GPT models and dall-e-2 with b64_json format
                generated_image_b64 = result["data"][0]["b64_json"]
                return self._base64_to_image(generated_image_b64)
            elif "url" in result["data"][0]:
                # dall-e-2 with URL format (fallback)
                image_url = result["data"][0]["url"]
                logger.warning("Received URL response, downloading image (consider using b64_json format)")
                img_response = requests.get(image_url, timeout=30)
                img_response.raise_for_status()
                return Image.open(io.BytesIO(img_response.content))
            else:
                raise RuntimeError("Invalid response format from OpenAI API")

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Request to OpenAI API failed: {e}")

    def clear_cache(self):
        """Clear the image cache."""
        self._cache.clear()
        logger.info("AI filter cache cleared")
