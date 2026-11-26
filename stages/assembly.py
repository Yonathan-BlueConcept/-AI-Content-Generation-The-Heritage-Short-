
import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from pipeline.validate import (
    validate_storyboard,
    validate_production_readiness,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

VIDEO_DIR = PROJECT_ROOT / "assets" / "videos"
NARRATION_DIR = PROJECT_ROOT / "assets" / "audio" / "narration"
MUSIC_PATH = PROJECT_ROOT / "assets" / "audio" / "music" / "bono_soundtrack.wav"

OUTPUT_DIR = PROJECT_ROOT / "outputs"
TEMP_DIR = PROJECT_ROOT / "assets" / "temp" / "assembly"
MANIFEST_PATH = OUTPUT_DIR / ".manifest.json"

FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"

# Output dimensions: width, height
FORMATS = {
    "vertical": (1080, 1920),
    "horizontal": (1920, 1080),
}

MAX_FILM_DURATION = 90


def run_command(command: list[str]) -> None:
    """Run an external command and display useful errors."""
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed:\n{' '.join(command)}\n\n"
            f"{result.stderr[-4000:]}"
        )


def get_duration(path: Path) -> float:
    """Read media duration using ffprobe."""
    command = [
        FFPROBE,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Could not read duration of {path}:\n{result.stderr}"
        )

    return float(result.stdout.strip())


def file_hash(path: Path) -> str:
    """Calculate a SHA-256 fingerprint for an input file."""
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {}

    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
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


def check_required_assets(storyboard: dict) -> list[dict]:
    """Check all required assets and calculate the final timeline."""
    missing = []
    timeline = []

    for shot in storyboard["shots"]:
        shot_id = shot["id"]

        video_path = VIDEO_DIR / f"{shot_id}.mp4"
        narration_path = NARRATION_DIR / f"{shot_id}.mp3"

        for path in (video_path, narration_path):
            if not path.exists() or path.stat().st_size == 0:
                missing.append(str(path.relative_to(PROJECT_ROOT)))

        if video_path.exists() and narration_path.exists():
            video_duration = get_duration(video_path)
            narration_duration = get_duration(narration_path)

            # Preserve the complete narration.
            # Extend the video by holding its final frame if necessary.
            segment_duration = max(
                video_duration,
                narration_duration,
            )

            timeline.append({
                "shot_id": shot_id,
                "video_path": video_path,
                "narration_path": narration_path,
                "video_duration": video_duration,
                "narration_duration": narration_duration,
                "duration": segment_duration,
            })

    if not MUSIC_PATH.exists() or MUSIC_PATH.stat().st_size == 0:
        missing.append(str(MUSIC_PATH.relative_to(PROJECT_ROOT)))

    if missing:
        print("\nMissing required assets:")
        for item in missing:
            print(f"  - {item}")

        raise FileNotFoundError(
            f"{len(missing)} required asset(s) are missing. "
            "Finish video generation and run assembly again."
        )

    total_duration = sum(item["duration"] for item in timeline)

    print("\nProduction timeline:")
    for item in timeline:
        print(
            f"  {item['shot_id']}: "
            f"video={item['video_duration']:.2f}s, "
            f"narration={item['narration_duration']:.2f}s, "
            f"timeline={item['duration']:.2f}s"
        )

    print(f"\nTotal film duration: {total_duration:.2f}s")

    if total_duration > MAX_FILM_DURATION:
        raise ValueError(
            f"Film duration is {total_duration:.2f}s, "
            f"exceeding the {MAX_FILM_DURATION}s assignment limit. "
            "The narration and storyboard timing need adjustment."
        )

    if total_duration < 60:
        raise ValueError(
            f"Film duration is only {total_duration:.2f}s. "
            "The assignment requires at least 60 seconds."
        )

    return timeline


def create_subtitles(
    storyboard: dict,
    timeline: list[dict],
) -> Path:
    """Create an English SRT subtitle file from storyboard timings."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    subtitle_path = OUTPUT_DIR / "bono_english_subtitles.srt"

    def timestamp(seconds: float) -> str:
        milliseconds = round(seconds * 1000)
        hours, remainder = divmod(milliseconds, 3_600_000)
        minutes, remainder = divmod(remainder, 60_000)
        whole_seconds, milliseconds = divmod(remainder, 1000)

        return (
            f"{hours:02}:{minutes:02}:"
            f"{whole_seconds:02},{milliseconds:03}"
        )

    lines = []
    current_time = 0.0

    for index, item in enumerate(timeline, start=1):
        shot = next(
            shot for shot in storyboard["shots"]
            if shot["id"] == item["shot_id"]
        )

        start = current_time
        end = current_time + item["duration"]

        subtitle = shot["subtitle_en"].strip()

        lines.extend([
            str(index),
            f"{timestamp(start)} --> {timestamp(end)}",
            subtitle,
            "",
        ])

        current_time = end

    subtitle_path.write_text(
        "\n".join(lines),
        encoding="utf-8-sig",
    )

    return subtitle_path


def create_shot_segment(
    item: dict,
    output_path: Path,
    width: int,
    height: int,
    is_final_shot: bool,
) -> None:
    """Create one aspect-ratio-specific shot with its full narration."""
    video_duration = item["video_duration"]
    segment_duration = item["duration"]
    extra_duration = max(0, segment_duration - video_duration)

    video_filter = (
        f"fps=30,"
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},"
        f"setsar=1,"
        f"tpad=stop_mode=clone:stop_duration={extra_duration:.3f}"
    )

    if is_final_shot:
        font_path = Path("C:/Windows/Fonts/arial.ttf")

        font_option = ""
        if font_path.exists():
            font_option = (
                "fontfile='C\\:/Windows/Fonts/arial.ttf':"
            )

        video_filter += (
            f",drawtext={font_option}"
            "text='BONO':"
            "fontcolor=white:"
            "fontsize=h*0.075:"
            "x=(w-text_w)/2:"
            "y=h*0.73:"
            "box=1:"
            "boxcolor=black@0.35:"
            "boxborderw=20"
        )

        video_filter += (
            f",drawtext={font_option}"
            "text='THE WATER THAT CONNECTED US':"
            "fontcolor=white:"
            "fontsize=h*0.025:"
            "x=(w-text_w)/2:"
            "y=h*0.82:"
            "box=1:"
            "boxcolor=black@0.35:"
            "boxborderw=12"
        )

    filter_complex = (
    f"[0:v]{video_filter}[v];"
    "[1:a]aresample=48000,"
    "aformat=sample_fmts=fltp:channel_layouts=stereo,"
    "apad[a]"
)

    command = [
        FFMPEG,
        "-y",
        "-i", str(item["video_path"]),
        "-i", str(item["narration_path"]),
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "[a]",
        "-t", f"{segment_duration:.3f}",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "48000",
        "-movflags", "+faststart",
        str(output_path),
    ]

    run_command(command)


def create_concat_file(segment_paths: list[Path], path: Path) -> None:
    """Create an FFmpeg concat-demuxer input file."""
    lines = []

    for segment in segment_paths:
        normalized = segment.resolve().as_posix()
        normalized = normalized.replace("'", r"'\''")
        lines.append(f"file '{normalized}'")

    path.write_text("\n".join(lines), encoding="utf-8")


def assemble_format(
    format_name: str,
    dimensions: tuple[int, int],
    timeline: list[dict],
    subtitle_path: Path,
    fingerprint: str,
    force: bool,
) -> None:
    """Build one complete film format."""
    width, height = dimensions

    output_path = OUTPUT_DIR / f"bono_heritage_{format_name}.mp4"
    manifest = load_manifest()

    cached = manifest.get(format_name, {})

    if (
        not force
        and cached.get("fingerprint") == fingerprint
        and output_path.exists()
        and output_path.stat().st_size > 0
    ):
        print(f"\n{format_name}: using cached final film.")
        return

    format_temp_dir = TEMP_DIR / format_name
    format_temp_dir.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    segment_paths = []

    print(f"\nBuilding {format_name} version ({width}x{height})...")

    for index, item in enumerate(timeline):
        segment_path = format_temp_dir / f"{index + 1:02}.mp4"

        create_shot_segment(
            item=item,
            output_path=segment_path,
            width=width,
            height=height,
            is_final_shot=index == len(timeline) - 1,
        )

        segment_paths.append(segment_path)
        print(f"  Prepared {item['shot_id']}")

    concat_path = format_temp_dir / "concat.txt"
    concatenated_path = format_temp_dir / "concatenated.mp4"

    create_concat_file(segment_paths, concat_path)

    print("  Joining video and narration segments...")

    run_command([
        FFMPEG,
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_path),
        "-c", "copy",
        str(concatenated_path),
    ])

    # Escape the Windows drive colon for FFmpeg's filter parser.
    subtitle_filter_path = (
        subtitle_path.resolve()
        .as_posix()
        .replace(":", r"\:")
        .replace("'", r"\'")
    )

    subtitle_size = 18 if format_name == "vertical" else 31
    subtitle_margin = 65 if format_name == "vertical" else 55

    subtitle_filter = (
        f"subtitles=filename='{subtitle_filter_path}':"
        f"force_style='FontName=Arial,FontSize={subtitle_size},"
        f"Outline=2,Shadow=1,Alignment=2,MarginV={subtitle_margin}'"
    )

    total_duration = sum(item["duration"] for item in timeline)

    print("  Adding subtitles and mixing background music...")

    
    filter_complex = (
        "[0:a]asplit=2[voice_sc][voice_mix];"
        "[1:a]volume=0.20[music];"
        "[music][voice_sc]sidechaincompress="
        "threshold=0.03:ratio=8:attack=25:release=500[ducked];"
        "[voice_mix][ducked]amix=inputs=2:duration=first:"
        "dropout_transition=2,"
        "loudnorm=I=-16:TP=-1.5:LRA=11[aout]"
    )


    run_command([
        FFMPEG,
        "-y",
        "-i", str(concatenated_path),
        "-stream_loop", "-1",
        "-i", str(MUSIC_PATH),
        "-filter_complex", filter_complex,
        "-map", "0:v:0",
        "-map", "[aout]",
        "-vf", subtitle_filter,
        "-t", f"{total_duration:.3f}",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "48000",
        "-movflags", "+faststart",
        str(output_path),
    ])

    # Verify the final output before updating the cache.
    final_duration = get_duration(output_path)

    if abs(final_duration - total_duration) > 1.0:
        raise RuntimeError(
            f"{format_name} output duration mismatch: "
            f"expected {total_duration:.2f}s, "
            f"got {final_duration:.2f}s"
        )

    manifest[format_name] = {
        "fingerprint": fingerprint,
        "output": str(output_path.relative_to(PROJECT_ROOT)),
        "duration_seconds": round(final_duration, 2),
        "resolution": f"{width}x{height}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    save_manifest(manifest)

    print(f"  Finished: {output_path}")
    print(f"  Duration: {final_duration:.2f}s")


def assemble_film(
    force: bool = False,
    storyboard: dict | None = None,
) -> None:
    """Assemble the final films from a supplied or production storyboard."""

    if storyboard is None:
        storyboard = validate_storyboard()

    validate_production_readiness(storyboard)

    print("\nChecking required production assets...")
    timeline = check_required_assets(storyboard)

    subtitle_path = create_subtitles(storyboard, timeline)

    # Include every input file in the assembly fingerprint.
    fingerprint_data = {
        "storyboard": storyboard,
        "inputs": [],
    }

    for item in timeline:
        fingerprint_data["inputs"].extend([
            file_hash(item["video_path"]),
            file_hash(item["narration_path"]),
        ])

    fingerprint_data["inputs"].append(file_hash(MUSIC_PATH))

    fingerprint = hashlib.sha256(
        json.dumps(
            fingerprint_data,
            sort_keys=True,
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()

    for format_name, dimensions in FORMATS.items():
        assemble_format(
            format_name=format_name,
            dimensions=dimensions,
            timeline=timeline,
            subtitle_path=subtitle_path,
            fingerprint=fingerprint,
            force=force,
        )

    print("\nAssembly completed.")
    print(f"Vertical:   {OUTPUT_DIR / 'bono_heritage_vertical.mp4'}")
    print(f"Horizontal: {OUTPUT_DIR / 'bono_heritage_horizontal.mp4'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate both final films even if cached.",
    )
    args = parser.parse_args()

    assemble_film(force=args.force)
