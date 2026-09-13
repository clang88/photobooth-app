from typing import Literal, TypedDict, get_args

OpenAIModelLiteral = Literal[
    "gpt-image-1",
    "gpt-image-1-mini",
    "gpt-image-1.5",
    "gpt-image-2",
    "gpt-image-2.5-sunburst",
    "gpt-image-2.5-flare",
]

OPENAI_MODEL_VALUES: tuple[OpenAIModelLiteral, ...] = get_args(OpenAIModelLiteral)

DEFAULT_OPENAI_MODEL: OpenAIModelLiteral = "gpt-image-2.5-flare"


class OpenAIModelConfig(TypedDict):
    supported_params: set[str]
    defaults: dict[str, str]
    supported_values: dict[str, tuple[str, ...]]


GPT_IMAGE_SIZE_VALUES: tuple[str, ...] = ("1024x1024", "1536x1024", "1024x1536", "auto")
GPT_IMAGE_QUALITY_VALUES: tuple[str, ...] = ("low", "medium", "high", "auto")
GPT_IMAGE_25_QUALITY_VALUES: tuple[str, ...] = ("low", "medium", "high", "xhigh", "max", "auto")

GPT_IMAGE_BASE_PARAMS: set[str] = {
    "model",
    "prompt",
    "n",
    "size",
    "quality",
    "output_format",
    "background",
    "output_compression",
    "partial_images",
    "stream",
    "user",
    "moderation",
}

OPENAI_MODEL_CONFIGS: dict[str, OpenAIModelConfig] = {
    "gpt-image-1": {
        "supported_params": GPT_IMAGE_BASE_PARAMS | {"input_fidelity"},
        "defaults": {"size": "auto", "quality": "auto", "output_format": "jpeg", "input_fidelity": "low"},
        "supported_values": {"size": GPT_IMAGE_SIZE_VALUES, "quality": GPT_IMAGE_QUALITY_VALUES},
    },
    "gpt-image-1-mini": {
        "supported_params": GPT_IMAGE_BASE_PARAMS,
        "defaults": {"size": "auto", "quality": "auto", "output_format": "jpeg"},
        "supported_values": {"size": GPT_IMAGE_SIZE_VALUES, "quality": GPT_IMAGE_QUALITY_VALUES},
    },
    "gpt-image-1.5": {
        "supported_params": GPT_IMAGE_BASE_PARAMS | {"input_fidelity"},
        "defaults": {"size": "auto", "quality": "auto", "output_format": "jpeg", "input_fidelity": "low"},
        "supported_values": {"size": GPT_IMAGE_SIZE_VALUES, "quality": GPT_IMAGE_QUALITY_VALUES},
    },
    "gpt-image-2": {
        "supported_params": GPT_IMAGE_BASE_PARAMS,
        "defaults": {"size": "auto", "quality": "auto", "output_format": "jpeg"},
        "supported_values": {"size": GPT_IMAGE_SIZE_VALUES, "quality": GPT_IMAGE_QUALITY_VALUES},
    },
    "gpt-image-2.5-sunburst": {
        "supported_params": GPT_IMAGE_BASE_PARAMS,
        "defaults": {"size": "auto", "quality": "auto", "output_format": "jpeg"},
        "supported_values": {"size": GPT_IMAGE_SIZE_VALUES, "quality": GPT_IMAGE_25_QUALITY_VALUES},
    },
    "gpt-image-2.5-flare": {
        "supported_params": GPT_IMAGE_BASE_PARAMS,
        "defaults": {"size": "auto", "quality": "auto", "output_format": "jpeg"},
        "supported_values": {"size": GPT_IMAGE_SIZE_VALUES, "quality": GPT_IMAGE_25_QUALITY_VALUES},
    },
}
