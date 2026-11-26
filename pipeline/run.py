
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pipeline.validate import (
    validate_storyboard,
    validate_production_readiness,
)

from stages.keyframes import generate_keyframes
from stages.videos import generate_videos
from stages.music import generate_soundtrack
from stages.narration import generate_narration
from stages.assembly import assemble_film


def run_pipeline(
    force: bool = False,
    storyboard_path: Path | None = None,
    duration_range: tuple[int, int] = (60, 90),
) -> None:
    """Execute the BONO production pipeline."""

    print("\n========================================")
    print("BONO HERITAGE SHORT - PRODUCTION PIPELINE")
    print("========================================\n")

    # 1. Validate storyboard
    print("[1/5] Validating storyboard...")

    if storyboard_path is None:
        storyboard = validate_storyboard()
    else:
        storyboard = validate_storyboard(
            storyboard_path=storyboard_path,
            duration_range=duration_range,
        )

    validate_production_readiness(storyboard)

    # 2. Generate keyframes
    print("\n[2/5] Generating keyframes...")

    generate_keyframes(storyboard=storyboard, force=force)

    # 3. Generate video clips
    print("\n[3/5] Generating video clips...")

    generate_videos(storyboard=storyboard, force=force)

    # 4. Generate music and narration concurrently
    print("\n[4/5] Generating music and narration...")

    with ThreadPoolExecutor(max_workers=2) as executor:
        music_future = executor.submit(
            generate_soundtrack,
            force=force,
            storyboard=storyboard,
        )

        narration_future = executor.submit(
            generate_narration,
            storyboard=storyboard,
            force=force,
        )

        # Both futures must complete successfully.
        music_future.result()
        narration_future.result()

    # 5. Assemble final films
    print("\n[5/5] Assembling final films...")

    assemble_film(
        force=force,
        storyboard=storyboard,
    )

    print("\n========================================")
    print("PRODUCTION PIPELINE COMPLETED")
    print("========================================")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the BONO Heritage Short production pipeline."
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Force regeneration instead of using cached outputs.",
    )

    args = parser.parse_args()

    run_pipeline(force=args.force)


if __name__ == "__main__":
    main()
