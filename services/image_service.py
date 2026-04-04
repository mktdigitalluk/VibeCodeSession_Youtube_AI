from pathlib import Path
import logging
import os
import replicate
from PIL import Image

logger = logging.getLogger(__name__)


def generate_thumbnail(prompt: str, output_path: Path, title: str) -> Path:
    """
    Generate a thumbnail using Replicate Flux (black-forest-labs/flux-dev).
    Requires REPLICATE_API_TOKEN in environment or keys.env.

    Returns the path to a JPEG file — YouTube requires JPEG or PNG for thumbnails.
    The original WebP from Replicate is also saved alongside as .webp for reference.
    """

    token = os.getenv("REPLICATE_API_TOKEN")
    if not token:
        raise RuntimeError(
            "REPLICATE_API_TOKEN not set in environment or keys.env. "
            "Add it to keys.env: REPLICATE_API_TOKEN=r8_..."
        )

    os.environ["REPLICATE_API_TOKEN"] = token

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # We always store the raw WebP from Replicate, then convert to JPEG for YouTube.
    webp_path = output_path.with_suffix(".webp")
    jpeg_path = output_path.with_suffix(".jpg")

    short_prompt = (
        f"software developer coding on laptop, "
        f"code visible on screen, "
        f"cinematic lighting, "
        f"beautiful environment, "
        f"{prompt}, "
        f"high quality digital illustration, "
        f"no text"
    )

    logger.info("Submitting thumbnail to Replicate Flux | model=black-forest-labs/flux-dev")
    logger.debug("Thumbnail full prompt: %s", short_prompt)

    try:
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
                "num_inference_steps": 28,
            },
        )
    except Exception as exc:
        logger.error("Replicate API call failed: %s", exc)
        raise

    if not output or len(output) == 0:
        raise RuntimeError("Replicate returned an empty output list — no image generated.")

    image_obj = output[0]

    logger.info("Replicate responded, writing WebP to disk: %s", webp_path)
    try:
        with open(webp_path, "wb") as f:
            f.write(image_obj.read())
    except Exception as exc:
        logger.error("Failed to write WebP thumbnail to disk: %s", exc)
        raise

    webp_size_kb = webp_path.stat().st_size / 1024
    logger.info("WebP thumbnail saved | path=%s | size_kb=%.1f", webp_path, webp_size_kb)

    if webp_size_kb < 1:
        raise RuntimeError(
            f"WebP thumbnail is suspiciously small ({webp_size_kb:.1f} KB). "
            "Replicate may have returned an empty or invalid image."
        )

    # Convert WebP → JPEG for YouTube compatibility
    # YouTube thumbnail endpoint rejects WebP (HTTP 400 badRequest).
    logger.info("Converting WebP → JPEG for YouTube compatibility: %s", jpeg_path)
    try:
        img = Image.open(webp_path).convert("RGB")
        img.save(jpeg_path, "JPEG", quality=92)
    except Exception as exc:
        logger.error("Failed to convert thumbnail to JPEG: %s", exc)
        raise

    jpeg_size_kb = jpeg_path.stat().st_size / 1024
    logger.info("JPEG thumbnail saved | path=%s | size_kb=%.1f", jpeg_path, jpeg_size_kb)

    # Return the JPEG path — this is what main.py and youtube_service will use
    return jpeg_path
