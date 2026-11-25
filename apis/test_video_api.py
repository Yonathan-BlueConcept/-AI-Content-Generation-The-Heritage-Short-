
import requests
import time
from pathlib import Path

# Configuration
BASE_URL = "https://taught-balance-dreams-chorus.trycloudflare.com"

INPUT_DIR = Path("input_images")
OUTPUT_DIR = Path("output_videos")

POLL_INTERVAL = 5

# Supported image formats
SUPPORTED_FORMATS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp"
}


def generate_video(image_path):
    print(f"\nUploading image: {image_path.name}")

    # Determine MIME type
    mime_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp"
    }

    mime_type = mime_types[image_path.suffix.lower()]

    with image_path.open("rb") as image:
        response = requests.post(
            f"{BASE_URL}/generate",
            files={
                "file": (
                    image_path.name,
                    image,
                    mime_type
                )
            },
            timeout=60
        )

    response.raise_for_status()
    result = response.json()

    job_id = result["job_id"]

    print(f"Job submitted: {job_id}")
    print(f"Initial status: {result['status']}")

    return job_id


def wait_for_completion(job_id):
    print("\nWaiting for video generation...")

    while True:
        response = requests.get(
            f"{BASE_URL}/jobs/{job_id}",
            timeout=30
        )

        response.raise_for_status()
        job = response.json()

        status = job["status"]
        print(f"Generation status: {status}")

        if status == "completed":
            print("Video generation completed!")
            return job

        if status == "failed":
            raise RuntimeError(
                job.get("error", "Unknown generation error")
            )

        if status not in ("queued", "processing"):
            raise RuntimeError(f"Unexpected job status: {status}")

        time.sleep(POLL_INTERVAL)


def download_video(video_url, output_path):
    print("\nDownloading generated MP4...")

    response = requests.get(
        f"{BASE_URL}{video_url}",
        timeout=120
    )

    response.raise_for_status()

    output_path.write_bytes(response.content)

    print(f"Video saved: {output_path}")
    print(f"File size: {len(response.content):,} bytes")


def process_image(image_path):
    output_path = OUTPUT_DIR / f"{image_path.stem}.mp4"

    print("\n" + "=" * 50)
    print(f"Processing: {image_path.name}")
    print("=" * 50)

    job_id = generate_video(image_path)

    job = wait_for_completion(job_id)

    download_video(job["video_url"], output_path)


def main():
    # Create directories if they don't exist
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Discover supported images
    images = sorted(
        file for file in INPUT_DIR.iterdir()
        if file.is_file()
        and file.suffix.lower() in SUPPORTED_FORMATS
    )

    if not images:
        print("No supported images found in input_images/")
        return

    print(f"Found {len(images)} images.")

    successful = 0
    failed = 0

    # Process images sequentially
    for index, image_path in enumerate(images, start=1):
        print(f"\nImage {index}/{len(images)}")

        try:
            process_image(image_path)
            successful += 1

        except Exception as e:
            failed += 1
            print(f"Failed to process {image_path.name}: {e}")

    print("\n" + "=" * 50)
    print("PROCESSING SUMMARY")
    print("=" * 50)
    print(f"Total images: {len(images)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Videos saved in: {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
