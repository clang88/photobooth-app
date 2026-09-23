# AI Filter Plugins for Photobooth App

## Overview

This project includes two external AI filter plugins that transform photos using cloud-based image generation models:

- **filter_nanobanana** — Uses Google Gemini (Nano Banana) for AI-style transfers
- **filter_openai** — Uses OpenAI GPT Image models for AI-style transfers

These plugins are **external plugins** located in the `plugins/` directory. They hook into the photobooth image processing pipeline via [pluggy](https://pluggy.readthedocs.io/) hook specifications, meaning they are loaded dynamically at runtime.

---

## How Filters Work

When an image is captured, it flows through a **processing pipeline**:

```
Capture → Remove Background → Mount Background → Fill Color → Filter → Frame → Text
```

Each step is a `PipelineStep`. The AI filter plugins register a `PluginFilterStep` that sits in the pipeline and transforms the image.

### Hook Interface

Each filter plugin implements three hook methods:

| Hook Method | Purpose |
|---|---|
| `mp_avail_filter()` | Returns **all** available filter names for this plugin. Used to build the full list of filters the system knows about. |
| `mp_userselectable_filter()` | Returns **user-visible** filter names. When enabled, these filters appear in the UI gallery so users can pick them interactively. |
| `mp_filter_pipeline_step(image, filter_name, preview)` | The actual processing step. Called by the pipeline when this plugin's filter is selected. Returns the transformed image. |

### Unifying and De-unifying Filter Names

Because multiple plugins can define filters with the same name (e.g., "sketch"), each plugin qualifies its filter names:

```python
# unify: "FilterOpenai" + "sketch" → "FilterOpenai.sketch"
# deunify: reverse — extracts the raw name if it belongs to this plugin
```

---

## Two Ways to Use AI Filters

### 1. User-Selectable (Gallery Preview)

Users pick a filter from the gallery after capture by choosing from a visible list. This is configured via:

```jsonc
{
  "plugin_behavior": {
    "add_userselectable_filter": true,       // show filters in gallery UI
    "enable_fallback_on_error": true,        // show error overlay instead of failing
    "cache_results": true                     // cache results to avoid regenerating
  }
}
```

When enabled, the filters are exposed via the API endpoint `/api/filter/` and can be previewed with `/api/filter/{mediaitem_id}?filter=FilterOpenai.sketch`.

### 2. Pre-Configured in Actions (Pipeline Step)

Filters can be baked into an action's processing configuration. This applies the filter automatically without user intervention.

In the action config (`SingleImageProcessing` or `CollageProcessing`):

```jsonc
{
  "image_filter": "FilterOpenai.sketch"
}
```

Or for collages:

```jsonc
{
  "capture_image_filter": "FilterNanobanana.anime"
}
```

This is how filters are selected as part of a capture flow rather than interactively. The pipeline resolves the filter string to the correct plugin via `deunify()` and calls `mp_filter_pipeline_step()`.

---

## Configuration

Both plugins are configured in their respective JSON files:

| Plugin | Config File |
|---|---|
| Nano Banana (Gemini) | `config/plugin_filter_nanobanana.json` |
| OpenAI (GPT Image) | `config/plugin_filter_openai.json` |

### Connection Settings (`connection`)

| Setting | Nano Banana | OpenAI | Description |
|---|---|---|---|
| `gemini_api_key` / `openai_api_key` | ✅ | ✅ | The API key for the respective service. Obtain from [Google AI Studio](https://aistudio.google.com/app/apikey) or [OpenAI Dashboard](https://platform.openai.com/account/api-keys). |
| `default_model` | Gemini model (e.g., `gemini-1.5-flash`) | GPT model (e.g., `gpt-image-1.5`) | Default AI model used when no style prompt has its own model override. |
| `timeout_seconds` | ✅ | ✅ | Timeout for API calls (default: 120s, range: 5–300). |
| `max_retries` | ✅ | ✅ | Number of retry attempts on timeout (default: 1, range: 0–5). |

### Image Generation Settings (`image_generation`)

| Setting | Nano Banana | OpenAI | Description |
|---|---|---|---|
| `input_image_format` | ✅ | ❌ | Format to convert input images to before sending (jpeg/png/webp). Defaults to jpeg. |
| `aspect_ratio` | ✅ | ❌ | Gemini model-specific aspect ratios (1:1, 2:3, 3:2, etc.). |
| `image_size` | ✅ | ✅ | Resolution hint. Nanobanana: 1K/2K/4K; OpenAI: auto or specific sizes. |
| `response_modalities` | ✅ | ❌ | Gemini response types (image, text-image). |
| `max_input_image_size` | ✅ | ✅ | Max dimension for input images (default: 1024, range: 256–2048). Larger images are auto-resized. |
| `image_quality` | ❌ | ✅ | OpenAI-specific: auto/high/medium/low. |
| `input_fidelity` | ❌ | ✅ | How much the model preserves input details (high/low). |
| `output_format` | ❌ | ✅ | Output format for generated images (png/jpeg/webp). |
| `output_compression` | ❌ | ✅ | JPEG/WebP compression level (0–100%). |
| `moderation` | ❌ | ✅ | Content moderation level (low/auto). |

**Note:** Parameters not supported by the selected model will be logged by photobooth-app and ignored/fall back to a predefined default.

### Plugin Behavior Settings (`plugin_behavior`) — shared by both plugins

| Setting | Description |
|---|---|
| `add_userselectable_filter` | When `true`, the enabled style prompts appear in the gallery UI as filter choices. |
| `enable_fallback_on_error` | When `true`, a generated image with an overlaid error message is returned instead of crashing and showing a system error. |
| `cache_results` | When `true`, identical image+filter combinations are served from memory without re-calling the API. |

---

## Style Prompts (`style_prompts`)

Each plugin defines a list of pre-built AI-style prompts. These are the "filters" — each one carries:

```jsonc
{
  "style_name": "sketch",           // identifier shown in UI / used in action config
  "prompt": "pencil sketch...",     // sent to the AI model along with the image
  "enabled": true,                  // toggle on/off for user selection
  "model": null                     // optional: override default model for this specific style
}
```

Each plugin also defines a special `"custom"` and `"random"` style name. When `"custom"` filter is selected, the prompt is read from `{plugin_root}/custom_prompt/prompt.txt`, letting you edit it externally without touching the config file. Use the prompt editor at `http://localhost:8001` to manage prompts per plugin.

When `"random"` is selected, the filter will be randomly chosen from the enabled custom styles, always excluding `"custom"` and `"random"`.

---

## API Endpoints for Filter Preview

| Endpoint | Description |
|---|---|
| `GET /api/filter/` | Returns all user-selectable filter names. |
| `GET /api/filter/{mediaitem_id}?filter=FilterOpenai.sketch` | Returns a preprocessed preview image with the given filter applied. Used by the gallery UI for filter selection. |

### Preview Optimization

When a filter preview is requested (`preview=true`), the pipeline skips compute-intensive steps (e.g., background removal). The AI filter plugin returns a stylized image with the prompt name and provider logo during preview mode, so the UI can render a responsive gallery. The full transformation is only applied when the user confirms a filter choice and the image is processed for storage/production.

---

## Error Handling

Both plugins implement a **multi-level fallback**:

1. **Retry on timeout** — If the API call times out, the plugin retries up to `max_retries` times with a log message per attempt.
2. **Non-retryable failures** — Request errors (connection refused, etc.) and API errors (4xx/5xx) are raised immediately without retry.
3. **Error overlay** — If `enable_fallback_on_error` is `true`, the filter returns the original image with an overlaid text message describing the error. If `false`, the error is propagated up and the pipeline fails.

The error text overlay:
- Wraps long error messages to 4 lines max
- Uses a semi-transparent dark background rectangle for readability
- Auto-scales the font size relative to image width
- Falls back gracefully through system fonts (DejaVu Sans → Helvetica → PIL default)

---

## Feature Comparison: Nano Banana vs OpenAI

| Feature | Nano Banana (Gemini) | OpenAI (GPT Image) |
|---|---|---|
| **Models** | Gemini series (flash, pro, etc.) | GPT Image 1/1.5/2, Mini, Sunburst, Flare |
| **API approach** | Content generation (text + inline image) | Image edit API with multipart uploads |
| **Retry on timeout** | ✅ | ✅ |
| **Image resizing** | ✅ (LANCZOS, config-controlled max size) | ✅ (same mechanism) |
| **Custom prompt file** | ✅ (`custom_prompt/prompt.txt`) | ✅ (`custom_prompt/prompt.txt`) |
| **Error text overlay** | ✅ | ✅ |
| **Model-specific param capping** | Uses `model_catalog.py` helpers | Uses inline `MODEL_CONFIG` dict |
| **Input format config** | ✅ (jpeg/png/webp) | Hardcoded to jpeg |
| **Aspect ratio control** | ✅ (model-aware validation) | ❌ |
| **Quality presets** | ❌ | ✅ (auto/high/medium/low) |
| **Input fidelity** | ❌ | ✅ (high/low) |
| **Output compression** | ❌ | ✅ (0–100%) |

---

## Setup Checklist

1. **Install the plugin** — Ensure the `plugins/filter_nanobanana/` or `plugins/filter_openai/` directory exists under your photobooth's plugins path. The plugin system auto-detects and loads them at startup.

2. **Create the config file** — Create `config/plugin_filter_nanobanana.json` or `config/plugin_filter_openai.json` with your desired settings. Start from the defaults (see config files `config.py`) and override what you need.

3. **Set your API key** — Either edit the config JSON file directly or set environment variables:
   - Nano Banana: `filter-nanobanana-connection-gemini_api_key`
   - OpenAI: `filter-openai-connection-openai_api_key`

4. **Choose filter mode** — Decide whether filters are user-selectable (gallery UI) or pre-configured in actions:
   - Set `plugin_behavior.add_userselectable_filter` to `true` for gallery UI
   - Or set `image_filter` in the action's `SingleImageProcessing` config for automatic application

5. **Optional: enable custom prompts** — Add a `StylePrompt` entry with `"custom"` as the `style_name`, then place your prompt in `{plugin_root}/custom_prompt/prompt.txt`.

6. **Restart** — Restart the photobooth service so the new plugin config is loaded.

---

## Troubleshooting

| Problem | Likely Cause | Fix |
|---|---|---|
| Filters not showing in gallery | `add_userselectable_filter` is `false` or style prompts are disabled | Set to `true` and ensure at least one `style_prompt.enabled` is `true` |
| Filters not applying in actions | Filter name doesn't match `PluginFilters.Enum` member | Ensure the config uses the full qualified name like `"FilterOpenai.sketch"` |
| API returns error 401 | Wrong or expired API key | Check `config/plugin_filter_*.json` and verify the key with the provider |
| API returns error 429 | Rate limiting / too many requests | Increase `timeout_seconds`, reduce concurrency, or check model quotas |
| Slow processing | Large input images hitting the API / slow model | Switch model (`gemini-3.1-flash-image` or `gemini-3.1-flash-lite-image` or `gpt-image-2.5-flare`), decrease `max_input_image_size` or check network latency to API endpoint |
| Black/dark fallback image (no text) | PIL or ImageDraw is not available / error overlay failed to load | The filter should show an error text overlay. If it fails silently, check logs in `log/`. |
| Custom prompt not loaded from file | `custom_prompt/prompt.txt` doesn't exist or plugin path is wrong | Ensure `{plugin_root}/custom_prompt/prompt.txt` exists and is readable |