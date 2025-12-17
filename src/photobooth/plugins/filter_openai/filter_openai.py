import base64
import hashlib
import io
import logging

import niquests as requests
from PIL import Image

from photobooth.plugins import hookimpl
from photobooth.plugins.base_plugin import BaseFilter

from .config import FilterOpenAiConfig

logger = logging.getLogger(__name__)


# Model-specific parameter configuration
MODEL_CONFIG = {
    "dall-e-2": {
        "supported_params": {"model", "prompt", "n", "size", "response_format", "user"},
        "defaults": {
            "size": "1024x1024",
            "response_format": "b64_json",
        },
        "supported_values": {"size": ["256x256", "512x512", "1024x1024"]},
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
            "moderation",
        },
        "defaults": {"size": "auto", "quality": "auto", "output_format": "png", "input_fidelity": "low"},
        "supported_values": {"size": ["1024x1024", "1536x1024", "1024x1536", "auto"]},
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
            "moderation",
        },
        "defaults": {"size": "auto", "quality": "auto", "output_format": "png"},
        "supported_values": {"size": ["1024x1024", "1536x1024", "1024x1536", "auto"]},
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
            "moderation",
        },
        "defaults": {"size": "auto", "quality": "auto", "output_format": "png", "input_fidelity": "low"},
        "supported_values": {"size": ["1024x1024", "1536x1024", "1024x1536", "auto"]},
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
        # Return all configured style_prompts
        all_filters = [style.style_name for style in self._config.style_prompts]
        return [self.unify(f) for f in all_filters]

    @hookimpl
    def mp_userselectable_filter(self) -> list[str]:
        """Return user-selectable AI filters based on configuration."""
        if not self._config.plugin_behavior.add_userselectable_filter:
            return []

        # Dynamically generate list from enabled style prompts + custom
        selectable_filters = []

        # Add all enabled style prompts
        for style in self._config.style_prompts:
            if style.enabled:
                selectable_filters.append(style.style_name)

        return [self.unify(f) for f in selectable_filters]

    @hookimpl
    def mp_filter_pipeline_step(self, image: Image.Image, plugin_filter: str, preview: bool) -> Image.Image | None:
        """Main filter processing step."""
        filter_name = self.deunify(plugin_filter)

        if filter_name:  # If this is our filter, process it
            try:
                return self.do_filter(image, filter_name, preview)
            except Exception as exc:
                logger.error(f"AI filter '{filter_name}' failed: {exc}")
                if self._config.plugin_behavior.enable_fallback_on_error:
                    logger.info("Returning original image due to AI filter error")
                    return image
                else:
                    raise
        return None

    def do_filter(self, image: Image.Image, filter_type: str, preview: bool) -> Image.Image:
        """Apply AI filter to the image."""
        # Generate cache key
        cache_key = self._generate_cache_key(image, filter_type, preview)

        # Check cache first
        if self._config.plugin_behavior.cache_results and cache_key in self._cache:
            logger.debug(f"Using cached result for filter '{filter_type}'")
            return self._cache[cache_key]

        logger.info(f"Applying AI filter '{filter_type}'")

        try:
            # Apply the AI transformation
            result_image = self._apply_openai_filter(image, filter_type, preview)
            # Cache the result
            if self._config.plugin_behavior.cache_results:
                self._cache[cache_key] = result_image

            return result_image

        except Exception as exc:
            logger.error(f"Failed to apply AI filter '{filter_type}': {exc}")
            raise

    def _generate_cache_key(self, image: Image.Image, filter_type: str, preview: bool) -> str:
        """Generate a cache key for the image and filter combination."""
        # Create a hash of image data + filter settings
        img_bytes = io.BytesIO()
        image.save(img_bytes, format="PNG")
        img_hash = hashlib.md5(img_bytes.getvalue()).hexdigest()[:16]

        settings_hash = hashlib.md5(f"{filter_type}:{preview}".encode()).hexdigest()[:16]

        return f"{img_hash}_{settings_hash}"

    def _image_to_bytes(self, image: Image.Image, format: str = "png") -> bytes:
        buffer = io.BytesIO()
        model = self._config.connection.openai_model
        # Convert to RGBA format as required by DALL-E 2
        if model == "dall-e-2" and image.mode != "RGBA":
            image = image.convert("RGBA")
        # Convert to RGB for other models if not already RGB or RGBA
        elif image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGB")
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
                if param_name in model_config.get("supported_values", {}):
                    supported_values = model_config["supported_values"][param_name]
                    if param_value not in supported_values:
                        logger.warning(
                            f"Parameter '{param_name}' value '{param_value}' not supported by model '{model}'. Supported values: {supported_values}. Using default '{defaults.get(param_name)}'"
                        )
                        filtered_params[param_name] = defaults.get(param_name)
            else:
                logger.debug(f"Parameter '{param_name}' not supported by model '{model}', skipping")

        return filtered_params

    def _apply_openai_filter(self, image: Image.Image, filter_type: str, preview: bool) -> Image.Image:
        """Apply filter using OpenAI DALL-E or GPT-Image-1."""
        if not self._config.connection.openai_api_key:
            raise ValueError("OpenAI API key not configured")
        model = self._config.connection.openai_model

        # For preview mode, for now we just return the normal image...
        if preview:
            return image

        # Get style prompt for this filter type
        style_prompt = None
        for style in self._config.style_prompts:
            if style.style_name == filter_type and style.enabled:
                style_prompt = style.prompt
                break

        if style_prompt is None:
            raise ValueError(f"Filter '{filter_type}' not found in enabled style_prompts")

        prompt = f"{style_prompt}"

        # Convert image to bytes
        image_bytes = self._image_to_bytes(image)

        # Build requested parameters - only include parameters that exist in config
        requested_params = {
            "model": model,
            "prompt": prompt,
        }

        # Add parameters that exist in config
        param_mapping = {
            "image_size": "size",
            "image_quality": "quality",
            "input_fidelity": "input_fidelity",
            "output_format": "output_format",
            "output_compression": "output_compression",
            "moderation": "moderation",
        }

        for config_param, api_param in param_mapping.items():
            if hasattr(self._config.image_generation, config_param):
                requested_params[api_param] = getattr(self._config.image_generation, config_param)

        # Add hardcoded defaults for common parameters
        if "n" not in requested_params:
            requested_params["n"] = "1"  # Always generate 1 image for photobooth
        if "response_format" not in requested_params:
            requested_params["response_format"] = "b64_json"  # Default to base64 JSON

        # Filter parameters based on model capabilities
        filtered_params = self._filter_params_for_model(model, requested_params)

        # Log what parameters we're actually using
        logger.info(f"Using model '{model}' with parameters: {filtered_params}")

        headers = {"Authorization": f"Bearer {self._config.connection.openai_api_key}"}

        # Convert parameters to files format for multipart request - niquests requires string values
        files = {key: (None, str(value)) for key, value in filtered_params.items()}

        # Add the image file
        files["image"] = ("image", image_bytes, "image/png")

        try:
            logger.debug("Sending request to OpenAI API...")
            session = requests.Session(disable_http3=True)  # HTTP/3 seems to cause timeouts?
            response = session.post(
                "https://api.openai.com/v1/images/edits", headers=headers, files=files, timeout=self._config.connection.timeout_seconds
            )
            session.close()
            logger.debug(f"Received response with status code: {response.status_code}")

            if response.status_code != 200:
                logger.error(f"OpenAI API returned error status {response.status_code}: {response.text}")
                raise RuntimeError(f"OpenAI API error: {response.status_code} - {response.text}")

            logger.debug("Parsing JSON response...")
            result = response.json()
            logger.debug(f"Response keys: {list(result.keys()) if result else 'None'}")

            if "data" not in result or not result["data"]:
                logger.error(f"Invalid response structure: {result}")
                raise RuntimeError("No image data received from OpenAI")

            response_data = result["data"][0]
            logger.debug(f"Response data keys: {list(response_data.keys())}")

            # Handle response format differences
            if "b64_json" in response_data:
                # GPT models and dall-e-2 with b64_json format
                logger.debug("Processing b64_json response...")
                generated_image_b64 = response_data["b64_json"]
                return self._base64_to_image(generated_image_b64)
            elif "url" in response_data:
                # dall-e-2 with URL format (fallback)
                logger.warning("Received URL response, downloading image (consider using b64_json format)")
                image_url = response_data["url"]
                img_response = requests.get(image_url, timeout=30)
                img_response.raise_for_status()
                return Image.open(io.BytesIO(img_response.content))
            else:
                logger.error(f"Unknown response format. Available keys: {list(response_data.keys())}")
                raise RuntimeError("Invalid response format from OpenAI API")

        except requests.exceptions.Timeout as e:
            logger.error(f"Request timed out after {self._config.connection.timeout_seconds} seconds: {e}")
            raise RuntimeError(f"Request to OpenAI API timed out: {e}") from e
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise RuntimeError(f"Request to OpenAI API failed: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error during API call: {e}")
            raise

    def clear_cache(self):
        """Clear the image cache."""
        self._cache.clear()
        logger.info("AI filter cache cleared")
