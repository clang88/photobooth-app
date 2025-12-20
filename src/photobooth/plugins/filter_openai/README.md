# OpenAI Image Generation Filter Plugin

This plugin adds AI-powered image filters to the photobooth application using OpenAI's image generation models, allowing users to apply various artistic styles and enhancements to their photos.

## Features

- **OpenAI Integration**: Uses OpenAI's GPT-Image models for image generation and editing
- **Multiple Models**: Support for gpt-image-1, gpt-image-1-mini, and gpt-image-1.5 (I couldn't get DALL-E2 to work correctly, but I'm leaving it in as a selectable model)
- **Custom style prompts**: The default prompts can be changed or new prompts added by the user.
- **Configurable Parameters**: Adjustable image quality, size, and generation parameters
- **Caching**: Optional result caching to avoid regenerating identical images (useful for switching between styles)
- **Fallback Support**: Option to return original image if AI generation fails

## Missing features
- **Preview Mode**: Currently just returns original image for quick previews, perhaps adding the option to define a "sample" image that is presented as an example for the prompt might be a good workaround; unsure if this can be done via plugins...

## Configuration

### Basic Settings

- `add_userselectable_filter`: Enable/disable user-selectable AI filters in the UI
- `enable_fallback_on_error`: Return original image if AI generation fails
- `cache_results`: Cache generated images to avoid repeated processing

### OpenAI Settings

- `openai_api_key`: Your OpenAI API key (required)
- `openai_model`: Model to use:
  - `gpt-image-1`: Large and quite capable image model
  - `gpt-image-1-mini`: Faster and more cost-effective option
  - `gpt-image-1.5`: Enhanced version of gpt-image-1, slightly faster with better quality
  - `dall-e-2`: ⚠️ **Not recommended** - Did not work correctly in my testing
- `timeout_seconds`: API timeout in seconds (5-300)

### Image Generation Parameters

- `image_quality`: Quality setting (auto, high, medium, low)
- `image_size`: Output size (auto, 1024x1024, 1536x1024, 1024x1536)
- `input_fidelity`: How closely to match input image (high, low)
- `output_format`: Image format (png, jpeg, webp)
- `output_compression`: Compression level for JPEG/WebP (0-100)

## Available Filter Types

1. **cartoon**: Disney-like cartoon style with animated, colorful illustration
2. **sketch**: Pencil sketch black and white drawing, artistic sketch
3. **watercolor**: Soft watercolor painting with brush strokes
4. **oil_painting**: Classical art style with rich textures
5. **vintage**: Vintage photography with sepia tones and retro aesthetic
6. **cyberpunk**: Futuristic style with neon lights and sci-fi aesthetic
7. **fantasy**: Magical and mystical atmosphere
8. **anime**: Studio Ghibli style with vibrant colors and hand-drawn aesthetic

Each filter can be customized by modifying the `style_prompts` in the configuration.

## Setup Instructions

### 1. OpenAI API Key

1. Visit [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create an account and generate an API key
3. Ensure you have sufficient credits for image generation

### 2. Configuration

1. Open the photobooth admin interface
2. Navigate to Plugin Configuration
3. Select "OpenAI Filter Plugin"
4. Enter your OpenAI API key
5. Select your preferred model (recommend gpt-image-1-mini for cost-effectiveness)
6. Adjust generation parameters as needed
7. Customize style prompts if desired

## Usage

Once configured, OpenAI filters will appear in the photobooth filter selection alongside other filters like Pilgram2. Users can:

1. Take a photo
2. Select an AI filter from the available options
3. The AI will process the image (this takes 10-30 seconds)
4. View and save the AI-generated result

**Note**: Preview mode currently returns the original image for performance reasons.

## Performance Considerations

- **Internet Required**: Requires stable internet connection to reach OpenAI's API
- **Processing Time**: AI generation typically takes 10-30 seconds depending on model and parameters
- **API Costs**: Usage incurs costs based on OpenAI's pricing (gpt-image-1-mini is most cost-effective)
- **Caching**: Enable caching to avoid regenerating identical images and save on costs
- **Model Selection**: gpt-image-1-mini offers good balance of speed and cost vs quality

## Troubleshooting

### Common Issues

1. **API Key Errors**: 
   - Verify your OpenAI API key is valid and active
   - Check that you have sufficient credits in your OpenAI account
   - Ensure the API key has permissions for image generation

2. **DALL-E 2 Issues**: 
   - ⚠️ **Known Issue**: DALL-E 2 has compatibility problems and may not work correctly; for some reason edits are not properly applied.
   - **Recommendation**: Use gpt-image-1, gpt-image-1-mini, or ideally gpt-image-1.5 instead

3. **Timeout Errors**: 
   - Increase `timeout_seconds` for bigger/slower models and slower connections
   - Try switching to gpt-image-1-mini for faster processing

4. **Image Format Errors**: 
   - Images are automatically converted to RGB/RGBA format for OpenAI compatibility
   - If issues persist it might be because of the image size, please contact the plugin maintainer with sample images

5. **Generation Quality**: 
   - Adjust `image_quality` and `input_fidelity` settings for faster generation
   - Customize `style_prompts` to create your own filters!

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

1. Modify the `style_prompts` list in the plugin configuration
2. Add a new `StylePrompt` with your desired `style_name` and `prompt`
3. The new style will automatically appear in the available filters

### Custom Prompts

Each style uses a text prompt to guide the AI generation. You can customize these prompts to achieve different artistic effects.

## Dependencies

- `niquests`: HTTP requests for OpenAI API calls (uses niquests instead of requests for better HTTP/2 support)
- `Pillow`: Image processing
- `base64`: Image encoding for API transmission

## License

Same as photobooth-app (MIT License)