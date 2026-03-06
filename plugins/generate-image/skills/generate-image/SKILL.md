---
name: generate-image
description: Generate images using Amazon Nova Canvas on AWS Bedrock. Use when creating images, AI art, text-to-image generation, or visual content.
---

# Generate Image

Generate images using Amazon Nova Canvas model hosted on AWS Bedrock. This skill supports both basic text-to-image generation and color-guided generation.

## Prerequisites

1. **AWS credentials configured** with access to Bedrock
   - The script uses the default AWS credential chain (environment variables, `~/.aws/credentials`, instance profile, etc.)
   - To use a specific profile, pass `--aws-profile your-profile-name`
2. Access to AWS Bedrock in your AWS account
3. Python 3.6+ installed
4. boto3 library installed: `pip install boto3`

## Script Usage

The `scripts/generate_image.py` script provides a command-line interface to generate images using Nova Canvas.

### Basic Text-to-Image Generation

Generate a simple image from a text prompt:

```bash
python3 scripts/generate_image.py "a serene landscape with mountains and lake" \
  --output-dir ./my_images
```

### Advanced Options

#### Using Negative Prompts

Specify what you don't want in the image (recommended for better quality):

```bash
python3 scripts/generate_image.py "portrait of a woman" \
  --output-dir ./my_images \
  --negative-prompt "people, anatomy, hands, low quality, low resolution, low detail"
```

#### Custom Size and Quality

```bash
python3 scripts/generate_image.py "futuristic city skyline at sunset" \
  --output-dir ./my_images \
  --width 1920 \
  --height 1080 \
  --quality premium
```

#### Color-Guided Generation

Generate images with specific color palettes:

```bash
python3 scripts/generate_image.py "abstract art with flowing shapes" \
  --output-dir ./my_images \
  --colors "#FF5733" "#33FF57" "#3357FF"
```

#### Generate Multiple Images

```bash
python3 scripts/generate_image.py "cat playing with yarn" \
  --output-dir ./my_images \
  --number-of-images 3 \
  --filename cute_cat
```

#### Reproducible Results

Use a seed for consistent generation:

```bash
python3 scripts/generate_image.py "mountain landscape" \
  --output-dir ./my_images \
  --seed 12345
```

#### Custom Output Directory

```bash
python3 scripts/generate_image.py "sunset over ocean" \
  --output-dir ./my_images \
  --filename ocean_sunset
```

#### Using a Specific AWS Profile

```bash
python3 scripts/generate_image.py "mountain vista" \
  --output-dir ./my_images \
  --aws-profile my-custom-profile
```

## Complete Parameter Reference

| Parameter | Description | Default | Valid Range/Values |
|-----------|-------------|---------|-------------------|
| `prompt` | Text description of the image (required) | - | 1-1024 characters |
| `--output-dir` | Directory to save images (required) | - | Any valid path |
| `--negative-prompt` | What to exclude from the image | None | 1-1024 characters |
| `--colors` | Hex color values for color guidance | None | Up to 10 colors (e.g., "#FF9800") |
| `--filename` | Base name for saved files | Auto-generated timestamp | Any valid filename |
| `--width` | Image width in pixels | 1024 | 320-4096 (divisible by 16) |
| `--height` | Image height in pixels | 1024 | 320-4096 (divisible by 16) |
| `--quality` | Image quality | standard | standard, premium |
| `--cfg-scale` | Prompt adherence strength | 7.0 | 1.1-10.0 |
| `--seed` | Random seed for reproducibility | Random | 0-858993459 |
| `--number-of-images` | Number of images to generate | 1 | 1-5 |
| `--region` | AWS region for Bedrock | us-east-1 | Valid AWS region |
| `--aws-profile` | AWS profile name to use | None (default credential chain) | Any configured profile |

## Prompt Best Practices

An effective prompt often includes short descriptions of:

1. **The subject** - What the image is about
2. **The environment** - Where it takes place
3. **(optional) Position or pose** - How subjects are positioned
4. **(optional) Lighting** - Lighting conditions
5. **(optional) Camera position/framing** - Viewpoint
6. **(optional) Visual style** - "photo", "illustration", "painting", etc.

### Important Guidelines

- Do NOT use negation words like "no", "not", "without" in your prompt
- Instead, use the `--negative-prompt` parameter for what you don't want
- Always include "people, anatomy, hands, low quality, low resolution, low detail" in negative prompts for better results

### Example Prompts

```bash
# Realistic photo
python3 scripts/generate_image.py \
  "realistic editorial photo of female teacher standing at a blackboard with a warm smile" \
  --output-dir ./my_images \
  --negative-prompt "people, anatomy, hands, low quality"

# Whimsical illustration
python3 scripts/generate_image.py \
  "whimsical and ethereal soft-shaded story illustration: A woman in a large hat stands at the ship's railing looking out across the ocean" \
  --output-dir ./my_images \
  --quality premium

# Cinematic drone shot
python3 scripts/generate_image.py \
  "drone view of a dark river winding through a stark Iceland landscape, cinematic quality" \
  --output-dir ./my_images \
  --width 1920 \
  --height 1080
```

## Using in Python Code

You can also import and use the generator in your Python code:

```python
from scripts.generate_image import NovaCanvasGenerator

# Initialize generator with default credential chain
generator = NovaCanvasGenerator(region="us-east-1")

# Or use a specific profile
generator = NovaCanvasGenerator(region="us-east-1", profile_name="my-custom-profile")

# Generate a basic image
images = generator.generate_image(
    prompt="a beautiful sunset over the ocean",
    output_dir="./my_images",
    negative_prompt="people, anatomy, hands, low quality",
    width=1024,
    height=1024,
    quality="standard"
)

# Generate with color guidance
images = generator.generate_image(
    prompt="abstract art with geometric shapes",
    output_dir="./my_images",
    colors=["#FF5733", "#33FF57", "#3357FF"],
    width=1024,
    height=1024
)

print(f"Generated images: {images}")
```

## Troubleshooting

### AWS Credentials Error
If you encounter authentication errors:
1. Ensure your AWS credentials are configured with Bedrock access
2. By default, the script uses the standard AWS credential chain (environment variables, `~/.aws/credentials`, instance profile, etc.)
3. To use a specific profile: `--aws-profile your-profile-name`

### Bedrock Access Error
Make sure your AWS account has access to Bedrock and the Nova Canvas model in the specified region.

### Invalid Dimensions
Width and height must be between 320 and 4096 pixels and divisible by 16.

## Example Color Palettes

- Vibrant: `["#FF5733", "#33FF57", "#3357FF"]`
- High contrast: `["#000000", "#FFFFFF"]`
- Gold and bronze: `["#FFD700", "#B87333"]`
- Sunset: `["#FF6B35", "#F7931E", "#FDC830", "#F37335"]`
- Ocean: `["#006994", "#1E90FF", "#87CEEB", "#B0E0E6"]` 