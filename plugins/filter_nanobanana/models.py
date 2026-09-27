from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from .model_catalog import GeminiModelLiteral

# File extensions allowed for reference images.
ALLOWED_REFERENCE_EXTENSIONS: tuple[str, ...] = (".png", ".jpg", ".jpeg")
# Maximum number of reference images allowed per style prompt.
MAX_REFERENCE_IMAGES: int = 3


class StylePrompt(BaseModel):
    style_name: str = Field(
        description="The name for this AI filter style.",
    )
    prompt: str = Field(
        description="Prompt template to guide the AI generation process for this style.",
    )
    enabled: bool = Field(
        description="Enable this style prompt.",
        default=True,
    )
    model: GeminiModelLiteral | None = Field(
        default=None,
        description="Google Gemini model to use for this specific style. If not set, will use the default model from connection settings.",
    )
    reference_images: list[str] = Field(
        default=[],
        description=(
            "Optional reference images (1-3) that guide the AI's aesthetic. "
            "Each entry is a path relative to the project root, e.g. "
            "'plugins/filter_nanobanana/reference_images/chibi.jpg'. "
            "Only .png, .jpg and .jpeg files are supported."
        ),
    )

    @field_validator("reference_images")
    @classmethod
    def _validate_reference_images(cls, value: list[str]) -> list[str]:
        if len(value) > MAX_REFERENCE_IMAGES:
            raise ValueError(f"reference_images supports at most {MAX_REFERENCE_IMAGES} images, got {len(value)}")

        for entry in value:
            path = Path(entry)
            if path.suffix.lower() not in ALLOWED_REFERENCE_EXTENSIONS:
                raise ValueError(f"reference image '{entry}' has an unsupported extension. Allowed: {', '.join(ALLOWED_REFERENCE_EXTENSIONS)}")
            if not path.is_file():
                raise ValueError(f"reference image does not exist: {entry}")

        return value
