import typing
from typing import Literal

from pydantic import Field, HttpUrl
from pydantic_settings import SettingsConfigDict

from photobooth import CONFIG_PATH
from photobooth.services.config.baseconfig import BaseConfig

# Available AI generation types
ai_generation_type = Literal[
    "style_transfer",
    "enhance", 
    "cartoon",
    "sketch",
    "watercolor",
    "oil_painting",
    "vintage",
    "cyberpunk",
    "fantasy",
    "anime"
]

# AI service providers
ai_provider_type = Literal[
    "openai",
    "stability_ai", 
    "replicate",
    "local_stable_diffusion"
]

class FilterAiConfig(BaseConfig):
    model_config = SettingsConfigDict(
        title="AI Filter Plugin Config",
        json_file=f"{CONFIG_PATH}plugin_filter_ai.json",
        env_prefix="filter-ai-",
    )

    # General plugin settings
    add_userselectable_filter: bool = Field(
        default=True,
        description="Add userselectable AI filters to the list the user can choose from.",
    )
    
    userselectable_filter: list[ai_generation_type] = Field(
        default=["style_transfer", "enhance", "cartoon", "sketch"],
        description="Select AI filters the user can choose from. Even if unselected here, the filter is still available in the admin configuration.",
    )

    # AI Service Configuration
    ai_provider: ai_provider_type = Field(
        default="openai",
        description="AI service provider to use for image generation and processing.",
    )

    # OpenAI Configuration
    openai_api_key: str = Field(
        default="",
        description="OpenAI API key for DALL-E image processing. Required when using OpenAI provider.",
    )
    
    openai_model: str = Field(
        default="dall-e-3",
        description="OpenAI model to use (dall-e-2, dall-e-3).",
    )

    # Stability AI Configuration  
    stability_api_key: str = Field(
        default="",
        description="Stability AI API key for Stable Diffusion. Required when using Stability AI provider.",
    )

    # Replicate Configuration
    replicate_api_key: str = Field(
        default="",
        description="Replicate API key for various AI models. Required when using Replicate provider.",
    )

    # Local Stable Diffusion Configuration
    local_sd_endpoint: HttpUrl = Field(
        default="http://127.0.0.1:7860",
        description="Local Stable Diffusion API endpoint (e.g., Automatic1111 WebUI API).",
    )

    # Generation Parameters
    generation_strength: float = Field(
        default=0.7,
        ge=0.1,
        le=1.0,
        description="Strength of the AI transformation (0.1-1.0). Higher values create more dramatic changes.",
    )

    generation_steps: int = Field(
        default=20,
        ge=10,
        le=50,
        description="Number of inference steps for AI generation. More steps = higher quality but slower processing.",
    )

    timeout_seconds: int = Field(
        default=30,
        ge=5,
        le=120,
        description="Timeout for AI API calls in seconds.",
    )

    # Style prompts for different filter types
    style_prompts: dict[str, str] = Field(
        default={
            "style_transfer": "artistic style transfer, maintain subject, professional photography",
            "enhance": "enhanced, high quality, sharp details, professional photography",
            "cartoon": "cartoon style, animated, colorful, disney-like illustration",
            "sketch": "pencil sketch, black and white drawing, artistic sketch",
            "watercolor": "watercolor painting, soft brush strokes, artistic",
            "oil_painting": "oil painting, classical art style, rich textures",
            "vintage": "vintage photography, sepia tones, retro aesthetic",
            "cyberpunk": "cyberpunk style, neon lights, futuristic, sci-fi aesthetic",
            "fantasy": "fantasy art, magical, ethereal, mystical atmosphere",
            "anime": "anime style, manga illustration, japanese animation style"
        },
        description="Prompt templates for different AI filter styles. These guide the AI generation process.",
    )

    # Fallback settings
    enable_fallback_on_error: bool = Field(
        default=True,
        description="If AI generation fails, return the original image instead of an error.",
    )

    cache_results: bool = Field(
        default=True,
        description="Cache AI-generated results to avoid regenerating the same image multiple times.",
    )