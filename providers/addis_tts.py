
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

BASE_URL = "https://api.addisassistant.com"
VOICE_ID = "am-yohanes-calm"
LANGUAGE = "am"
OUTPUT_FORMAT = "mp3_44100"


def get_headers() -> dict:
    api_key = os.getenv("ADDIS_API_KEY")

    if not api_key:
        raise ValueError("ADDIS_API_KEY is missing from .env")

    return {
        "x-api-key": api_key,
        "Content-Type": "application/json",
    }


def list_amharic_voices() -> list:
    response = requests.get(
        f"{BASE_URL}/api/v1/voice/voices",
        headers={"x-api-key": get_headers()["x-api-key"]},
        params={"language": LANGUAGE},
        timeout=30,
    )
    response.raise_for_status()

    result = response.json()
    voices = result.get("data", result)

    if isinstance(voices, dict):
        voices = voices.get("voices", [])

    return voices


def estimate_speech_cost(text: str) -> dict:
    payload = {
        "text": text,
        "voice_id": VOICE_ID,
        "language": LANGUAGE,
        "output_format": OUTPUT_FORMAT,
    }

    response = requests.post(
        f"{BASE_URL}/api/v1/voice/estimate",
        headers=get_headers(),
        json=payload,
        timeout=30,
    )
    response.raise_for_status()

    return response.json()


def generate_speech(
    text: str,
    output_path: Path,
    client_request_id: str,
) -> dict:
    if not text.strip():
        raise ValueError("Narration text cannot be empty.")

    payload = {
        "text": text,
        "voice_id": VOICE_ID,
        "language": LANGUAGE,
        "output_format": OUTPUT_FORMAT,
        "client_request_id": client_request_id,
    }

    response = requests.post(
        f"{BASE_URL}/api/v1/voice/generations",
        headers=get_headers(),
        json=payload,
        timeout=120,
    )
    response.raise_for_status()

    result = response.json()
    data = result.get("data", result)

    audio_url = data.get("audio_url")

    if not audio_url:
        raise RuntimeError(
            f"Addis AI did not return an audio URL: {result}"
        )

    audio_response = requests.get(
        audio_url,
        timeout=120,
    )
    audio_response.raise_for_status()

    if not audio_response.content:
        raise RuntimeError("Downloaded narration audio is empty.")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(audio_response.content)

    return {
        "clip_id": data.get("id"),
        "request_id": response.headers.get("x-request-id"),
        "client_request_id": client_request_id,
        "output_path": str(output_path),
        "size_bytes": len(audio_response.content),
        "usage": data.get("usage"),
    }
