from typing import Literal, cast

from pydantic import BaseModel, Field
from pydantic_settings import SettingsConfigDict

from photobooth import CONFIG_PATH
from photobooth.services.config.baseconfig import BaseConfig

from .model_catalog import COMMON_ASPECT_RATIOS, DEFAULT_GEMINI_MODEL, GEMINI_MODEL_VALUES, MODEL_IMAGE_SIZES, GeminiModelLiteral
from .models import StylePrompt


MODELS_WITH_IMAGE_SIZE = ", ".join(
    cast(str, model) for model in GEMINI_MODEL_VALUES if MODEL_IMAGE_SIZES[model]
)
SUPPORTED_ASPECT_RATIOS_DESCRIPTION = ", ".join(COMMON_ASPECT_RATIOS)


class ConnectionSettings(BaseModel):
    gemini_api_key: str = Field(
        default="",
        description="Google Gemini API key for AI image processing. Obtain from https://aistudio.google.com/app/apikey",
    )

    default_model: GeminiModelLiteral = Field(
        default=DEFAULT_GEMINI_MODEL,
        description="Default Google Gemini model to use for image generation when no model is specified in style prompts. Use flash-image for speed, pro-image for quality.",
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
            StylePrompt(style_name="jojo", prompt="Redraw this portrait in the style of Jojo's Bizarre Adventure, exaggerated poses and vibrant colors with thick lines."),
            StylePrompt(style_name="anime", prompt="Redraw this in the style of Studio Ghibli. Make older people look a bit younger than they are."),
            StylePrompt(style_name="dragonball", prompt="Redraw this in the style of Classic Dragon Ball by Akira Toriyama, don't change the subjects features and poses too much. Clean, bold anime style with sharp linework, simple but expressive faces with the typical Toriyama eyes, large spiky hair and strong silhouettes. Bright, flat colors with minimal shading, clear outlines, and a playful yet powerful tone. Characters appear energetic and iconic, with a mix of humor and intense martial-arts action."),
            StylePrompt(style_name="cartoon", prompt="Transform this portrait into a cartoon style, animated, colorful, disney-like illustration"),
            StylePrompt(style_name="sketch", prompt="Convert this portrait to a pencil sketch, black and white drawing, artistic sketch"),
            StylePrompt(style_name="watercolor", prompt="Transform this portrait into a watercolor painting, soft brush strokes, artistic"),
            StylePrompt(style_name="oil_painting", prompt="Convert this portrait to an oil painting, classical art style, rich textures"),
            StylePrompt(style_name="vintage", prompt="Transform this portrait to vintage photography style, sepia tones, retro aesthetic"),
            StylePrompt(style_name="cyberpunk", prompt="Redraw this portrait in cyberpunk style, neon lights, futuristic, sci-fi aesthetic"),
            StylePrompt(style_name="fantasy", prompt="hotorealistic Elven style transfer. Keep subject's features and background geometry 1:1, but dress the subject(s) in fancy elven clothes. Adjust lighting to be low-contrast and ethereal. Add \"The Fellowship of the Ring\" film grain and color palette. Subtle elven ear modification. High-end fantasy film aesthetic, soft romantic lighting, shimmering highlights, 8k resolution, cinematic bloom."),
            StylePrompt(style_name="pixar", prompt="Redraw this portrait in Pixar animation style, 3D rendered appearance, colorful and friendly"),
            StylePrompt(style_name="custom", prompt="This prompt is read from a the 'prompt.txt' file in the {CONFIG_PATH}/photobooth-data/prompts/ folder. Do not modify!"),
            StylePrompt(style_name="4-vacation", prompt="Dress the people in vacation attire, including umbrellas, sunglasses and hats. Maintain their exact faces and poses."),
            StylePrompt(style_name="5-bachelor-party", prompt="Put the people into a bachelor party scene, with flashing lights, confetti, videogames (PS4) and baskets of stuff to sell. They all wear party hats. Keep their faces and poses unchanged."),
            StylePrompt(style_name="6-vacation-2", prompt="Apply a light filter that overlays a semi-transparent collage of passport entry stamps from different countries (e.g., Austria, Italy, Spain, Thailand) across the image and some airplanes and trains, *avoiding* covering the people's faces. Keep the subjects and background unchanged."),
            StylePrompt(style_name="7-train", prompt="Put old-fashioned train conductors hats on all the people in the image and put a steam-powered train into the background. Keep their faces, poses, and expressions unchanged. Do not add or remove people!"),
            StylePrompt(style_name="8-car", prompt="Make all the people in the image sit on their own small kid's toy car. Keep their faces and expressions unchanged, but adapt their poses to fit them in the car. Do not add or remove people!"),
            StylePrompt(style_name="9-hairstyle", prompt="Make all people in the photo bald and add a sparkle to their head. Keep their faces (including beards), poses, and expressions unchanged. Do not add or remove people!"),
            StylePrompt(style_name="10-200km", prompt="Make all the people in the image look like adventurers and travelers with dirty and worn clothes. They wear backpacks and heavy traveling boots. The person in the middle holds a map and a compass. Keep their faces, poses, and expressions as well as the background unchanged. Do not add or remove people!"),
            StylePrompt(style_name="11-pet", prompt="Add photorealistic pet dinosaurs on a leash to each person. Add one T-Rex in the background trying to fit the frame. Keep their faces, poses, and expressions unchanged, but adapt the poses if necessary to have them sit in their chairs. Do not add or remove people!"),
            StylePrompt(style_name="12-teacher", prompt="Redraw the image in an anime style, with the people dressed as students in a classroom setting. Keep their faces, poses, and expressions recognizable. Do not add or remove people!"),
            StylePrompt(style_name="13-musicians", prompt="Put all the people in the image on a music stage, playing instruments, while keeping their faces, poses, and expressions recognizable. Do it in a chibi cute anime style."),
            StylePrompt(style_name="14-endurance", prompt="Put the people on a track and field racing track. They are wearing sportswear and running shoes. Keep their faces, and expressions recognizable. Draw it in a black and white sketch like style. Do not add or remove people!"),
            StylePrompt(style_name="15-mountain", prompt="Put the people on a mountain top, wearing hiking gear and backpacks. Keep their faces, poses, and expressions unchanged. Draw it in a realistic style. Do not add or remove people!"),
            StylePrompt(style_name="16-spicy", prompt="Make all the people in the image spit fire as they ate extremely spicy food. They are sweaty and red but happy. Do not add or remove people!"),
            StylePrompt(style_name="17-virgo", prompt="Make all the people in the image look like fair men or women dressed like the zodiac sign Virgo. Put them in white tunicas and give them flowing beautiful hair. Keep their faces, poses, and expressions unchanged. Do not add or remove people!"),
            StylePrompt(style_name="20-glasses", prompt="Give all the people in the image googly eyes. Keep their faces, poses, and expressions unchanged. Do not add or remove people!"),
            StylePrompt(style_name="21-multilingual", prompt="Add speech bubbles to the top of the peoples heads in the image, saying funny things in a different language (Japanese, Chinese, English, Spanish, German, Italian). Keep their faces, poses, and expressions unchanged. Do not add or remove people!"),
            StylePrompt(style_name="22-aries", prompt="Give all people in the piture horns like a ram. Keep their faces, poses, and expressions unchanged. Do not add or remove people!"),
            StylePrompt(style_name="23-tatoo", prompt="Make the people in the photo look like Yakuza, show their tattoos prominently, but avoid face tatoos. Remember, NO face tattoos. Keep their faces, poses, and expressions unchanged. Do not add or remove people!"),
            StylePrompt(style_name="24-series", prompt="Put the people inside of a TV and make it look like romantic NETFLIX TV show titled 'Wedding Season'. Avoid changing their faces, poses or expressions. Do not add or remove people!"),
            StylePrompt(style_name="25-gamers", prompt="Put all the people in this image into a 2D side-scroller beat 'em up video game scene. Make them all fight a godzilla with a bride veil. Keep them recognizable but draw them in a pixalated 8-bit style. Don't add names to the characeters, only the bridezilla healthbar should have a name."),
            StylePrompt(style_name="26-japan", prompt="Modify only the clothing of the people in the image. Change their current outfits into traditional Japanese kimonos or yukatas. Crucially, do not alter, remove, or replace any people. Keep all faces, identical facial expressions, body poses, and the background exactly as they are in the original image."),
        ],
        description="Prompt templates for different AI filter styles. These guide the AI generation process.",
    )