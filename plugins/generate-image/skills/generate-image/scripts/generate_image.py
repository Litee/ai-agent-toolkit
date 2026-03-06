#!/usr/bin/env python3
"""
Image Generation Script using AWS Bedrock Nova Canvas Model

This script generates images using Amazon Nova Canvas model hosted on AWS Bedrock.
It supports both basic text-to-image generation and color-guided generation.
"""

import argparse
import base64
import json
import os
import sys
from datetime import datetime
from typing import List, Optional

import boto3


class NovaCanvasGenerator:
    """Generator class for AWS Bedrock Nova Canvas model."""

    # Model ID for Nova Canvas on Bedrock
    MODEL_ID = "amazon.nova-canvas-v1:0"

    def __init__(self, region: str = "us-east-1", profile_name: Optional[str] = None):
        """
        Initialize the generator with AWS Bedrock client.

        Args:
            region: AWS region where Bedrock is available
            profile_name: AWS profile name to use (optional)
        """
        # Create session with profile if specified
        if profile_name:
            session = boto3.Session(profile_name=profile_name)
            self.bedrock = session.client(
                service_name='bedrock-runtime',
                region_name=region
            )
        else:
            self.bedrock = boto3.client(
                service_name='bedrock-runtime',
                region_name=region
            )

    def generate_image(
        self,
        prompt: str,
        output_dir: str,
        colors: Optional[List[str]] = None,
        negative_prompt: Optional[str] = None,
        filename: Optional[str] = None,
        width: int = 1024,
        height: int = 1024,
        quality: str = "standard",
        cfg_scale: float = 7.0,
        seed: Optional[int] = None,
        number_of_images: int = 1
    ) -> List[str]:
        """
        Generate images using text prompt with optional color guidance.

        Args:
            prompt: Text description of the image (1-1024 characters)
            output_dir: Directory to save generated images (required)
            colors: Optional list of up to 10 hexadecimal color values (e.g., "#FF9800").
                   If provided, uses COLOR_GUIDED_GENERATION task type.
                   If None, uses TEXT_IMAGE task type.
            negative_prompt: Text to define what not to include (1-1024 characters)
            filename: Base name for saved files (without extension)
            width: Image width (320-4096, divisible by 16)
            height: Image height (320-4096, divisible by 16)
            quality: Image quality ("standard" or "premium")
            cfg_scale: How strongly the image adheres to prompt (1.1-10.0)
            seed: Seed for generation (0-858993459)
            number_of_images: Number of images to generate (1-5)

        Returns:
            List of file paths to generated images
        """
        # Validate parameters
        self._validate_params(prompt, negative_prompt, width, height,
                            quality, cfg_scale, seed, number_of_images)

        # Validate colors if provided
        if colors is not None and (len(colors) == 0 or len(colors) > 10):
            raise ValueError("colors must contain between 1 and 10 color values")

        # Determine task type based on whether colors are provided
        use_colors = colors is not None

        # Prepare request body
        body = {
            "taskType": "COLOR_GUIDED_GENERATION" if use_colors else "TEXT_IMAGE",
            "imageGenerationConfig": {
                "numberOfImages": number_of_images,
                "quality": quality,
                "width": width,
                "height": height,
                "cfgScale": cfg_scale
            }
        }

        # Add task-specific parameters
        if use_colors:
            body["colorGuidedGenerationParams"] = {
                "text": prompt,
                "colors": colors
            }
            if negative_prompt:
                body["colorGuidedGenerationParams"]["negativeText"] = negative_prompt
        else:
            body["textToImageParams"] = {
                "text": prompt
            }
            if negative_prompt:
                body["textToImageParams"]["negativeText"] = negative_prompt

        if seed is not None:
            body["imageGenerationConfig"]["seed"] = seed

        # Call Bedrock
        response = self.bedrock.invoke_model(
            modelId=self.MODEL_ID,
            body=json.dumps(body)
        )

        # Parse response and save images
        response_body = json.loads(response['body'].read())
        return self._save_images(response_body, filename, output_dir)

    def _validate_params(
        self,
        prompt: str,
        negative_prompt: Optional[str],
        width: int,
        height: int,
        quality: str,
        cfg_scale: float,
        seed: Optional[int],
        number_of_images: int
    ):
        """Validate generation parameters."""
        if not prompt or len(prompt) < 1 or len(prompt) > 1024:
            raise ValueError("prompt must be between 1 and 1024 characters")

        if negative_prompt and (len(negative_prompt) < 1 or len(negative_prompt) > 1024):
            raise ValueError("negative_prompt must be between 1 and 1024 characters")

        if width < 320 or width > 4096 or width % 16 != 0:
            raise ValueError("width must be between 320 and 4096 and divisible by 16")

        if height < 320 or height > 4096 or height % 16 != 0:
            raise ValueError("height must be between 320 and 4096 and divisible by 16")

        if quality not in ["standard", "premium"]:
            raise ValueError("quality must be either 'standard' or 'premium'")

        if cfg_scale < 1.1 or cfg_scale > 10.0:
            raise ValueError("cfg_scale must be between 1.1 and 10.0")

        if seed is not None and (seed < 0 or seed > 858993459):
            raise ValueError("seed must be between 0 and 858993459")

        if number_of_images < 1 or number_of_images > 5:
            raise ValueError("number_of_images must be between 1 and 5")

    def _save_images(
        self,
        response_body: dict,
        filename: Optional[str],
        output_dir: str
    ) -> List[str]:
        """Save generated images to files."""
        os.makedirs(output_dir, exist_ok=True)

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"nova_canvas_{timestamp}"

        saved_files = []
        images = response_body.get('images', [])

        for i, image_base64 in enumerate(images):
            if len(images) > 1:
                output_path = os.path.join(output_dir, f"{filename}_{i+1}.png")
            else:
                output_path = os.path.join(output_dir, f"{filename}.png")

            # Decode and save image
            image_data = base64.b64decode(image_base64)
            with open(output_path, 'wb') as f:
                f.write(image_data)

            saved_files.append(output_path)
            print(f"Saved image to: {output_path}")

        return saved_files


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Generate images using AWS Bedrock Nova Canvas model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic text-to-image generation
  %(prog)s "a serene landscape with mountains and lake" --output-dir ./my_images

  # With negative prompt
  %(prog)s "portrait of a woman" --output-dir ./my_images --negative-prompt "people, anatomy, hands"

  # Custom size and quality
  %(prog)s "futuristic city" --output-dir ./my_images --width 1280 --height 720 --quality premium

  # Color-guided generation
  %(prog)s "abstract art" --output-dir ./my_images --colors "#FF5733" "#33FF57" "#3357FF"

  # Generate multiple images
  %(prog)s "cat playing" --output-dir ./my_images --number-of-images 3
        """
    )

    # Required arguments
    parser.add_argument(
        "prompt",
        help="Text description of the image to generate (1-1024 characters)"
    )

    # Optional arguments
    parser.add_argument(
        "--negative-prompt",
        help="Text to define what not to include in the image (recommended: 'people, anatomy, hands, low quality, low resolution, low detail')"
    )

    parser.add_argument(
        "--colors",
        nargs="+",
        help="List of hexadecimal color values for color-guided generation (e.g., '#FF9800' '#33FF57')"
    )

    parser.add_argument(
        "--filename",
        help="Base name for saved files (without extension)"
    )

    parser.add_argument(
        "--width",
        type=int,
        default=1024,
        help="Image width in pixels (320-4096, divisible by 16, default: 1024)"
    )

    parser.add_argument(
        "--height",
        type=int,
        default=1024,
        help="Image height in pixels (320-4096, divisible by 16, default: 1024)"
    )

    parser.add_argument(
        "--quality",
        choices=["standard", "premium"],
        default="standard",
        help="Image quality (default: standard)"
    )

    parser.add_argument(
        "--cfg-scale",
        type=float,
        default=7.0,
        help="How strongly the image adheres to the prompt (1.1-10.0, default: 7.0)"
    )

    parser.add_argument(
        "--seed",
        type=int,
        help="Seed for generation (0-858993459) for reproducible results"
    )

    parser.add_argument(
        "--number-of-images",
        type=int,
        default=1,
        help="Number of images to generate (1-5, default: 1)"
    )

    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory to save generated images (required)"
    )

    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region for Bedrock (default: us-east-1)"
    )

    parser.add_argument(
        "--aws-profile",
        default=None,
        help="AWS profile name to use (default: use default credential chain)"
    )

    args = parser.parse_args()

    try:
        # Initialize generator
        generator = NovaCanvasGenerator(region=args.region, profile_name=args.aws_profile)

        # Generate images
        if args.colors:
            print(f"Generating {args.number_of_images} image(s) with color guidance...")
        else:
            print(f"Generating {args.number_of_images} image(s)...")

        saved_files = generator.generate_image(
            prompt=args.prompt,
            output_dir=args.output_dir,
            colors=args.colors,
            negative_prompt=args.negative_prompt,
            filename=args.filename,
            width=args.width,
            height=args.height,
            quality=args.quality,
            cfg_scale=args.cfg_scale,
            seed=args.seed,
            number_of_images=args.number_of_images
        )

        print(f"\nSuccessfully generated {len(saved_files)} image(s)!")
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
