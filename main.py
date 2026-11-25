# import httpx
# from fastapi import FastAPI, HTTPException

# app = FastAPI()


# @app.get("/")
# def read_root():
#     return {"status": "ok", "message": "FastAPI is running"}


# @app.get("/test-api")
# async def test_external_api():
#     url = "https://httpbin.org/get"
#     async with httpx.AsyncClient(timeout=10.0) as client:
#         try:
#             response = await client.get(url)
#             response.raise_for_status()
#             return {"status": "success", "data": response.json()}
#         except httpx.HTTPError as exc:
#             raise HTTPException(status_code=502, detail=f"External API error: {exc}")



import os
import base64
from pathlib import Path

import requests
from dotenv import load_dotenv


# Load credentials
load_dotenv()

ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")

if not ACCOUNT_ID or not API_TOKEN:
    raise ValueError(
        "Missing Cloudflare credentials. Check your .env file."
    )


# Cloudflare FLUX.2 Klein 4B endpoint
MODEL = "@cf/black-forest-labs/flux-2-klein-4b"

API_URL = (
    f"https://api.cloudflare.com/client/v4/accounts/"
    f"{ACCOUNT_ID}/ai/run/{MODEL}"
)


# Test prompt
PROMPT = """
Photorealistic cinematic documentary reconstruction of a rural Ethiopian village in an earlier period, before household water connections became widespread.

A dry residential village with modest concrete-block houses, corrugated iron roofs, dusty unpaved paths, and simple outdoor spaces between homes. The houses are relatively close together, creating a lived-in village environment. The landscape is dry, with sparse vegetation and muted earthy colors.

The village feels authentic and historically plausible. It is a peaceful everyday residential environment, not an abandoned settlement and not an exaggerated depiction of poverty.

Wide cinematic establishing shot, natural warm daylight, realistic architecture and materials, subtle documentary film color grading, professional cinematography, photorealistic, 16:9 landscape composition.

No modern apartment buildings, no paved urban roads, no luxury houses, no lush tropical vegetation, no text, no logos, no watermark.
"""


def generate_image(prompt: str, output_path: str = "generated_image2.png"):

    headers = {
        "Authorization": f"Bearer {API_TOKEN}"
    }

    # FLUX.2 Klein requires multipart form data.
    # requests automatically generates the multipart boundary.
    files = {
        "prompt": (None, prompt),
        "width": (None, "1024"),
        "height": (None, "1024"),
    }

    print("Sending request to Cloudflare...")
    print("Model:", MODEL)

    response = requests.post(
        API_URL,
        headers=headers,
        files=files,
        timeout=300,
    )

    if not response.ok:
        print("API request failed:")
        print(response.status_code)
        print(response.text[:3000])
        response.raise_for_status()

    content_type = response.headers.get("content-type", "")

    # Handle a direct image response.
    if "image/" in content_type:
        image_bytes = response.content

    # Handle a JSON response containing a base64 image.
    elif "application/json" in content_type:
        data = response.json()

        if not data.get("success", True):
            raise RuntimeError(f"Cloudflare error: {data}")

        result = data.get("result", {})
        encoded_image = result.get("image")

        if not encoded_image:
            raise RuntimeError(
                f"No image found in API response: {data}"
            )

        image_bytes = base64.b64decode(encoded_image)

    else:
        raise RuntimeError(
            f"Unexpected response type: {content_type}\n"
            f"{response.text[:2000]}"
        )

    # Save generated image
    output = Path(output_path)
    output.write_bytes(image_bytes)

    print("\nImage generated successfully!")
    print("Saved to:", output.resolve())
    print("File size:", round(len(image_bytes) / 1024, 2), "KB")

    return output


if __name__ == "__main__":
    generate_image(PROMPT)
