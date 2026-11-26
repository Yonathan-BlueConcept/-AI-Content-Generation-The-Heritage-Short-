# BONO: The Water That Connected Us

An AI-powered documentary film about BONO, a former communal drinking-water source in an Ethiopian village, and the role it played in everyday community life.

This project combines AI-generated imagery, image-to-video generation, Amharic narration, English subtitles, original background music, and deterministic FFmpeg assembly in a reproducible production pipeline.

## Film Deliverables

The production storyboard defines a 63-second documentary consisting of 21 shots.

| Deliverable | Description |
|---|---|
| Vertical film | 9:16 MP4 |
| Horizontal film | 16:9 MP4 |
| Narration | Amharic |
| Subtitles | English |
| Music | Original AI-generated soundtrack |
| Visuals | AI-generated keyframes and video clips |

The final videos are submitted separately from this GitHub repository, as required by the assignment.

## Architecture

The pipeline is organized into five production stages:

1. **Keyframes** — Generate images from storyboard visual prompts.
2. **Moving shots** — Convert keyframes into short video clips using Stable Video Diffusion XT.
3. **Music** — Generate the original soundtrack.
4. **Narration** — Generate Amharic voice narration for each shot.
5. **Assembly** — Synchronize and combine video, narration, music, and English subtitles into vertical and horizontal films.

### Pipeline execution flow

```text
                 storyboard.json
                       |
                       v
              Storyboard Validation
                       |
                       v
                 Keyframe Stage
                       |
                       v
                  Video Stage
                       |
             +---------+---------+
             |                   |
             v                   v
        Music Stage        Narration Stage
             |                   |
             +---------+---------+
                       |
                       v
                Assembly Stage
                       |
              +--------+--------+
              |                 |
              v                 v
        Vertical Film     Horizontal Film
```

Music and narration run concurrently after video generation. Assembly starts only after both stages complete successfully.

## Repository Structure

```text
theheritageshort/
│
├── pipeline/
│   ├── run.py
│   ├── validate.py
│   ├── graph.py
│   └── state.py
│
├── providers/
│   ├── cloudflare_images.py
│   ├── video_api.py
│   ├── stable_audio.py
│   └── addis_tts.py
│
├── stages/
│   ├── keyframes.py
│   ├── videos.py
│   ├── music.py
│   ├── narration.py
│   └── assembly.py
│
├── schema/
│   └── storyboard.schema.json
│
├── tests/
│   ├── test_pipeline.py
│   └── fixtures/
│       └── storyboard.test.json
│
├── assets/                 # Generated assets (not committed)
├── outputs/                # Final films (not committed)
├── cache/                  # Cache data
│
├── storyboard.json         # Production storyboard
├── runs.jsonl              # Model execution log
├── ARCHITECTURE.md
├── COSTS.md
├── DESIGN.md
├── ETHICS.md
├── EXPERIMENTS.md
├── FAILURES.md
├── pyproject.toml
├── uv.lock
└── .env.example
```

## Core Design: Storyboard as the Contract

`storyboard.json` is the central production contract.

It defines:

- Project metadata and target duration.
- Output aspect ratios.
- Narration and music configuration.
- Shot identifiers and durations.
- Visual and motion prompts.
- Amharic narration text.
- English subtitles.
- Per-shot generation settings.

Each production stage reads the relevant storyboard information and generates its corresponding assets.

This keeps production decisions separate from implementation and allows changes to individual shots without redesigning the entire pipeline.

The storyboard is validated against `schema/storyboard.schema.json` before production begins.

## Technology Stack

| Component | Technology |
|---|---|
| Pipeline orchestration | Python |
| Dependency management | uv |
| Storyboard validation | JSON Schema |
| Keyframe generation | Cloudflare FLUX.2 Klein 4B |
| Video generation | Stable Video Diffusion XT |
| Video API | FastAPI + Uvicorn |
| GPU environment | Kaggle |
| Public API tunnel | Cloudflare Tunnel |
| Music generation | Stability AI Stable Audio 3.0 |
| Amharic narration | Addis AI / Addis Voices |
| Video processing | FFmpeg |
| Logging | JSON Lines |

## Requirements

### Local machine

- Python 3.14 or compatible version satisfying `pyproject.toml`.
- [uv](https://docs.astral.sh/uv/)
- FFmpeg and FFprobe installed and available in your system PATH.
- Internet connection for provider API access.

### External video-generation service

Video generation requires:

- A Kaggle account with GPU access.
- The saved Kaggle notebook containing the Stable Video Diffusion XT service.
- Cloudflare Tunnel.

The video-generation service runs separately from the local production pipeline.

## Installation

Clone the repository:

```bash
git clone https://github.com/Yonathan-BlueConcept/-AI-Content-Generation-The-Heritage-Short-.git
cd ./-AI-Content-Generation-The-Heritage-Short-
```

Install dependencies:

```bash
uv sync
```

Create your local environment file.

PowerShell:

```powershell
Copy-Item .env.example .env
```

Linux/macOS:

```bash
cp .env.example .env
```

Configure the required credentials in `.env`:

```env
CLOUDFLARE_ACCOUNT_ID=your_cloudflare_account_id
CLOUDFLARE_API_TOKEN=your_cloudflare_api_token

STABILITY_API_KEY=your_stability_api_key

ADDIS_API_KEY=your_addis_api_key

VIDEO_API_BASE_URL=https://your-video-api-tunnel-url
```

Never commit `.env` or expose API credentials in source code.

## Starting the Video Generation Service

The Stable Video Diffusion XT service runs in Kaggle rather than on the local machine.

### 1. Start the Kaggle runtime

Open the saved notebook and enable GPU acceleration.

The notebook installs the service dependencies and Cloudflare Tunnel:

```python
%pip install -q fastapi uvicorn python-multipart
```

It also installs `cloudflared`, loads the Stable Video Diffusion XT model, and initializes the FastAPI application.

Model:

```text
stabilityai/stable-video-diffusion-img2vid-xt
```

The service uses a GPU and generates short video clips from uploaded images.

### 2. Start the FastAPI service

The notebook starts Uvicorn on:

```text
0.0.0.0:8000
```

The service provides these endpoints:

| Endpoint | Method | Purpose |
|---|---|---|
| `/health` | GET | Check service health |
| `/generate` | POST | Submit an image-to-video job |
| `/jobs/{job_id}` | GET | Check generation status |
| `/videos/{job_id}` | GET | Download the completed video |

### 3. Start Cloudflare Tunnel

Run the following in a Kaggle notebook cell:

```bash
cloudflared tunnel --url http://localhost:8000
```

Cloudflare generates a temporary public HTTPS URL.

For example:

```text
https://example.trycloudflare.com
```

Copy the newly generated URL into your local `.env`:

```env
VIDEO_API_BASE_URL=https://example.trycloudflare.com
```

**Important:** Cloudflare Quick Tunnel URLs change when the tunnel restarts. Update `.env` whenever a new URL is generated.

Keep the Kaggle runtime and tunnel running while the local pipeline is generating videos.

## Running the Production Pipeline

Once the environment variables are configured and the video service is available, execute:

```bash
uv run python -m pipeline.run
```

The pipeline performs the following operations:

1. Validates the production storyboard.
2. Generates missing keyframes.
3. Generates missing video clips.
4. Generates music and narration concurrently.
5. Assembles the final films.

To force regeneration:

```bash
uv run python -m pipeline.run --force
```

**Warning:** Forced regeneration can trigger additional provider API usage and costs.

## Storyboard Validation

Validate the production storyboard independently:

```bash
uv run python -m pipeline.validate
```

Validation checks the storyboard against its JSON Schema and verifies production readiness, including shot identifiers, duration consistency, narration and subtitle requirements, and video clip limits.

The production storyboard currently contains 21 shots with a total duration of 63 seconds.

## Tests

Run the orchestration tests:

```bash
uv run python -m unittest tests.test_pipeline -v
```

The tests verify:

- Correct stage execution order.
- Failure propagation.
- Prevention of assembly when required stages fail.
- Concurrent execution of music and narration.

The orchestration tests use mocked stages, so they do not require paid provider API calls or a running Kaggle GPU service.

## Generated Assets and Outputs

Generated assets are stored locally and excluded from Git.

Expected output structure:

```text
assets/
├── keyframes/
├── videos/
├── audio/
│   ├── music/
│   └── narration/
└── temp/

outputs/
├── bono_heritage_vertical.mp4
├── bono_heritage_horizontal.mp4
├── bono_english_subtitles.srt
└── .manifest.json
```

The two final MP4 files are the film deliverables.

They are intentionally excluded from the public GitHub repository and will be submitted separately.

## Caching and Regeneration

The pipeline uses stage-level manifests and input fingerprints to avoid unnecessary generation.

A stage can reuse existing outputs when its relevant inputs have not changed.

Examples:

- An unchanged keyframe can be reused.
- A cached video clip can be reused when its keyframe and generation configuration remain unchanged.
- Changing narration does not require regenerating visual assets.
- Changing a visual prompt invalidates the affected visual generation and downstream assembly.

Use `--force` when a complete regeneration is intentionally required.

## Execution Logging

Model execution records are written to:

```text
runs.jsonl
```

The log records information such as:

- Timestamp.
- Production stage.
- Shot identifier, where applicable.
- Model name.
- Generation parameters.
- Seed, when available.
- Latency.
- Cost, when available.
- Execution status.
- Output location.

Provider-specific metadata may also be recorded.

Unavailable values, such as an unsupported seed or unknown cost, are recorded as `null` rather than fabricated.

## External Dependencies and Limitations

This repository does not include the Stable Video Diffusion XT model or the Kaggle GPU service implementation.

Video generation requires the separately maintained Kaggle notebook and an active public tunnel.

The pipeline also depends on external image, music, and narration providers. Their availability, pricing, credentials, and usage limits can affect production.

Generated video quality and generation duration depend on the underlying model and runtime.

The final videos are not stored in Git because the assignment requires separate video submission.

## Project Documentation

Additional engineering and production documentation:

- `ARCHITECTURE.md` — System architecture and stage responsibilities.
- `DESIGN.md` — Creative and technical design decisions.
- `COSTS.md` — Provider costs and production expenses.
- `ETHICS.md` — Ethical considerations in AI-assisted historical reconstruction.
- `EXPERIMENTS.md` — Experiments and model evaluations.
- `FAILURES.md` — Recorded failures and lessons learned.

## License and Attribution

This project uses third-party AI models and services. Their respective licenses, terms of use, and attribution requirements apply.

---

**BONO: The Water That Connected Us**

A reconstruction of a place that once brought a community together.