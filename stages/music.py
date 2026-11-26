
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from providers.stable_audio import generate_music, MODEL
from pipeline.validate import (
    validate_storyboard,
    validate_production_readiness,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

OUTPUT_DIR = PROJECT_ROOT / "assets" / "audio" / "music"
OUTPUT_PATH = OUTPUT_DIR / "bono_soundtrack.wav"
MANIFEST_PATH = OUTPUT_DIR / ".manifest.json"
RUNS_PATH = PROJECT_ROOT / "runs.jsonl"

SEED = 0
STEPS = 8
OUTPUT_FORMAT = "wav"


def create_fingerprint(prompt: str, duration: int) -> str:
    settings = {
        "model": MODEL,
        "prompt": prompt,
        "duration": duration,
        "seed": SEED,
        "steps": STEPS,
        "output_format": OUTPUT_FORMAT,
    }

    serialized = json.dumps(
        settings,
        sort_keys=True,
        ensure_ascii=False,
    )

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()


def load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {}

    try:
        return json.loads(
            MANIFEST_PATH.read_text(encoding="utf-8")
        )
    except (json.JSONDecodeError, OSError):
        return {}


def save_manifest(manifest: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    temporary_path = MANIFEST_PATH.with_suffix(".tmp")

    temporary_path.write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    temporary_path.replace(MANIFEST_PATH)


def append_run_log(record: dict) -> None:
    RUNS_PATH.parent.mkdir(parents=True, exist_ok=True)

    with RUNS_PATH.open("a", encoding="utf-8") as file:
        file.write(
            json.dumps(record, ensure_ascii=False) + "\n"
        )


def generate_soundtrack(
    force: bool = False,
    storyboard: dict | None = None,
) -> None:
    if storyboard is None:
        storyboard = validate_storyboard()

    validate_production_readiness(storyboard)

    music_config = storyboard["audio"]["music"]

    if not music_config["enabled"]:
        print("Music generation is disabled.")
        return

    prompt = music_config["prompt"].strip()

    if not prompt:
        raise ValueError(
            "Music prompt in storyboard.json is empty."
        )

    duration = int(
        storyboard["project"]["target_duration_sec"]
    )

    fingerprint = create_fingerprint(prompt, duration)
    manifest = load_manifest()

    cached = manifest.get("soundtrack", {})

    if (
        not force
        and cached.get("fingerprint") == fingerprint
        and OUTPUT_PATH.exists()
        and OUTPUT_PATH.stat().st_size > 0
    ):
        print(f"Using cached soundtrack: {OUTPUT_PATH}")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Generating {duration}-second BONO soundtrack...")

    started_at = time.monotonic()
    timestamp = datetime.now(timezone.utc).isoformat()

    record = {
        "timestamp": timestamp,
        "stage": "music",
        "shot_id": None,
        "seed": None,
        "model": MODEL,
        "parameters": {
            "prompt": prompt,
            "duration": duration,
            "seed_requested": SEED,
            "steps": STEPS,
            "output_format": OUTPUT_FORMAT,
        },
        "latency_sec": None,
        "cost": None,
        "status": "failed",
        "output": str(
            OUTPUT_PATH.relative_to(PROJECT_ROOT)
        ),
    }

    try:
        result = generate_music(
            prompt=prompt,
            duration=duration,
            output_path=OUTPUT_PATH,
            seed=SEED,
        )

        latency = round(time.monotonic() - started_at, 2)



        record.update({
            "generation_id": result["generation_id"],
            "seed": result.get("seed"),
            "latency_sec": latency,
            "content_type": result.get("content_type"),
            "status": "success",
            "size_bytes": result["size_bytes"],
        })

        manifest["soundtrack"] = {
            "fingerprint": fingerprint,
            "model": MODEL,
            "duration_sec": duration,
            "output": str(
                OUTPUT_PATH.relative_to(PROJECT_ROOT)
            ),
            "generation_id": result["generation_id"],
            "seed_used": result.get("seed"),
            "generated_at": timestamp,
        }

        save_manifest(manifest)

        print(f"Soundtrack generated: {OUTPUT_PATH}")
        print(f"Generation time: {latency}s")

    except Exception as exc:
        record["error"] = str(exc)
        raise

    finally:
        if record["latency_sec"] is None:
            record["latency_sec"] = round(
                time.monotonic() - started_at,
                2,
            )

        append_run_log(record)


if __name__ == "__main__":
    generate_soundtrack()
