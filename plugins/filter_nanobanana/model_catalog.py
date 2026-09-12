from typing import Literal, get_args


GeminiModelLiteral = Literal[
    "gemini-2.5-flash-image",
    "gemini-3-pro-image",
    "gemini-3.1-flash-image",
]

GEMINI_MODEL_VALUES: tuple[str, ...] = get_args(GeminiModelLiteral)

DEFAULT_GEMINI_MODEL: GeminiModelLiteral = "gemini-3.1-flash-image"

COMMON_ASPECT_RATIOS: tuple[str, ...] = (
    "1:1",
    "2:3",
    "3:2",
    "3:4",
    "4:3",
    "4:5",
    "5:4",
    "9:16",
    "16:9",
    "21:9",
)


MODEL_IMAGE_SIZES: dict[GeminiModelLiteral, tuple[str, ...]] = {
    "gemini-2.5-flash-image": (),
    "gemini-3-pro-image": ("1K", "2K", "4K"),
    "gemini-3.1-flash-image": ("512", "1K", "2K", "4K"),
}


def get_allowed_aspect_ratios(model: GeminiModelLiteral) -> tuple[str, ...]:
    _ = model
    return COMMON_ASPECT_RATIOS


def get_allowed_image_sizes(model: GeminiModelLiteral) -> tuple[str, ...]:
    return MODEL_IMAGE_SIZES[model]


def supports_image_size(model: GeminiModelLiteral) -> bool:
    return bool(get_allowed_image_sizes(model))