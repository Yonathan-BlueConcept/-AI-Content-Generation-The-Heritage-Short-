
import os
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

BASE_URL = os.getenv("VIDEO_API_BASE_URL", "").rstrip("/")
POLL_INTERVAL = 5
JOB_TIMEOUT_SECONDS = 1800


def get_base_url() -> str:
    if not BASE_URL:
        raise ValueError(
            "VIDEO_API_BASE_URL is missing from your .env file."
        )
    return BASE_URL


def generate_video(image_path: Path) -> str:
    """Upload one keyframe and submit a video-generation job."""

    mime_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }

    image_path = Path(image_path)
    mime_type = mime_types.get(image_path.suffix.lower())

    if not mime_type:
        raise ValueError(f"Unsupported image format: {image_path.suffix}")

    with image_path.open("rb") as image:
        response = requests.post(
            f"{get_base_url()}/generate",
            files={
                "file": (image_path.name, image, mime_type)
            },
            timeout=60,
        )

    response.raise_for_status()
    result = response.json()

    job_id = result.get("job_id")
    if not job_id:
        raise RuntimeError(f"API did not return a job_id: {result}")

    return job_id


def wait_for_completion(job_id: str) -> dict:
    """Poll a submitted job until completion or failure."""

    deadline = time.monotonic() + JOB_TIMEOUT_SECONDS
    consecutive_errors = 0

    while time.monotonic() < deadline:

        try:
            response = requests.get(
                f"{get_base_url()}/jobs/{job_id}",
                timeout=30,
            )
            response.raise_for_status()
            job = response.json()
            consecutive_errors = 0

        except requests.RequestException:
            consecutive_errors += 1

            if consecutive_errors >= 5:
                raise RuntimeError(
                    f"Could not check job {job_id} after "
                    f"{consecutive_errors} consecutive errors."
                )

            time.sleep(POLL_INTERVAL)
            continue

        status = job.get("status")

        if status == "completed":
            if not job.get("video_url"):
                raise RuntimeError(
                    f"Completed job {job_id} has no video_url."
                )
            return job

        if status == "failed":
            raise RuntimeError(
                job.get("error", f"Video generation failed: {job_id}")
            )

        if status not in ("queued", "processing"):
            raise RuntimeError(
                f"Unexpected status for job {job_id}: {status}"
            )

        time.sleep(POLL_INTERVAL)

    raise TimeoutError(
        f"Video generation timed out after "
        f"{JOB_TIMEOUT_SECONDS} seconds. Job ID: {job_id}"
    )


def download_video(video_url: str, output_path: Path) -> Path:
    """Download the completed MP4."""

    url = urljoin(f"{get_base_url()}/", video_url)

    response = requests.get(url, timeout=120)
    response.raise_for_status()

    if not response.content:
        raise RuntimeError("The video API returned an empty file.")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(response.content)

    return output_path


def generate_video_from_image(
    image_path: Path,
    output_path: Path,
) -> tuple[str, Path]:
    """Submit, wait for, and download one video."""

    job_id = generate_video(image_path)
    job = wait_for_completion(job_id)
    output = download_video(job["video_url"], output_path)

    return job_id, output
