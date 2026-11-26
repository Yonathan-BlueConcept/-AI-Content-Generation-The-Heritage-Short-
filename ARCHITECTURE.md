# Architecture — BONO Heritage Short

## 1. System Overview

BONO is a storyboard-driven AI video production pipeline. It transforms a structured storyboard into a complete short documentary through five independent production stages:

1. Keyframe generation
2. Video generation
3. Music generation
4. Narration generation
5. Video assembly

The storyboard is the central contract between stages. Each stage reads the same storyboard and generates its corresponding assets.

## 2. Architecture Principles

- **Separation of concerns:** Each production stage has its own module and responsibility.
- **Storyboard as the contract:** Production decisions and shot-level content are defined in `storyboard.json`.
- **Reproducibility:** Model parameters and execution details are recorded in `runs.jsonl` where available.
- **Caching:** Existing outputs are reused when their input fingerprints have not changed.
- **Failure isolation:** A failed stage should stop dependent production work rather than silently producing an incomplete film.
- **Configuration through environment variables:** API credentials are kept outside source code.

## 3. Pipeline Structure

```text
storyboard.json
       |
       v
Storyboard Validation
       |
       v
Keyframe Generation
       |
       v
Video Generation
       |
       +-------------------+
       |                   |
       v                   v
Music Generation     Narration Generation
       |                   |
       +---------+---------+
                 |
                 v
          Video Assembly
                 |
                 v
       Final Film Deliverables
       - Vertical video (9:16)
       - Horizontal video (16:9)
       - English subtitles
```

Music and narration generation can execute concurrently. Assembly depends on the required generated video, music, and narration assets.

## 4. Repository Components

| Component | Responsibility |
|---|---|
| `storyboard.json` | Defines shots, prompts, narration, subtitles, and generation settings |
| `schema/storyboard.schema.json` | Defines the storyboard data structure |
| `pipeline/validate.py` | Loads and validates the storyboard |
| `pipeline/run.py` | Coordinates production stages |
| `stages/keyframes.py` | Generates shot keyframes |
| `stages/videos.py` | Generates moving video clips |
| `stages/music.py` | Generates the background score |
| `stages/narration.py` | Generates spoken narration |
| `stages/assembly.py` | Combines generated assets into final films |
| `providers/` | Integrates external AI generation services |
| `tests/` | Contains automated pipeline tests |
| `runs.jsonl` | Records model execution metadata |

## 5. External Services

The pipeline integrates several external services:

- Cloudflare FLUX.2 Klein 4B for keyframe generation.
- Stable Video Diffusion XT for video generation.
- Stability AI Stable Audio 3.0 for music generation.
- Addis AI Addis Voices 2 for Amharic narration.

Video generation uses a separate FastAPI service running in a Kaggle environment and exposed through a Cloudflare Tunnel. Other generation services are accessed through their provider integrations.

## 6. Caching and Regeneration

Each production stage uses cached outputs when its relevant inputs have not changed.

The pipeline uses input fingerprints to determine whether an existing asset can be reused. This reduces unnecessary API calls, processing time, and generation costs.

A change to one shot should invalidate the affected shot's dependent assets rather than requiring every production asset to be generated again.

Final assembly can also be forced independently when an existing output needs to be rebuilt.

## 7. Testing

Automated tests cover pipeline orchestration and failure handling. Stage behavior is mocked in these tests so that the tests do not require external API calls.

The tests verify that production stops appropriately when a required stage fails.

## 8. Architectural Limitations

- Video generation depends on an external Kaggle runtime and tunnel.
- Generation quality and availability depend on external AI providers.
- Some providers do not expose reproducibility metadata such as seeds or exact generation costs.
- The pipeline is a sequential production workflow with limited parallel execution; it is not a distributed job-processing system.
- Generated assets are stored locally and are not automatically synchronized across machines.

These limitations are documented rather than hidden because they affect portability, reproducibility, and future maintenance.