# BONO Infrastructure and Cost Documentation

## 1. Overview

BONO uses multiple external AI services to generate images, video, narration, and music.

The project records execution metadata in `runs.jsonl`, including model, parameters, seed, latency, cost, and execution status where the provider makes that information available.

A `null` cost means the provider did not supply a reliable cost value. It does not mean the service was necessarily free.

## 2. Services Used

| Component | Service / Model | Purpose |
|---|---|---|
| Keyframes | Cloudflare FLUX.2 Klein 4B | Generate shot images |
| Video | Stable Video Diffusion XT | Animate shot images |
| Music | Stability AI Stable Audio 3.0 | Generate background music |
| Narration | Addis AI Addis Voices 2 | Generate Amharic narration |

## 3. Infrastructure

Video generation runs through a FastAPI service hosted in a Kaggle runtime and exposed through Cloudflare Tunnel.

The production pipeline runs locally and stores generated assets and final outputs on the local machine.

Infrastructure usage may involve external service limits and account-specific quotas.

## 4. Cost Accounting

- Actual generation costs should be taken from provider billing records and available execution logs.
- The project does not assign estimated prices to API calls when the provider does not expose reliable cost information.
- The `runs.jsonl` log is the primary source for per-execution metadata.

## 5. Cost Optimization

The pipeline reduces unnecessary generation through caching.

When the relevant input fingerprint has not changed, existing generated assets are reused.

This avoids repeating expensive generation calls when rerunning the pipeline or changing unrelated parts of the production.

The assembly stage can also be rerun independently without regenerating all source assets.

## 6. Cost Limitations

- Provider pricing and free-tier allowances may change.
- Some services do not expose per-request cost data.
- Kaggle and Cloudflare Tunnel availability depends on external account limits.
- Local processing and storage costs are not automatically calculated by the pipeline.