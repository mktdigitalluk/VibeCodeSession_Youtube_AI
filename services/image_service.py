
from pathlib import Path
import logging
import os
import replicate

logger = logging.getLogger(__name__)


def generate_thumbnail(prompt: str, output_path: Path, title: str) -> Path:
    """
    Generate a thumbnail using Replicate Flux (black-forest-labs/flux-dev).
    Requires REPLICATE_API_TOKEN in environment or keys.env.
    """

    token = os.getenv("REPLICATE_API_TOKEN")
    if not token:
        raise RuntimeError("REPLICATE_API_TOKEN not set in environment or keys.env")

    os.environ["REPLICATE_API_TOKEN"] = token

    output_path.parent.mkdir(parents=True, exist_ok=True)

    short_prompt = f"""
software developer coding on laptop,
code visible on screen,
cinematic lighting,
beautiful environment,
{prompt},
high quality digital illustration,
no text
"""

    logger.info("Generating thumbnail with Replicate Flux")

    output = replicate.run(
        "black-forest-labs/flux-dev",
        input={
            "prompt": short_prompt,
            "go_fast": True,
            "guidance": 3.5,
            "megapixels": "1",
            "num_outputs": 1,
            "aspect_ratio": "16:9",
            "output_format": "webp",
            "output_quality": 90,
            "prompt_strength": 0.8,
            "num_inference_steps": 28
        }
    )

    image = output[0]

    with open(output_path, "wb") as f:
        f.write(image.read())

    logger.info("Thumbnail saved to %s", output_path)

    return output_path
