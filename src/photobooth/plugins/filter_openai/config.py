from typing import Literal

from pydantic import Field
from pydantic_settings import SettingsConfigDict

from photobooth import CONFIG_PATH
from photobooth.services.config.baseconfig import BaseConfig

from .models import StylePrompt

# Available AI generation types
ai_generation_type = Literal[
    "style_transfer", "enhance", "cartoon", "sketch", "watercolor", "oil_painting", "vintage", "cyberpunk", "fantasy", "anime", "custom"
]


class FilterOpenAiConfig(BaseConfig):
    model_config = SettingsConfigDict(
        title="Open AI Filter Plugin Config",
        json_file=f"{CONFIG_PATH}plugin_filter_openai.json",
        env_prefix="filter-ai-",
    )

    # General plugin settings
    add_userselectable_filter: bool = Field(
        default=True,
        description="Add userselectable AI filters to the list the user can choose from.",
    )

    userselectable_filter: list[ai_generation_type] = Field(
        default=["style_transfer", "enhance", "cartoon", "sketch", "custom"],
        description="Select AI filters the user can choose from. Even if unselected here, the filter is still available in the admin configuration.",
    )

    # OpenAI Configuration
    openai_api_key: str = Field(
        default="",
        description="OpenAI API key for DALL-E image processing. Required when using OpenAI provider.",
    )

    openai_model: Literal["dall-e-2", "gpt-image-1"] = Field(
        default="gpt-image-1",
        description="OpenAI model to use (dall-e-2, gpt-image-1).",
    )

    timeout_seconds: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Timeout for AI API calls in seconds.",
    )

    # Style prompts for different filter types
    style_prompts: list[StylePrompt] = Field(
        default=[
            StylePrompt(style_name="style_transfer", prompt="artistic style transfer, maintain subject, professional photography"),
            StylePrompt(style_name="enhance", prompt="enhanced, high quality, sharp details, professional photography"),
            StylePrompt(style_name="cartoon", prompt="cartoon style, animated, colorful, disney-like illustration"),
            StylePrompt(style_name="sketch", prompt="pencil sketch, black and white drawing, artistic sketch"),
            StylePrompt(style_name="watercolor", prompt="watercolor painting, soft brush strokes, artistic"),
            StylePrompt(style_name="oil_painting", prompt="oil painting, classical art style, rich textures"),
            StylePrompt(style_name="vintage", prompt="vintage photography, sepia tones, retro aesthetic"),
            StylePrompt(style_name="cyberpunk", prompt="cyberpunk style, neon lights, futuristic, sci-fi aesthetic"),
            StylePrompt(style_name="fantasy", prompt="fantasy art, magical, ethereal, mystical atmosphere"),
            StylePrompt(style_name="anime", prompt="Redraw this portrait in Studio Ghibli style, vibrant colors and handdrawn aesthetic."),
        ],
        description="Prompt templates for different AI filter styles. These guide the AI generation process.",
    )

    # Custom prompt for user-defined styles
    custom_prompt: str = Field(
        default="professional photography, high quality, enhanced",
        description="Custom prompt text that will be used when 'custom' filter is selected. Users can modify this to create their own AI filter style.",
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
