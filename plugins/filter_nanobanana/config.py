from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import SettingsConfigDict

from photobooth import CONFIG_PATH
from photobooth.services.config.baseconfig import BaseConfig

from .model_catalog import COMMON_ASPECT_RATIOS, DEFAULT_GEMINI_MODEL, GEMINI_MODEL_VALUES, MODEL_IMAGE_SIZES, GeminiModelLiteral
from .models import ALLOWED_REFERENCE_EXTENSIONS, StylePrompt

MODELS_WITH_IMAGE_SIZE = ", ".join(model for model in GEMINI_MODEL_VALUES if MODEL_IMAGE_SIZES[model])
SUPPORTED_ASPECT_RATIOS_DESCRIPTION = ", ".join(COMMON_ASPECT_RATIOS)


class ConnectionSettings(BaseModel):
    gemini_api_key: str = Field(
        default="",
        description="Google Gemini API key for AI image processing. Obtain from https://aistudio.google.com/app/apikey",
    )

    default_model: GeminiModelLiteral = Field(
        default=DEFAULT_GEMINI_MODEL,
        description="Default Google Gemini model to use for image generation when no model is specified in style prompts. Use flash-lite-image for maximum speed and lowest cost (1K only), flash-image for speed, pro-image for quality.",
    )

    timeout_seconds: int = Field(
        default=120,
        ge=5,
        le=300,
        description="Timeout for AI API calls in seconds.",
    )

    max_retries: int = Field(
        default=1,
        ge=0,
        le=5,
        description="Number of retry attempts when an API call times out. Set to 0 to disable retries.",
    )


class ImageGenerationSettings(BaseModel):
    input_image_format: Literal["jpeg", "png", "webp"] = Field(
        default="jpeg",
        description="Format to convert input images to before sending to Gemini API.",
    )

    aspect_ratio: Literal["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"] = Field(
        default="1:1",
        description=f"Aspect ratio for generated images. Supported values: {SUPPORTED_ASPECT_RATIOS_DESCRIPTION}.",
    )

    image_size: Literal["1K", "2K", "4K"] = Field(
        default="1K",
        description=f"Resolution for generated images. Supported by: {MODELS_WITH_IMAGE_SIZE}.",
    )

    response_modalities: list[Literal["TEXT", "IMAGE"]] = Field(
        default=["IMAGE"],
        description="Response modalities - can include TEXT and/or IMAGE.",
    )

    max_input_image_size: int = Field(
        default=1024,
        ge=256,
        le=2048,
        description="Maximum dimension (width or height) for images sent to the API.",
    )


class PluginBehaviorSettings(BaseModel):
    add_userselectable_filter: bool = Field(
        default=True,
        description="Add userselectable AI filters to the list the user can choose from. When enabled, all enabled style_prompts will be available for user selection.",
    )

    enable_fallback_on_error: bool = Field(
        default=True,
        description="If AI generation fails, return the original image instead of an error.",
    )

    cache_results: bool = Field(
        default=True,
        description="Cache AI-generated results to avoid regenerating the same image multiple times.",
    )


class FilterNanobananaConfig(BaseConfig):
    model_config = SettingsConfigDict(
        title="Nano Banana Filter Plugin Config",
        json_file=f"{CONFIG_PATH}plugin_filter_nanobanana.json",
        env_prefix="filter-nanobanana-",
    )

    connection: ConnectionSettings = ConnectionSettings()
    image_generation: ImageGenerationSettings = ImageGenerationSettings()
    plugin_behavior: PluginBehaviorSettings = PluginBehaviorSettings()

    # Style prompts for different filter types
    style_prompts: list[StylePrompt] = Field(
        default=[
            StylePrompt(
                style_name="1996",
                prompt="Keep framing and faces unchanged. Dress the people in typical 1990s attire (oversized T-Shirts, colorful windbreakers, flannel shirts etc.) and give them 90s hairdos. In the style of a throw-away film camera photo and imprint the date 08.10.1996 like on 90s disposable cameras. Maintain their exact faces and poses.",
            ),
            StylePrompt(
                style_name="kaleidoscope",
                prompt="Symmetrical kaleidoscope portrait effect, repeating geometric mirror patterns while keeping the subject's face fully recognizable and centered.",
            ),
            StylePrompt(style_name="ghibli", prompt="Redraw this in the style of Studio Ghibli. Make older people look a bit younger than they are."),
            StylePrompt(
                style_name="jojo",
                prompt="Redraw this portrait in the style of the new anime version of Jojo's Bizarre Adventure, while keeping the facial features and hair of the people mostly unchanged. Slightly exaggerate the poses and use vibrant colors with thick lines and stylized text.",
            ),
            StylePrompt(style_name="cartoon", prompt="Transform this portrait into a cartoon style, animated, colorful, disney-like illustration"),
            StylePrompt(
                style_name="sketch",
                prompt="Pencil sketch, black and white drawing, artistic sketch. Keep people recognizable and maintain their poses.",
            ),
            StylePrompt(style_name="watercolor", prompt="Watercolor painting, soft brush strokes, artistic."),
            StylePrompt(style_name="vintage", prompt="Transform this portrait to vintage photography style, sepia tones, retro aesthetic"),
            StylePrompt(
                style_name="barbie",
                prompt="Redraw this portrait in the style of Mattel's Barbie, vibrant colors, fashionable outfits, and playful aesthetic. Make everyone plastic, but keep poses and framing.",
            ),
            StylePrompt(
                style_name="fantasy",
                prompt='Photorealistic Elven style transfer. Keep subject\'s features and background geometry 1:1, but dress the subject(s) in fancy elven clothes. Adjust lighting to be low-contrast and ethereal. Add "The Fellowship of the Ring" film grain and color palette. Subtle elven ear modification. High-end fantasy film aesthetic, soft romantic lighting, shimmering highlights, 8k resolution, cinematic bloom.',
            ),
            StylePrompt(
                style_name="dragonball",
                prompt="Redraw this in the style of Classic Dragon Ball by Akira Toriyama, don't change the subjects features and poses too much. Clean, bold anime style with sharp linework, simple but expressive faces with the typical Toriyama eyes, large spiky hair and strong silhouettes. Bright, flat colors with minimal shading, clear outlines, and a playful yet powerful tone. Characters appear energetic and iconic, with a mix of humor and intense martial-arts action.",
            ),
            StylePrompt(style_name="pixar", prompt="Redraw this portrait in Pixar animation style, 3D rendered appearance, colorful and friendly"),
            StylePrompt(
                style_name="ken",
                prompt="Redraw this in a hyper-detailed 1980s retro anime style, 'Fist of the North Star' aesthetic. Men are depicted with extreme muscular hypertrophy, defined deltoids, and rugged, scarred features. Women are drawn with ethereal elegance, large expressive eyes, and soft porcelain skin. Character poses are dramatic and high-tension with heavy black ink cross-hatching and intense 'Gekiga' line work. Dramatic high-contrast shadows, cinematic desert wasteland lighting, 8mm film grain texture.",
            ),
            StylePrompt(
                style_name="tattoo",
                prompt="Make the people in the photo look like Yakuza, show their tattoos prominently, but avoid face tatoos. Remember, NO face tattoos. Keep their faces, poses, and expressions unchanged. Do not add or remove people!",
            ),
            StylePrompt(
                style_name="mountain",
                prompt="Add realistic technical hiking gear and backpacks to the people in the photo. Keep the framing, faces, expressions, and poses completely unchanged, but replace the background with a scenic mountain landscape. Faces need to stay completely unchanged!",
            ),
            StylePrompt(
                style_name="chibi",
                prompt="Transform the people in the main image into super deformed chibi characters while keeping their faces and expressions recognizable and the poses unchanged. Make sure to always show the full body, even if it is cut off in the main image.Copy the style exactly from the reference image 1.",
                reference_images=["plugins/filter_nanobanana/reference_images/chibi.jpg"],
            ),
            StylePrompt(
                style_name="lego",
                prompt="Redraw this portrait in the style of LEGO minifigures, keeping the subjects' facial features and poses recognizable. Use bright, blocky colors and maintain the iconic LEGO aesthetic.",
            ),
            StylePrompt(
                style_name="8-bit",
                prompt="Redraw all people as a JRPG 8-bit party top-down view. Keep them recognizable but draw them in a pixalated 8-bit style. Don't add names to the characters.",
            ),
            StylePrompt(
                style_name="metal_slug",
                prompt='Transform this image into a homage to the Metal Slug character select screen with highly stylized pixelated portraits of each person in the frame. Keep their expressions recognizable but draw them in the exaggerated, colorful sprite character portraits style with dramatic lighting like in the reference image. Add "P1", "P2", etc. above each person like the game\'s selection screen, and add funny nick-names based on their features under the portraits. Follow the style of the faces and select screen exactly from the reference image 1.',
                reference_images=[
                    "plugins/filter_nanobanana/reference_images/metal_slug_select.jpg",
                ],
            ),
            StylePrompt(
                style_name="matrix",
                prompt="Make the people in the image look like they come straight out of the Matrix, wearing leather jackets, sunglasses, but keep their faces and expressions recognizable and the poses unchanged. Slight green color grading over the image reminiscent of the movies.",
            ),
            StylePrompt(
                style_name="impressionist",
                prompt="Redraw this portrait in the style of Impressionist painters like Claude Monet, Van Gogh or Pierre-Auguste Renoir, with visible brushstrokes, soft lighting, and a focus on capturing the overall atmosphere rather than fine details.",
            ),
            StylePrompt(
                style_name="custom",
                prompt="This prompt is read from the 'custom_prompt/prompt.txt' file in the filter_nanobanana plugin folder. Do not modify!",
            ),
            StylePrompt(
                style_name="random",
                prompt="This prompt selects one of the enabled prompts randomly (excluding custom and random). Do not modify!",
            ),
        ],
        description="Prompt templates for different AI filter styles. These guide the AI generation process.",
    )

    def _reference_image_options(self) -> list[str]:
        """Return CWD-relative paths of the reference images available for selection in the UI."""
        ref_dir = Path(__file__).resolve().parent / "reference_images"
        if not ref_dir.is_dir():
            return []
        try:
            base = ref_dir.relative_to(Path.cwd())
        except ValueError:
            # If the plugin is not under the CWD (unusual), fall back to absolute paths.
            base = ref_dir
        options: list[str] = []
        for file in sorted(ref_dir.iterdir()):
            if file.is_file() and file.suffix.lower() in ALLOWED_REFERENCE_EXTENSIONS:
                options.append((base / file.name).as_posix())
        return options

    def get_schema(self):
        """Get schema to build UI.

        Extends the base schema by injecting the available reference images as
        ``enum`` options on the ``reference_images`` field, so the frontend renders
        a multiselect dropdown instead of free-text inputs.
        """
        schema = super().get_schema()
        options = self._reference_image_options()

        def inject(node):
            if isinstance(node, dict):
                props = node.get("properties")
                if isinstance(props, dict) and "reference_images" in props:
                    field = props["reference_images"]
                    if isinstance(field, dict) and isinstance(field.get("items"), dict):
                        field["items"]["enum"] = options
                for value in node.values():
                    inject(value)
            elif isinstance(node, list):
                for value in node:
                    inject(value)

        inject(schema)
        return schema
