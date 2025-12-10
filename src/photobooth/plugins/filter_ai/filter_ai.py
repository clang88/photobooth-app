import base64
import hashlib
import io
import json
import logging
import time
from pathlib import Path
from typing import cast, get_args
import requests

from PIL import Image

from photobooth.plugins import hookimpl
from photobooth.plugins.base_plugin import BaseFilter

from .config import FilterAiConfig, ai_generation_type

logger = logging.getLogger(__name__)


class FilterAi(BaseFilter[FilterAiConfig]):
    def __init__(self):
        super().__init__()
        self._config: FilterAiConfig = FilterAiConfig()
        
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

        logger.info(f"Applying AI filter '{filter_type}' using provider '{self._config.ai_provider}'")
        
        try:
            # Apply the AI transformation based on provider
            if self._config.ai_provider == "openai":
                result_image = self._apply_openai_filter(image, filter_type, preview)
            elif self._config.ai_provider == "stability_ai":
                result_image = self._apply_stability_ai_filter(image, filter_type, preview)
            elif self._config.ai_provider == "replicate":
                result_image = self._apply_replicate_filter(image, filter_type, preview)
            elif self._config.ai_provider == "local_stable_diffusion":
                result_image = self._apply_local_sd_filter(image, filter_type, preview)
            else:
                raise ValueError(f"Unsupported AI provider: {self._config.ai_provider}")
            
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
        image.save(img_bytes, format='PNG')
        img_hash = hashlib.md5(img_bytes.getvalue()).hexdigest()[:16]
        
        settings_hash = hashlib.md5(
            f"{filter_type}:{self._config.ai_provider}:{self._config.generation_strength}:{preview}".encode()
        ).hexdigest()[:16]
        
        return f"{img_hash}_{settings_hash}"

    def _image_to_base64(self, image: Image.Image, format: str = "PNG") -> str:
        """Convert PIL Image to base64 string."""
        buffer = io.BytesIO()
        image.save(buffer, format=format)
        img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return img_str

    def _base64_to_image(self, base64_str: str) -> Image.Image:
        """Convert base64 string to PIL Image."""
        image_data = base64.b64decode(base64_str)
        image = Image.open(io.BytesIO(image_data))
        return image

    def _apply_openai_filter(self, image: Image.Image, filter_type: ai_generation_type, preview: bool) -> Image.Image:
        """Apply filter using OpenAI DALL-E."""
        if not self._config.openai_api_key:
            raise ValueError("OpenAI API key not configured")

        # For preview mode, we might want to use a smaller/faster processing
        size = "256x256" if preview else "1024x1024"
        
        # Get style prompt for this filter type
        style_prompt = self._config.style_prompts.get(filter_type, "professional photography")
        prompt = f"Transform this image with {style_prompt}"

        # Convert image to base64
        base64_image = self._image_to_base64(image)

        headers = {
            "Authorization": f"Bearer {self._config.openai_api_key}",
            "Content-Type": "application/json"
        }

        # Note: This is a simplified example. OpenAI's actual API for image editing
        # may require different endpoints and parameters
        data = {
            "model": self._config.openai_model,
            "image": base64_image,
            "prompt": prompt,
            "size": size,
            "response_format": "b64_json"
        }

        response = requests.post(
            "https://api.openai.com/v1/images/edits",
            headers=headers,
            json=data,
            timeout=self._config.timeout_seconds
        )
        
        if response.status_code != 200:
            raise RuntimeError(f"OpenAI API error: {response.status_code} - {response.text}")
        
        result = response.json()
        if "data" not in result or not result["data"]:
            raise RuntimeError("No image data received from OpenAI")
        
        # Convert response back to image
        generated_image_b64 = result["data"][0]["b64_json"]
        return self._base64_to_image(generated_image_b64)

    def _apply_stability_ai_filter(self, image: Image.Image, filter_type: ai_generation_type, preview: bool) -> Image.Image:
        """Apply filter using Stability AI."""
        if not self._config.stability_api_key:
            raise ValueError("Stability AI API key not configured")

        style_prompt = self._config.style_prompts.get(filter_type, "professional photography")
        
        # Prepare the request
        headers = {
            "Authorization": f"Bearer {self._config.stability_api_key}",
            "Accept": "application/json"
        }

        # Convert image to bytes
        img_bytes = io.BytesIO()
        image.save(img_bytes, format='PNG')
        img_bytes.seek(0)

        files = {
            "init_image": ("image.png", img_bytes, "image/png")
        }
        
        data = {
            "text_prompts[0][text]": style_prompt,
            "text_prompts[0][weight]": 1.0,
            "cfg_scale": 7,
            "image_strength": self._config.generation_strength,
            "steps": self._config.generation_steps,
            "samples": 1
        }

        response = requests.post(
            "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/image-to-image",
            headers=headers,
            files=files,
            data=data,
            timeout=self._config.timeout_seconds
        )
        
        if response.status_code != 200:
            raise RuntimeError(f"Stability AI API error: {response.status_code} - {response.text}")
        
        result = response.json()
        if "artifacts" not in result or not result["artifacts"]:
            raise RuntimeError("No image artifacts received from Stability AI")
        
        # Convert response back to image
        generated_image_b64 = result["artifacts"][0]["base64"]
        return self._base64_to_image(generated_image_b64)

    def _apply_replicate_filter(self, image: Image.Image, filter_type: ai_generation_type, preview: bool) -> Image.Image:
        """Apply filter using Replicate."""
        if not self._config.replicate_api_key:
            raise ValueError("Replicate API key not configured")

        # This is a placeholder implementation
        # You would need to choose appropriate Replicate models for each filter type
        logger.warning("Replicate provider not fully implemented - returning original image")
        return image

    def _apply_local_sd_filter(self, image: Image.Image, filter_type: ai_generation_type, preview: bool) -> Image.Image:
        """Apply filter using local Stable Diffusion (e.g., Automatic1111 WebUI)."""
        style_prompt = self._config.style_prompts.get(filter_type, "professional photography")
        
        # Convert image to base64 for API
        base64_image = self._image_to_base64(image)

        data = {
            "init_images": [base64_image],
            "prompt": style_prompt,
            "steps": self._config.generation_steps,
            "denoising_strength": self._config.generation_strength,
            "width": image.width,
            "height": image.height,
            "cfg_scale": 7,
            "sampler_index": "Euler a"
        }

        try:
            response = requests.post(
                f"{self._config.local_sd_endpoint}/sdapi/v1/img2img",
                json=data,
                timeout=self._config.timeout_seconds
            )
            
            if response.status_code != 200:
                raise RuntimeError(f"Local SD API error: {response.status_code} - {response.text}")
            
            result = response.json()
            if "images" not in result or not result["images"]:
                raise RuntimeError("No images received from local Stable Diffusion")
            
            # Convert response back to image
            generated_image_b64 = result["images"][0]
            return self._base64_to_image(generated_image_b64)
            
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"Failed to connect to local Stable Diffusion at {self._config.local_sd_endpoint}: {exc}")

    def clear_cache(self):
        """Clear the image cache."""
        self._cache.clear()
        logger.info("AI filter cache cleared")