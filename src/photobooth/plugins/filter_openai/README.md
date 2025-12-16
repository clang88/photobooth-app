# AI Image Generation Filter Plugin

This plugin adds AI-powered image filters to the photobooth application, allowing users to apply various artistic styles and enhancements to their photos using state-of-the-art AI models.

## Features

- **Multiple AI Providers**: Support for OpenAI DALL-E, Stability AI, Replicate, and local Stable Diffusion
- **Variety of Styles**: Style transfer, enhancement, cartoon, sketch, watercolor, oil painting, vintage, cyberpunk, fantasy, and anime styles
- **Configurable Parameters**: Adjustable generation strength, steps, and timeouts
- **Caching**: Optional result caching to avoid regenerating identical images
- **Fallback Support**: Option to return original image if AI generation fails
- **Preview Mode**: Faster processing for quick previews

## Configuration

### Basic Settings

- `add_userselectable_filter`: Enable/disable user-selectable AI filters in the UI
- `userselectable_filter`: List of filter types available to users
- `ai_provider`: Choose between "openai", "stability_ai", "replicate", or "local_stable_diffusion"

### Provider Settings

#### OpenAI
- `openai_api_key`: Your OpenAI API key (required)
- `openai_model`: Model to use (dall-e-2, dall-e-3)

#### Stability AI
- `stability_api_key`: Your Stability AI API key (required)

#### Replicate
- `replicate_api_key`: Your Replicate API key (required)

#### Local Stable Diffusion
- `local_sd_endpoint`: URL of your local Stable Diffusion API (e.g., Automatic1111 WebUI)

### Generation Parameters

- `generation_strength`: How strong the AI transformation should be (0.1-1.0)
- `generation_steps`: Number of inference steps (10-50, more = higher quality but slower)
- `timeout_seconds`: API timeout in seconds (5-120)

### Advanced Settings

- `style_prompts`: Custom prompts for each filter style
- `enable_fallback_on_error`: Return original image if AI generation fails
- `cache_results`: Cache generated images to avoid repeated processing

## Available Filter Types

1. **style_transfer**: General artistic style transfer
2. **enhance**: Image enhancement and upscaling
3. **cartoon**: Disney-like cartoon style
4. **sketch**: Pencil sketch black and white drawing
5. **watercolor**: Soft watercolor painting effect
6. **oil_painting**: Classical oil painting style
7. **vintage**: Retro/sepia photography effect
8. **cyberpunk**: Futuristic neon cyberpunk style
9. **fantasy**: Magical and mystical atmosphere
10. **anime**: Japanese animation/manga style

## Setup Instructions

### 1. API Key Configuration

Choose your preferred AI provider and obtain an API key:

- **OpenAI**: Visit [OpenAI Platform](https://platform.openai.com/api-keys)
- **Stability AI**: Visit [Stability AI Platform](https://platform.stability.ai/account/keys)
- **Replicate**: Visit [Replicate](https://replicate.com/account/api-tokens)

### 2. Configuration

1. Open the photobooth admin interface
2. Navigate to Plugin Configuration
3. Select "AI Filter Plugin"
4. Configure your preferred provider and API key
5. Adjust generation parameters as needed
6. Select which filters to make available to users

### 3. Local Stable Diffusion Setup (Optional)

For local processing without cloud APIs:

1. Install [Automatic1111 WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui)
2. Start with `--api` flag: `./webui.sh --api`
3. Set `local_sd_endpoint` to your WebUI URL (default: http://127.0.0.1:7860)

## Usage

Once configured, AI filters will appear in the photobooth filter selection alongside other filters like Pilgram2. Users can:

1. Take a photo
2. Select an AI filter from the gallery
3. Preview the AI-generated result
4. Apply the filter to save the transformed image

## Performance Considerations

- **Cloud APIs**: Require internet connection and have usage costs
- **Processing Time**: AI generation typically takes 10-30 seconds
- **Caching**: Enable caching to avoid regenerating identical images
- **Preview Mode**: Uses faster/smaller processing for quick previews
- **Local Setup**: No usage costs but requires powerful hardware

## Troubleshooting

### Common Issues

1. **API Key Errors**: Verify your API key is valid and has sufficient credits
2. **Timeout Errors**: Increase `timeout_seconds` for slower connections
3. **Quality Issues**: Adjust `generation_strength` and `generation_steps`
4. **Connection Errors**: Check internet connection for cloud providers

### Logs

Check the photobooth logs for detailed error messages:
```
tail -f photobooth.log | grep "filter_openai"
```

## Development

### Testing

Run the plugin tests:
```bash
pytest src/tests/tests/plugins/test_filter_openai.py -v
```

### Adding New Styles

1. Add new style to `style_prompts` in `config.py`
2. Add corresponding prompt to `style_prompts` configuration
3. Update user documentation

## Dependencies

- `openai`: OpenAI API client
- `requests`: HTTP requests for API calls
- `Pillow`: Image processing
- `base64`: Image encoding for API transmission

## License

Same as photobooth-app (MIT License)