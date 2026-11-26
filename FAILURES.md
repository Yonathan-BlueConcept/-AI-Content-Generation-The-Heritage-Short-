# Failures and Troubleshooting — BONO

## 1. Video Generation Service Dependency

**Problem:** Video generation depends on a separate FastAPI service running in a Kaggle environment. The local production pipeline cannot generate clips when that service is unavailable.

**Cause:** The video-generation model runs outside the local development environment.

**Resolution:** The service is started in Kaggle and exposed to the local machine through a Cloudflare Tunnel.

**Lesson:** External generation services introduce availability and networking dependencies that must be documented and managed.

## 2. Short Video Generation Duration

**Problem:** Stable Video Diffusion XT generates clips of approximately three seconds per run, rather than complete documentary sequences.

**Cause:** The model and generation setup have a short output-duration limitation.

**Resolution:** The storyboard was divided into multiple short shots, which are generated independently and assembled into the final film.

**Lesson:** Production planning must account for model limitations before generation begins.

## 3. FFmpeg Font Configuration

**Problem:** FFmpeg's `drawtext` filter initially failed because it could not load the default Fontconfig configuration.

**Cause:** The Windows environment did not provide the Fontconfig configuration expected by the filter.

**Resolution:** The filter was configured to use an explicit Windows Arial font file. A standalone FFmpeg test confirmed that the explicit font path worked.

**Lesson:** Explicitly configuring dependencies can make media-processing commands more reliable across environments.

## 4. Assembly Regeneration

**Problem:** Changes to assembly logic do not necessarily invalidate cached source assets or trigger a new final render automatically.

**Cause:** The assembly fingerprint is based on its tracked inputs and does not include every possible implementation-code change.

**Resolution:** The assembly stage supports forced regeneration using the `--force` option.

**Lesson:** Cache invalidation must account for the distinction between changed production inputs and changed processing logic.

## 5. Automated Failure Handling

The pipeline includes tests for orchestration failure behavior.

For example, a test verifies that a music-generation failure prevents final assembly.

These tests use mocked stages rather than making external provider calls.

## 6. Remaining Limitations

- External provider outages and rate limits can interrupt generation.
- The Kaggle runtime and Cloudflare Tunnel must be available during video generation.
- AI-generated visuals may contain inconsistencies that require human review.
- Provider metadata such as seed and cost may not always be available.

## 7. Engineering Lessons

The main lessons from production were to isolate external services, keep generation stages independent, cache expensive outputs, validate inputs before production, and make failures visible instead of silently continuing with incomplete assets.