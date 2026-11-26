
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from providers.cloudflare_images import generate_image
from pipeline.validate import validate_storyboard, validate_production_readiness


PROJECT_ROOT = Path(__file__).resolve().parents[1]

OUTPUT_DIR = PROJECT_ROOT / "assets" / "keyframes"
MANIFEST_PATH = OUTPUT_DIR / ".manifest.json"
RUNS_LOG_PATH = PROJECT_ROOT / "runs.jsonl"

IMAGE_WIDTH = 1024
IMAGE_HEIGHT = 576

MAX_ATTEMPTS = 3


def load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {}

    with MANIFEST_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_manifest(manifest: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with MANIFEST_PATH.open("w", encoding="utf-8") as file:
        json.dump(manifest, file, indent=2)


def create_fingerprint(prompt: str, model: str) -> str:
    """
    Identify the inputs that determine a keyframe.
    Changing the prompt, model, or dimensions invalidates its cache.
    """

    inputs = {
        "prompt": prompt,
        "model": model,
        "width": IMAGE_WIDTH,
        "height": IMAGE_HEIGHT,
    }

    content = json.dumps(inputs, sort_keys=True)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def log_model_call(record: dict) -> None:
    with RUNS_LOG_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def generate_keyframes(
    storyboard: dict,
    force: bool = False,
) -> None:

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()

    production = storyboard["production"]
    model = production["image_model"]

    shots = storyboard["shots"]

    generated = 0
    skipped = 0

    for shot in shots:

        if not shot["generation"]["image"]:
            print(f"Skipping {shot['id']}: image generation disabled.")
            skipped += 1
            continue

        shot_id = shot["id"]
        prompt = shot["visual_prompt"]

        output_path = OUTPUT_DIR / f"{shot_id}.png"

        fingerprint = create_fingerprint(prompt, model)

        cached = (
            output_path.exists()
            and manifest.get(shot_id, {}).get("fingerprint") == fingerprint
        )

        if cached and not force:
            print(f"Skipping {shot_id}: cached keyframe exists.")
            skipped += 1
            continue

        print(f"\nGenerating keyframe: {shot_id}")

        for attempt in range(1, MAX_ATTEMPTS + 1):

            started_at = time.perf_counter()
            started_timestamp = datetime.now(timezone.utc).isoformat()

            try:
                result = generate_image(
                    prompt=prompt,
                    output_path=output_path,
                    width=IMAGE_WIDTH,
                    height=IMAGE_HEIGHT,
                )

                latency = round(time.perf_counter() - started_at, 2)

                log_model_call({
                    "timestamp": started_timestamp,
                    "stage": "keyframes",
                    "shot_id": shot_id,
                    "model": model,
                    "attempt": attempt,
                    "parameters": {
                        "width": IMAGE_WIDTH,
                        "height": IMAGE_HEIGHT,
                    },
                    "seed": None,
                    "latency_sec": latency,
                    "cost": None,
                    "status": "success",
                    "output": str(result.relative_to(PROJECT_ROOT)),
                })

                manifest[shot_id] = {
                    "fingerprint": fingerprint,
                    "output": str(output_path.relative_to(PROJECT_ROOT)),
                }

                save_manifest(manifest)

                print(f"Generated: {result}")
                print(f"Latency: {latency}s")

                generated += 1
                break

            except Exception as exc:

                latency = round(time.perf_counter() - started_at, 2)

                log_model_call({
                    "timestamp": started_timestamp,
                    "stage": "keyframes",
                    "shot_id": shot_id,
                    "model": model,
                    "attempt": attempt,
                    "parameters": {
                        "width": IMAGE_WIDTH,
                        "height": IMAGE_HEIGHT,
                    },
                    "seed": None,
                    "latency_sec": latency,
                    "cost": None,
                    "status": "failed",
                    "error": str(exc),
                })

                print(
                    f"Attempt {attempt}/{MAX_ATTEMPTS} failed "
                    f"for {shot_id}: {exc}"
                )

                if attempt == MAX_ATTEMPTS:
                    raise RuntimeError(
                        f"Keyframe generation failed for {shot_id} "
                        f"after {MAX_ATTEMPTS} attempts."
                    ) from exc

                time.sleep(2 ** attempt)

    print("\nKeyframe stage finished.")
    print(f"Generated: {generated}")
    print(f"Skipped: {skipped}")


if __name__ == "__main__":

    storyboard = validate_storyboard()
    validate_production_readiness(storyboard)

    generate_keyframes(storyboard)
