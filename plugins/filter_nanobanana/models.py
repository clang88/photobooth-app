from typing import Optional

from pydantic import BaseModel, Field

from .model_catalog import GeminiModelLiteral


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
    model: Optional[GeminiModelLiteral] = Field(
        default=None,
        description="Google Gemini model to use for this specific style. If not set, will use the default model from connection settings.",
    )