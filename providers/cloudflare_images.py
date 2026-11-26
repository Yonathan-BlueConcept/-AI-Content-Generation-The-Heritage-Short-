
import base64
import os
from pathlib import Path

import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

MODEL = "@cf/black-forest-labs/flux-2-klein-4b"


def generate_image(
    prompt: str,
    output_path: str | Path,
    width: int = 1024,
    height: int = 576,
) -> Path:
    """
    Generate an image using Cloudflare FLUX.2 Klein 4B.

    Args:
        prompt: Image-generation prompt.
        output_path: Where the generated image will be saved.
        width: Output image width.
        height: Output image height.

    Returns:
        Path to the saved image.
    """

    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    api_token = os.getenv("CLOUDFLARE_API_TOKEN")

    if not account_id or not api_token:
        raise ValueError(
            "Missing Cloudflare credentials. Check your .env file."
        )

    api_url = (
        "https://api.cloudflare.com/client/v4/accounts/"
        f"{account_id}/ai/run/{MODEL}"
    )

    headers = {
        "Authorization": f"Bearer {api_token}"
    }

    files = {
        "prompt": (None, prompt),
        "width": (None, str(width)),
        "height": (None, str(height)),
    }

    response = requests.post(
        api_url,
        headers=headers,
        files=files,
        timeout=300,
    )

    if not response.ok:
        raise RuntimeError(
            f"Cloudflare API error ({response.status_code}): "
            f"{response.text[:2000]}"
        )

    content_type = response.headers.get("content-type", "")

    if "image/" in content_type:
        image_bytes = response.content

    elif "application/json" in content_type:
        data = response.json()

        if not data.get("success", True):
            raise RuntimeError(f"Cloudflare generation failed: {data}")

        encoded_image = data.get("result", {}).get("image")

        if not encoded_image:
            raise RuntimeError(
                f"No image found in Cloudflare response: {data}"
            )

        image_bytes = base64.b64decode(encoded_image)

    else:
        raise RuntimeError(
            f"Unexpected response content type: {content_type}"
        )

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(image_bytes)

    return output
