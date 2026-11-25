
import requests
import time

# Cloudflare Tunnel URL
BASE_URL = "https://risks-climbing-moderators-popularity.trycloudflare.com"

# Input and output files
IMAGE_PATH = "test.jpg"
OUTPUT_PATH = "generated_video.mp4"

# Polling interval
POLL_INTERVAL = 5


def generate_video():
    print("Uploading image and submitting generation job...")

    with open(IMAGE_PATH, "rb") as image:
        response = requests.post(
            f"{BASE_URL}/generate",
            files={"file": ("test.jpg", image, "image/jpeg")},
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


def download_video(video_url):
    print("\nDownloading generated MP4...")

    response = requests.get(
        f"{BASE_URL}{video_url}",
        timeout=120
    )

    response.raise_for_status()

    with open(OUTPUT_PATH, "wb") as video:
        video.write(response.content)

    print("\nVideo successfully downloaded!")
    print(f"Saved to: {OUTPUT_PATH}")
    print(f"File size: {len(response.content):,} bytes")


def main():
    try:
        job_id = generate_video()
        job = wait_for_completion(job_id)
        download_video(job["video_url"])

    except requests.exceptions.RequestException as e:
        print(f"\nAPI request failed: {e}")

    except Exception as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()
