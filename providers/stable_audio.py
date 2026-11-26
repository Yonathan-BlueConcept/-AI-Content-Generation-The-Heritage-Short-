
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

BASE_URL = "https://api.stability.ai"
MODEL = "stable-audio-3"

SUBMIT_URL = (
    f"{BASE_URL}/v2beta/audio/stable-audio/text-to-audio"
)
RESULT_URL = f"{BASE_URL}/v2beta/audio/results"

POLL_INTERVAL_SECONDS = 10
JOB_TIMEOUT_SECONDS = 1800


def get_api_key() -> str:
    api_key = os.getenv("STABILITY_API_KEY")

    if not api_key:
        raise ValueError(
            "STABILITY_API_KEY is missing from your .env file."
        )

    return api_key


def generate_music(
    prompt: str,
    duration: int,
    output_path: Path,
    seed: int = 0,
) -> dict:
    if not prompt.strip():
        raise ValueError("Music prompt cannot be empty.")

    if not 1 <= duration <= 380:
        raise ValueError(
            "Duration must be between 1 and 380 seconds."
        )

    api_key = get_api_key()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    data = {
        "model": MODEL,
        "prompt": prompt,
        "duration": duration,
        "seed": seed,
        "steps": 8,
        "output_format": "wav",
    }

    print("Submitting Stable Audio generation request...")

    response = requests.post(
        SUBMIT_URL,
        headers=headers,
        data=data,
        files={"image": None},
        timeout=120,
    )

    if response.status_code != 202:
        raise RuntimeError(
            f"Music submission failed "
            f"({response.status_code}): {response.text}"
        )

    generation_id = response.json().get("id")

    if not generation_id:
        raise RuntimeError(
            f"No generation ID returned: {response.text}"
        )

    print(f"Generation submitted: {generation_id}")

    deadline = time.monotonic() + JOB_TIMEOUT_SECONDS
    consecutive_errors = 0

    while time.monotonic() < deadline:
        try:
            result = requests.get(
                f"{RESULT_URL}/{generation_id}",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Accept": "audio/*",
                },
                timeout=60,
            )

            if result.status_code == 202:
                consecutive_errors = 0
                print("Music is still generating...")
                time.sleep(POLL_INTERVAL_SECONDS)
                continue

            if result.status_code == 200:
                if not result.content:
                    raise RuntimeError(
                        "The API returned an empty audio file."
                    )

                output_path = Path(output_path)
                output_path.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )
                output_path.write_bytes(result.content)

                return {
                    "generation_id": generation_id,
                    "seed": result.headers.get("seed"),
                    "content_type": result.headers.get(
                        "Content-Type"
                    ),
                    "output_path": str(output_path),
                    "size_bytes": len(result.content),
                }

            raise RuntimeError(
                f"Audio retrieval failed "
                f"({result.status_code}): {result.text}"
            )

        except requests.RequestException as exc:
            consecutive_errors += 1

            if consecutive_errors >= 5:
                raise RuntimeError(
                    "Too many consecutive polling errors."
                ) from exc

            print(f"Temporary polling error: {exc}")
            time.sleep(POLL_INTERVAL_SECONDS)

    raise TimeoutError(
        f"Music generation timed out. Job ID: {generation_id}"
    )
