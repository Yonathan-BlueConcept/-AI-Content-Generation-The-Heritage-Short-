import math
import json
from pathlib import Path

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parent.parent

STORYBOARD_PATH = PROJECT_ROOT / "storyboard.json"
SCHEMA_PATH = PROJECT_ROOT / "schema" / "storyboard.schema.json"


class StoryboardValidationError(Exception):
    """Raised when the storyboard does not satisfy its schema."""


def load_json(path: Path) -> dict:
    """Load a JSON file and return its contents."""

    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    except json.JSONDecodeError as exc:
        raise StoryboardValidationError(
            f"Invalid JSON in {path.name}: {exc}"
        ) from exc

    except FileNotFoundError as exc:
        raise StoryboardValidationError(
            f"File not found: {path}"
        ) from exc


def validate_storyboard() -> dict:
    """Load and validate the project storyboard."""

    storyboard = load_json(STORYBOARD_PATH)
    schema = load_json(SCHEMA_PATH)

    validator = Draft202012Validator(schema)

    errors = sorted(
        validator.iter_errors(storyboard),
        key=lambda error: list(error.absolute_path)
    )

    if errors:
        messages = []

        for error in errors:
            field = ".".join(str(part) for part in error.absolute_path)
            field = field or "root"

            messages.append(f"- {field}: {error.message}")

        raise StoryboardValidationError(
            "Storyboard validation failed:\n"
            + "\n".join(messages)
        )

    print("Storyboard validation: PASSED")

    return storyboard


def validate_production_readiness(storyboard: dict) -> None:
    """Check whether a valid storyboard is ready for production."""

    errors = []

    project = storyboard["project"]
    production = storyboard["production"]
    audio = storyboard["audio"]
    shots = storyboard["shots"]

    # 1. At least one shot must exist.
    if not shots:
        errors.append("The storyboard must contain at least one shot.")

    # 2. Shot IDs must be unique.
    shot_ids = [shot["id"] for shot in shots]

    if len(shot_ids) != len(set(shot_ids)):
        errors.append("Shot IDs must be unique.")

    # 3. Total shot duration must match the target duration.
    total_duration = sum(
        shot["duration_sec"] for shot in shots
    )

    target_duration = project["target_duration_sec"]

    if not math.isclose(
        total_duration,
        target_duration,
        abs_tol=0.01
    ):
        errors.append(
            f"Total shot duration is {total_duration}s, "
            f"but target duration is {target_duration}s."
        )

    # 4. Check narration and subtitles when narration is enabled.
    if audio["narration"]["enabled"]:
        for shot in shots:
            if not shot["narration_am"].strip():
                errors.append(
                    f"{shot['id']}: Amharic narration is missing."
                )

            if not shot["subtitle_en"].strip():
                errors.append(
                    f"{shot['id']}: English subtitle is missing."
                )

    # 5. Calculate how many generated clips each shot requires.
    max_clip_duration = production["max_clip_duration_sec"]

    for shot in shots:
        required_clips = math.ceil(
            shot["duration_sec"] / max_clip_duration
        )

        print(
            f"{shot['id']}: {shot['duration_sec']}s "
            f"-> {required_clips} generated clip(s)"
        )

    if errors:
        raise StoryboardValidationError(
            "Production readiness validation failed:\n"
            + "\n".join(f"- {error}" for error in errors)
        )

    print(f"Total storyboard duration: {total_duration}s")
    print("Production readiness validation: PASSED")



if __name__ == "__main__":
    try:
        storyboard = validate_storyboard()
        validate_production_readiness(storyboard)

    except StoryboardValidationError as exc:
        print(exc)
        raise SystemExit(1)
