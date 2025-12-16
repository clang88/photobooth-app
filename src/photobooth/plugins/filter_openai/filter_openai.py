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

    def _image_to_base64(self, image: Image.Image, format: str = "jpeg") -> bytes:
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

    def _apply_openai_filter(self, image: Image.Image, filter_type: ai_generation_type, preview: bool) -> Image.Image:
        """Apply filter using OpenAI DALL-E or GPT-Image-1."""
        if not self._config.openai_api_key:
            raise ValueError("OpenAI API key not configured")
        model = self._config.openai_model

        # For preview mode, for now we just return the normal image...
        # size = "256x256" if model == "dall-e-2" and preview  else "1024x1024"
        if preview:
            return image
        size = "auto"

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

        headers = {"Authorization": f"Bearer {self._config.openai_api_key}"}

        files = {
            "model": (None, model),
            "prompt": (None, prompt),
            "n": (None, 1),
            "size": (None, size),  # TODO: Make configurable
            "quality": (None, "high"),  # TODO: Make configurable
            "input_fidelity": (None, "high"),  # TODO: Make configurable
            "output_format": (None, "jpeg"),  # TODO: Make configurable
        }
        # Model-specific setup
        if model == "dall-e-2":
            files["response_format"] = (None, "b64_json")  # TODO: Make configurable
        if model == "gpt-image-1":
            files["moderation"] = (None, "low")  # TODO: Make configurable

        logging.info("Sending request to OpenAI API... with following parameters: %s", files)

        # Hard-code image mimeType and name for now
        files["image"] = ("image", image_bytes, "image/png")

        response = requests.post("https://api.openai.com/v1/images/edits", headers=headers, files=files, timeout=self._config.timeout_seconds)

        if response.status_code != 200:
            raise RuntimeError(f"OpenAI API error: {response.status_code} - {response.text}")

        result = response.json()
        if "data" not in result or not result["data"]:
            raise RuntimeError("No image data received from OpenAI")

        # Convert response back to image
        generated_image_b64 = result["data"][0]["b64_json"]
        return self._base64_to_image(generated_image_b64)

    def clear_cache(self):
        """Clear the image cache."""
        self._cache.clear()
        logger.info("AI filter cache cleared")
