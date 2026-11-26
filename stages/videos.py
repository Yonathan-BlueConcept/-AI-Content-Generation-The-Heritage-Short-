
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from providers.video_api import generate_video_from_image
from pipeline.validate import (
    validate_storyboard,
    validate_production_readiness,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

KEYFRAME_DIR = PROJECT_ROOT / "assets" / "keyframes"
OUTPUT_DIR = PROJECT_ROOT / "assets" / "videos"

MANIFEST_PATH = OUTPUT_DIR / ".manifest.json"
RUNS_LOG_PATH = PROJECT_ROOT / "runs.jsonl"


def file_hash(path: Path) -> str:
    """Calculate a SHA-256 fingerprint of an input image."""

    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {}

    with MANIFEST_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_manifest(manifest: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with MANIFEST_PATH.open("w", encoding="utf-8") as file:
        json.dump(manifest, file, indent=2)


def log_model_call(record: dict) -> None:
    with RUNS_LOG_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def create_fingerprint(
    image_path: Path,
    model: str,
    duration: int,
) -> str:
    inputs = {
        "image_sha256": file_hash(image_path),
        "model": model,
        "duration_sec": duration,
    }

    content = json.dumps(inputs, sort_keys=True)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def generate_videos(
    storyboard: dict,
    force: bool = False,
) -> None:

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()

    production = storyboard["production"]
    model = production["video_model"]
    max_duration = production["max_clip_duration_sec"]

    generated = 0
    skipped = 0
    failed = []

    for shot in storyboard["shots"]:

        if not shot["generation"]["video"]:
            print(f"Skipping {shot['id']}: video generation disabled.")
            skipped += 1
            continue

        shot_id = shot["id"]
        duration = shot["duration_sec"]

        if duration > max_duration:
            failed.append(
                f"{shot_id}: duration {duration}s exceeds the "
                f"API's {max_duration}s clip limit."
            )
            print(f"Cannot process {shot_id}: clip is too long.")
            continue

        image_path = KEYFRAME_DIR / f"{shot_id}.png"
        output_path = OUTPUT_DIR / f"{shot_id}.mp4"

        if not image_path.exists():
            failed.append(f"{shot_id}: keyframe not found: {image_path}")
            print(f"Missing keyframe: {image_path}")
            continue

        fingerprint = create_fingerprint(
            image_path=image_path,
            model=model,
            duration=duration,
        )

        cached = (
            output_path.exists()
            and manifest.get(shot_id, {}).get("fingerprint")
            == fingerprint
        )

        if cached and not force:
            print(f"Skipping {shot_id}: cached video exists.")
            skipped += 1
            continue

        print(f"\nGenerating video: {shot_id}")

        started_at = time.perf_counter()
        started_timestamp = datetime.now(timezone.utc).isoformat()
        job_id = None

        try:
            job_id, result = generate_video_from_image(
                image_path=image_path,
                output_path=output_path,
            )

            latency = round(time.perf_counter() - started_at, 2)

            log_model_call({
                "timestamp": started_timestamp,
                "stage": "videos",
                "shot_id": shot_id,
                "model": model,
                "job_id": job_id,
                "parameters": {
                    "input_image": str(
                        image_path.relative_to(PROJECT_ROOT)
                    ),
                    "duration_sec": duration,
                },
                "seed": None,
                "latency_sec": latency,
                "cost": None,
                "status": "success",
                "output": str(result.relative_to(PROJECT_ROOT)),
            })

            manifest[shot_id] = {
                "fingerprint": fingerprint,
                "output": str(result.relative_to(PROJECT_ROOT)),
                "job_id": job_id,
            }

            save_manifest(manifest)

            print(f"Generated: {result}")
            print(f"Job ID: {job_id}")
            print(f"Generation time: {latency}s")

            generated += 1

        except Exception as exc:

            latency = round(time.perf_counter() - started_at, 2)

            log_model_call({
                "timestamp": started_timestamp,
                "stage": "videos",
                "shot_id": shot_id,
                "model": model,
                "job_id": job_id,
                "parameters": {
                    "input_image": str(
                        image_path.relative_to(PROJECT_ROOT)
                    ),
                    "duration_sec": duration,
                },
                "seed": None,
                "latency_sec": latency,
                "cost": None,
                "status": "failed",
                "error": str(exc),
            })

            failed.append(f"{shot_id}: {exc}")
            print(f"Failed {shot_id}: {exc}")

    print("\nVideo stage finished.")
    print(f"Generated: {generated}")
    print(f"Skipped: {skipped}")
    print(f"Failed: {len(failed)}")

    if failed:
        raise RuntimeError(
            "Some videos could not be generated:\n"
            + "\n".join(f"- {error}" for error in failed)
        )


if __name__ == "__main__":

    storyboard = validate_storyboard()
    validate_production_readiness(storyboard)

    generate_videos(storyboard)
