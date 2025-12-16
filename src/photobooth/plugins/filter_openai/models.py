from pydantic import BaseModel, Field


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
