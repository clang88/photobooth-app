"""Configuration for the unified AI filter plugin."""

from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import SettingsConfigDict

from photobooth import CONFIG_PATH
from photobooth.services.config.baseconfig import BaseConfig

from .models import StylePrompt



class ConnectionSettings(BaseModel):
    """Connection settings for all AI providers."""

    google_gemini_api_key: str = Field(
        default="",
        description="Google Gemini API key for AI image processing. Obtain from https://aistudio.google.com/app/apikey",
    )

    openai_api_key: str = Field(
        default="",
        description="OpenAI API key for GPT image processing. Obtain from https://platform.openai.com/account/api-keys",
    )

    default_model: Literal[
        "gemini-2.5-flash-image",
        "gemini-3-pro-image-preview",
        "gpt-image-1",
        "gpt-image-1-mini",
        "gpt-image-1.5",
    ] = Field(
        default="gemini-2.5-flash-image",
        description="Default AI model to use for image generation when no model is specified in style prompts. "
                   "Gemini models: gemini-2.5-flash-image (fast), gemini-3-pro-image-preview (quality). "
                   "OpenAI models: gpt-image-1 (balanced), gpt-image-1-mini (fast), gpt-image-1.5 (advanced). "
                   "Note: Only models from providers with configured API keys will work.",
    )

    timeout_seconds: int = Field(
        default=120,
        ge=5,
        le=300,
        description="Timeout for AI API calls in seconds (applies to all providers).",
    )


class ImageGenerationSettings(BaseModel):
    """Image generation settings for all AI providers."""

    # Google Gemini specific settings
    gemini_input_image_format: Literal["jpeg", "png", "webp"] = Field(
        default="jpeg",
        description="[Gemini] Format to convert input images to before sending to Gemini API.",
    )

    gemini_aspect_ratio: Literal["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"] = Field(
        default="1:1",
        description="[Gemini] Aspect ratio for generated images.",
    )

    gemini_image_size: Literal["1K", "2K", "4K"] = Field(
        default="1K",
        description="[Gemini] Resolution for generated images. Only available for gemini-3-pro-image-preview model.",
    )

    gemini_response_modalities: list[Literal["TEXT", "IMAGE"]] = Field(
        default=["IMAGE"],
        description="[Gemini] Response modalities - can include TEXT and/or IMAGE.",
    )

    gemini_max_input_image_size: int = Field(
        default=1024,
        ge=256,
        le=2048,
        description="[Gemini] Maximum dimension (width or height) for images sent to the API.",
    )

    # OpenAI specific settings
    openai_image_quality: Literal["auto", "high", "medium", "low"] = Field(
        default="auto",
        description="[OpenAI] Quality of generated images. 'auto' lets the model choose the best quality.",
    )

    openai_image_size: Literal["auto", "1024x1024", "1536x1024", "1024x1536", "256x256", "512x512", "1792x1024", "1024x1792"] = Field(
        default="auto",
        description="[OpenAI] Size of generated images. 'auto' lets the model choose optimal size.",
    )

    openai_input_fidelity: Literal["high", "low"] = Field(
        default="low",
        description="[OpenAI] Control how much effort the model exerts to match input image style and features. "
                   "'high' preserves more details but takes longer. Only supported by gpt-image-1 and gpt-image-1.5.",
    )

    openai_output_format: Literal["png", "jpeg", "webp"] = Field(
        default="jpeg",
        description="[OpenAI] Output format for generated images. PNG supports transparency, JPEG is smaller, WEBP offers good compression.",
    )

    openai_output_compression: int = Field(
        default=85,
        ge=0,
        le=100,
        description="[OpenAI] Compression level (0-100%) for generated images when using JPEG or WebP format. "
                   "Higher values = better quality but larger files.",
    )

    openai_moderation: Literal["low", "auto"] = Field(
        default="auto",
        description="[OpenAI] Content-moderation level for images. 'low' for less restrictive filtering or 'auto' (default).",
    )


class PluginBehaviorSettings(BaseModel):
    """Plugin behavior configuration."""

    add_userselectable_filter: bool = Field(
        default=True,
        description="Add userselectable AI filters to the list the user can choose from. "
                   "When enabled, all enabled style_prompts will be available for user selection.",
    )

    enable_fallback_on_error: bool = Field(
        default=True,
        description="If AI generation fails, return the original image instead of an error.",
    )

    cache_results: bool = Field(
        default=True,
        description="Cache AI-generated results to avoid regenerating the same image multiple times.",
    )


class FilterAiConfig(BaseConfig):
    """Configuration for the unified AI filter plugin."""

    model_config = SettingsConfigDict(
        title="AI Filter Plugin Config",
        json_file=f"{CONFIG_PATH}plugin_filter_ai.json",
        env_prefix="filter-ai-",
    )

    connection: ConnectionSettings = Field(
        default_factory=ConnectionSettings,
        description="Connection settings for all AI providers (API keys and default model).",
    )

    image_generation: ImageGenerationSettings = Field(
        default_factory=ImageGenerationSettings,
        description="Image generation settings for all AI providers.",
    )

    plugin_behavior: PluginBehaviorSettings = Field(
        default_factory=PluginBehaviorSettings,
        description="Plugin behavior settings.",
    )

    # Style prompts for different filter types
    style_prompts: list[StylePrompt] = Field(
        default=[
            StylePrompt(
                style_name="jojo",
                prompt="Redraw this portrait in the style of Jojo's Bizarre Adventure, exaggerated poses and vibrant colors with thick lines.",
                provider="google_gemini",
                model="gemini-2.5-flash-image",
            ),
            StylePrompt(
                style_name="anime",
                prompt="Redraw this portrait in an anime style similar to Howl's Moving Castle by Studio Ghibli.",
                provider="google_gemini",
                model="gemini-2.5-flash-image",
            ),
            StylePrompt(
                style_name="cartoon",
                prompt="Transform this portrait into a cartoon style, animated, colorful, disney-like illustration",
                provider="openai",
                model="gpt-image-1",
            ),
            StylePrompt(
                style_name="sketch",
                prompt="Convert this portrait to a pencil sketch, black and white drawing, artistic sketch",
                provider="openai",
                model="gpt-image-1-mini",
            ),
            StylePrompt(
                style_name="watercolor",
                prompt="Transform this portrait into a watercolor painting, soft brush strokes, artistic",
                provider="openai",
                model="gpt-image-1",
            ),
            StylePrompt(
                style_name="oil_painting",
                prompt="Convert this portrait to an oil painting, classical art style, rich textures",
                provider="openai",
                model="gpt-image-1",
            ),
            StylePrompt(
                style_name="vintage",
                prompt="Transform this portrait to vintage photography style, sepia tones, retro aesthetic",
                provider="google_gemini",
                model="gemini-2.5-flash-image",
            ),
            StylePrompt(
                style_name="cyberpunk",
                prompt="Redraw this portrait in cyberpunk style, neon lights, futuristic, sci-fi aesthetic",
                provider="google_gemini",
                model="gemini-2.5-flash-image",
            ),
            StylePrompt(
                style_name="fantasy",
                prompt="Transform this portrait into fantasy art, magical, ethereal, mystical atmosphere",
                provider="google_gemini",
                model="gemini-2.5-flash-image",
            ),
            StylePrompt(
                style_name="pixar",
                prompt="Redraw this portrait in Pixar animation style, 3D rendered appearance, colorful and friendly",
                provider="openai",
                model="gpt-image-1.5",
            ),
        ],
        description="Style prompts for different filter types. Each prompt specifies which AI provider and model to use.",
    )
