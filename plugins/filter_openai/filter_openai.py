import base64
import hashlib
import io
import logging
import textwrap
from typing import Any, cast

import requests
from anyio import Path
from PIL import Image, ImageDraw, ImageFont

from photobooth import CONFIG_PATH
from photobooth.plugins import hookimpl
from photobooth.plugins.base_plugin import BaseFilter

from .config import FilterOpenAiConfig
from .model_catalog import OPENAI_MODEL_CONFIGS, OpenAIModelLiteral

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
    def mp_long_running_filter(self) -> list[str]:
        """Return long-running AI filters from this plugin."""
        return self.mp_avail_filter()

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
                    logger.info("Returning original image with error text due to AI filter error")
                    return self._add_error_text(image.copy(), str(exc))
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

    def _generate_preview_image(self, filter_type: str) -> Image.Image:
        """Generate a placeholder preview image for a filter style."""
        width, height = 800, 800
        image = Image.new("RGB", (width, height), (245, 245, 245))

        # Load bundled Bitcount font (cross-platform, no OS dependency)
        font_path = Path(__file__).parent / "Bitcount.ttf"
        font_size = 120
        try:
            font = ImageFont.truetype(str(font_path), font_size)
        except OSError:
            font = ImageFont.load_default()

        # Load and resize logo for background
        logo_path = Path(__file__).parent / "logo.png"
        if logo_path.exists():
            try:
                logo = Image.open(str(logo_path)).convert("RGBA")
                # Resize logo to fit nicely as background (30% of canvas width)
                logo_aspect = logo.height / logo.width
                logo_w = int(width * 0.3)
                logo_h = int(logo_w * logo_aspect)
                logo = logo.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
                # Center and composite with low opacity
                logo_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                logo_x = (width - logo_w) // 2
                logo_y = (height - logo_h) // 2
                # Make logo semi-transparent
                logo_r, logo_g, logo_b, logo_a = logo.split()
                logo_a = logo_a.point(lambda p: cast(int, p) // 3)  # Reduce alpha to 1/3
                logo = Image.merge("RGBA", (logo_r, logo_g, logo_b, logo_a))
                logo_overlay.paste(logo, (logo_x, logo_y))
                image = Image.alpha_composite(image.convert("RGBA"), logo_overlay).convert("RGB")
            except Exception:
                pass  # Silently skip logo if it fails

        # Create draw object AFTER logo processing (image may have been replaced)
        draw = ImageDraw.Draw(image)

        # Estimate average character width for wrapping
        max_chars_per_line = 12

        # Wrap by words
        words = filter_type.split("_")
        lines: list[str] = []
        current_line = ""
        for word in words:
            if current_line:
                len_current = len(current_line) + 1 + len(word)
            else:
                len_current = len(word)
            if len_current <= max_chars_per_line:
                if current_line:
                    current_line += " " + word
                else:
                    current_line = word
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        if not lines:
            lines = [filter_type[:max_chars_per_line]]

        # Calculate vertical centering for all lines
        line_heights = [draw.textbbox((0, 0), line, font=font)[3] for line in lines]
        total_text_height = sum(line_heights) + 10 * (len(lines) - 1)  # 10px gap between lines
        y_start = (height - total_text_height) // 2

        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            text_w = bbox[2] - bbox[0]
            x = (width - text_w) // 2
            y = y_start + sum(line_heights[:i]) + 10 * i
            draw.text((x, y), line, fill=(50, 50, 50), font=font)

        # "AI" badge
        badge_font_path = Path(__file__).parent / "Inter.ttf"
        badge_font_size = 120
        try:
            badge_font = ImageFont.truetype(str(badge_font_path), badge_font_size)
        except OSError:
            badge_font = ImageFont.load_default()

        # Measure the "AI" text so the pill fits it exactly
        text_bbox = draw.textbbox((0, 0), "AI", font=badge_font)
        text_w = text_bbox[2] - text_bbox[0]
        text_h = text_bbox[3] - text_bbox[1]

        # Pill = text + padding, placed with a margin from the top-right corner
        pad_x, pad_y = 16, 12
        margin = 20
        pill_w = text_w + 2 * pad_x
        pill_h = text_h + 2 * pad_y
        pill_left = width - margin - pill_w
        pill_top = margin

        draw.rounded_rectangle(
            (pill_left, pill_top, pill_left + pill_w, pill_top + pill_h),
            radius=16,
            fill=(80, 120, 220),
        )

        # anchor="mm" centers the text exactly at the pill's center,
        # regardless of the font's internal metrics
        draw.text(
            (pill_left + pill_w / 2, pill_top + pill_h / 2),
            "AI",
            fill=(255, 255, 255),
            font=badge_font,
            anchor="mm",
        )

        return image

    def _generate_cache_key(self, image: Image.Image, filter_type: str, preview: bool) -> str:
        """Generate a cache key for the image and filter combination."""
        # Create a hash of image data + filter settings
        img_bytes = io.BytesIO()
        image.save(img_bytes, format="PNG")
        img_hash = hashlib.md5(img_bytes.getvalue()).hexdigest()[:16]

        # Get model for this filter type to include in cache key
        model = self._config.connection.default_model  # Default fallback
        for style in self._config.style_prompts:
            if style.style_name == filter_type:
                model = style.model if style.model else self._config.connection.default_model
                break

        settings_hash = hashlib.md5(f"{filter_type}:{preview}:{model}".encode()).hexdigest()[:16]

        return f"{img_hash}_{settings_hash}"

    def _resize_image_if_needed(self, image: Image.Image) -> Image.Image:
        """Resize image if it exceeds max dimensions."""
        max_size = self._config.image_generation.max_input_image_size

        # Check if resizing is needed
        if max(image.size) <= max_size:
            return image

        # Calculate new size while maintaining aspect ratio
        width, height = image.size
        if width > height:
            new_width = max_size
            new_height = int((height * max_size) / width)
        else:
            new_height = max_size
            new_width = int((width * max_size) / height)

        resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        logger.debug(f"Resized image from {image.size} to {resized_image.size}")
        return resized_image

    def _image_to_bytes(self, image: Image.Image, format: str = "png", model: OpenAIModelLiteral | str | None = None) -> bytes:
        # Resize if needed
        image = self._resize_image_if_needed(image)

        buffer = io.BytesIO()
        # Convert to RGB for models if not already RGB or RGBA
        if image.mode not in ("RGB", "RGBA"):
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

    def _add_error_text(self, image: Image.Image, error_message: str) -> Image.Image:
        """Overlay error text on the fallback image."""
        draw = ImageDraw.Draw(image)
        width, height = image.size

        # Scale font size relative to image width
        font_size = max(16, width // 30)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
        except OSError:
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
            except OSError:
                font = ImageFont.load_default()

        # Wrap text to fit image width (approx chars per line)
        max_chars = max(20, width // (font_size // 2))
        wrapped = textwrap.fill(error_message, width=max_chars)
        lines = wrapped.split("\n")
        # Keep at most 4 lines to avoid covering too much of the image
        if len(lines) > 4:
            lines = lines[:4]
            lines[-1] = lines[-1][: max_chars - 3] + "..."
        text = "\n".join(lines)

        # Calculate text position (top of image)
        bbox = draw.multiline_textbbox((0, 0), text, font=font)
        text_height = bbox[3] - bbox[1]
        text_width = bbox[2] - bbox[0]
        padding = 10
        x = (width - text_width) // 2
        y = padding * 2

        # Draw semi-transparent dark background
        bg_box = (x - padding, y - padding, x + text_width + padding, y + text_height + padding)
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle(bg_box, fill=(0, 0, 0, 160))
        image = Image.alpha_composite(image.convert("RGBA"), overlay).convert(image.mode)

        # Draw text on the composited image
        draw = ImageDraw.Draw(image)
        draw.multiline_text((x, y), text, fill=(255, 255, 255), font=font)

        return image

    def _filter_params_for_model(self, model: OpenAIModelLiteral | str, requested_params: dict[str, Any]) -> dict[str, Any]:
        """Filter parameters based on model capabilities and apply defaults."""
        model_config = OPENAI_MODEL_CONFIGS.get(model)
        if not model_config:
            logger.warning(f"Unknown model '{model}', using gpt-image-1 defaults")
            model_config = OPENAI_MODEL_CONFIGS["gpt-image-1"]

        supported_params = model_config["supported_params"]
        defaults = model_config["defaults"]

        # Start with model defaults
        filtered_params: dict[str, Any] = defaults.copy()

        # Add supported requested parameters
        for param_name, param_value in requested_params.items():
            if param_name in supported_params:
                filtered_params[param_name] = param_value
                if param_name in model_config.get("supported_values", {}):
                    supported_values = model_config["supported_values"][param_name]
                    if param_value not in supported_values:
                        default_val = defaults.get(param_name)
                        logger.warning(
                            f"Parameter '{param_name}' value '{param_value}' not supported by model '{model}'. Supported values: {supported_values}. "
                            f"Using default '{default_val}'"
                        )
                        if default_val is not None:
                            filtered_params[param_name] = default_val
                        else:
                            filtered_params.pop(param_name, None)
            else:
                logger.debug(f"Parameter '{param_name}' not supported by model '{model}', skipping")

        return filtered_params

    def _apply_openai_filter(self, image: Image.Image, filter_type: str, preview: bool) -> Image.Image:
        """Apply filter using OpenAI DALL-E or GPT-Image-1."""
        if not self._config.connection.openai_api_key:
            raise ValueError("OpenAI API key not configured")

        # For preview mode, generate and return a preview image instead of applying the full filter.
        if preview:
            return self._generate_preview_image(filter_type)

        # Get style prompt and model for this filter type
        style_prompt = None
        model: OpenAIModelLiteral | None = None
        for style in self._config.style_prompts:
            if style.style_name == filter_type:
                if filter_type == "custom":
                    try:
                        with open(f"{CONFIG_PATH}/prompts/prompt.txt") as f:
                            style_prompt = f.read().strip()
                    except Exception as e:
                        logger.error(f"Error reading custom prompt: {e}")
                        style_prompt = None
                else:
                    style_prompt = style.prompt
                # Use style-specific model if available, otherwise fall back to default
                model = style.model if style.model else self._config.connection.default_model
                break

        if style_prompt is None:
            raise ValueError(f"Filter '{filter_type}' not found in style_prompts")
        if model is None:
            raise ValueError(f"No model resolved for filter '{filter_type}'")

        prompt = f"{style_prompt}"

        # Convert image to bytes
        image_bytes = self._image_to_bytes(image, model=model)

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
        files: dict[str, Any] = {key: (None, str(value)) for key, value in filtered_params.items()}

        # Add the image file
        files["image"] = ("image", image_bytes, "image/png")

        max_retries = self._config.connection.max_retries
        last_exception = None

        for attempt in range(1 + max_retries):
            try:
                logger.info(f"Sending request to OpenAI API with model '{model}' (attempt {attempt + 1}/{1 + max_retries})...")
                logger.debug(f"Prompt: {prompt}")

                session = requests.Session()
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
                    # GPT models with b64_json format
                    logger.debug("Processing b64_json response...")
                    generated_image_b64 = response_data["b64_json"]
                    logger.info(f"Successfully generated image using '{model}' model")
                    return self._base64_to_image(generated_image_b64)
                elif "url" in response_data:
                    # URL format (fallback)
                    logger.warning("Received URL response, downloading image (consider using b64_json format)")
                    image_url = response_data["url"]
                    img_response = requests.get(image_url, timeout=30)
                    img_response.raise_for_status()
                    logger.info(f"Successfully generated image using '{model}' model")
                    return Image.open(io.BytesIO(img_response.content))
                else:
                    logger.error(f"Unknown response format. Available keys: {list(response_data.keys())}")
                    raise RuntimeError("Invalid response format from OpenAI API")

            except requests.exceptions.Timeout as e:
                last_exception = e
                logger.warning(f"Request timed out (attempt {attempt + 1}/{1 + max_retries}): {e}")
                if attempt < max_retries:
                    logger.info("Retrying...")
                    continue
                logger.error(f"All {1 + max_retries} attempts timed out after {self._config.connection.timeout_seconds}s each")
                raise RuntimeError(f"Request to OpenAI API timed out after {1 + max_retries} attempt(s): {e}") from e
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed: {e}")
                raise RuntimeError(f"Request to OpenAI API failed: {e}") from e
            except Exception as e:
                logger.error(f"Unexpected error during API call: {e}")
                raise

        # Should not be reached, but just in case
        raise RuntimeError(f"Request to OpenAI API failed after {1 + max_retries} attempt(s)") from last_exception

    def clear_cache(self):
        """Clear the image cache."""
        self._cache.clear()
        logger.info("AI filter cache cleared")
