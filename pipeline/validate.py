
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


if __name__ == "__main__":
    try:
        validate_storyboard()

    except StoryboardValidationError as exc:
        print(exc)
        raise SystemExit(1)
