
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from providers.addis_tts import (
    generate_speech,
    estimate_speech_cost,
    VOICE_ID,
    LANGUAGE,
    OUTPUT_FORMAT,
)
from pipeline.validate import (
    validate_storyboard,
    validate_production_readiness,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

OUTPUT_DIR = PROJECT_ROOT / "assets" / "audio" / "narration"
MANIFEST_PATH = OUTPUT_DIR / ".manifest.json"
RUNS_PATH = PROJECT_ROOT / "runs.jsonl"

MODEL = "addis-voices-2"


def create_fingerprint(text: str) -> str:
    settings = {
        "model": MODEL,
        "voice_id": VOICE_ID,
        "language": LANGUAGE,
        "output_format": OUTPUT_FORMAT,
        "text": text,
    }

    serialized = json.dumps(
        settings,
        sort_keys=True,
        ensure_ascii=False,
    )

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()


def create_request_id(shot_id: str, fingerprint: str) -> str:
    """
    Stable ID for this exact narration request.
    Reusing it makes uncertain retries idempotent.
    """
    return f"bono-{shot_id}-{fingerprint[:20]}"


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
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    temporary_path.replace(MANIFEST_PATH)


def append_run_log(record: dict) -> None:
    RUNS_PATH.parent.mkdir(parents=True, exist_ok=True)

    with RUNS_PATH.open("a", encoding="utf-8") as file:
        file.write(
            json.dumps(record, ensure_ascii=False) + "\n"
        )


def generate_narration(
    storyboard: dict,
    force: bool = False,
    shot_ids: set[str] | None = None,
) -> None:

    narration_config = storyboard["audio"]["narration"]

    if not narration_config["enabled"]:
        print("Narration generation is disabled.")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest()
    failed_shots = []

    for shot in storyboard["shots"]:
        shot_id = shot["id"]

        if shot_ids is not None and shot_id not in shot_ids:
            continue

        text = shot["narration_am"].strip()

        if not text:
            print(f"Skipping {shot_id}: narration is empty.")
            continue

        fingerprint = create_fingerprint(text)
        request_id = create_request_id(shot_id, fingerprint)

        output_path = OUTPUT_DIR / f"{shot_id}.mp3"
        relative_output = str(
            output_path.relative_to(PROJECT_ROOT)
        )

        cached = manifest.get(shot_id, {})

        if (
            not force
            and cached.get("fingerprint") == fingerprint
            and output_path.exists()
            and output_path.stat().st_size > 0
        ):
            print(f"{shot_id}: using cached narration.")
            continue

        print(f"\nGenerating narration for {shot_id}...")

        started_at = time.monotonic()
        timestamp = datetime.now(timezone.utc).isoformat()

        record = {
            "timestamp": timestamp,
            "stage": "narration",
            "shot": shot_id,
            "model": MODEL,
            "parameters": {
                "voice_id": VOICE_ID,
                "language": LANGUAGE,
                "output_format": OUTPUT_FORMAT,
                "character_count": len(text),
                "text_sha256": hashlib.sha256(
                    text.encode("utf-8")
                ).hexdigest(),
                "client_request_id": request_id,
            },
            "latency_seconds": None,
            "cost": None,
            "status": "failed",
            "output": relative_output,
        }

        try:
            # Estimate first, so we can check available balance.
            estimate = estimate_speech_cost(text)

            estimate_data = estimate.get("data", estimate)

            if not estimate_data.get("can_generate", False):
                raise RuntimeError(
                    f"Insufficient balance for {shot_id}. "
                    f"Estimated cost: "
                    f"{estimate_data.get('estimated_cost')} ETB"
                )

            result = generate_speech(
                text=text,
                output_path=output_path,
                client_request_id=request_id,
            )

            latency = round(
                time.monotonic() - started_at, 2
            )

            usage = result.get("usage") or {}

            actual_cost = usage.get(
                "cost",
                usage.get("total_cost"),
            )

            record.update({
                "clip_id": result.get("clip_id"),
                "request_id": result.get("request_id"),
                "usage": usage,
                "estimated_cost": estimate_data.get(
                    "estimated_cost"
                ),
                "cost": actual_cost,
                "latency_seconds": latency,
                "status": "success",
                "size_bytes": result["size_bytes"],
            })

            manifest[shot_id] = {
                "fingerprint": fingerprint,
                "client_request_id": request_id,
                "clip_id": result.get("clip_id"),
                "output": relative_output,
                "generated_at": timestamp,
            }

            save_manifest(manifest)

            print(f"{shot_id}: narration generated.")
            print(f"Saved: {output_path}")

        except Exception as exc:
            record["error"] = str(exc)
            failed_shots.append(shot_id)
            print(f"{shot_id}: FAILED - {exc}")

        finally:
            record["latency_seconds"] = round(
                time.monotonic() - started_at, 2
            )
            append_run_log(record)

    if failed_shots:
        raise RuntimeError(
            "Narration failed for: "
            + ", ".join(failed_shots)
        )

    print("\nNarration stage completed successfully.")


if __name__ == "__main__":
    storyboard = validate_storyboard()
    validate_production_readiness(storyboard)

    generate_narration(storyboard)
