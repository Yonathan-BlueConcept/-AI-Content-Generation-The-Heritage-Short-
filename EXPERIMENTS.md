# Experiments — BONO Heritage Short

## 1. Purpose

This document records the technical and creative experiments conducted while developing the BONO production pipeline.

The experiments focus on generation workflows, model constraints, production reliability, and final film quality.

## 2. Experiments

### Experiment 1 — AI-Generated Keyframes

**Objective:** Generate visual representations of the BONO water source and its surrounding environment.

**Approach:** Use Cloudflare FLUX.2 Klein 4B to generate images from storyboard prompts.

**Observation:** Generated images provide a practical way to visualize a remembered location without historical photographs.

**Limitation:** Generated details cannot be treated as historically accurate evidence.

### Experiment 2 — Image-to-Video Generation

**Objective:** Turn storyboard keyframes into moving shots.

**Approach:** Use Stable Video Diffusion XT to generate video clips from images.

**Observation:** The model produces short clips, making shot-level generation and later assembly necessary.

### Experiment 3 — Short-Clip Production Strategy

**Objective:** Determine how to produce a documentary longer than the model's individual clip duration.

**Approach:** Divide the film into 21 storyboard shots, each planned for approximately three seconds.

**Observation:** Short independent clips provide manageable production units that can be assembled into a longer film.

### Experiment 4 — Storyboard as a Production Contract

**Objective:** Keep visual generation, narration, subtitles, and assembly consistent.

**Approach:** Define shot information in a structured `storyboard.json` file and validate it against a JSON Schema.

**Observation:** A shared structured contract makes production stages easier to coordinate and maintain.

### Experiment 5 — Stage Separation

**Objective:** Improve maintainability and make individual production stages independently executable.

**Approach:** Separate keyframes, videos, music, narration, and assembly into individual stage modules.

**Observation:** Each stage has a distinct responsibility and can be developed or executed independently.

### Experiment 6 — Concurrent Audio Generation

**Objective:** Reduce unnecessary waiting during production.

**Approach:** Run music and narration generation concurrently using a thread pool.

**Observation:** These stages do not depend on each other's outputs, so they can execute in parallel before assembly.

### Experiment 7 — Caching and Selective Regeneration

**Objective:** Avoid repeating expensive generation calls.

**Approach:** Use input fingerprints to determine whether generated assets can be reused.

**Observation:** Cached outputs reduce unnecessary regeneration when relevant inputs remain unchanged.

### Experiment 8 — Automated Pipeline Failure Testing

**Objective:** Verify that failures in required production stages are handled safely.

**Approach:** Write automated tests using mocked stages, including a test where music generation fails.

**Observation:** The tests verify that final assembly does not proceed when a required stage fails.

### Experiment 9 — Final Film Format Validation

**Objective:** Produce deliverables suitable for both vertical and horizontal viewing.

**Approach:** Assemble separate 9:16 and 16:9 versions and inspect their video dimensions and audio streams using FFprobe.

**Observation:** Both output formats were generated and their media properties were inspected.

### Experiment 10 — Subtitle and Audio Review

**Objective:** Make the film understandable and ensure narration remains clear.

**Approach:** Review the assembled outputs for subtitle readability, narration quality, music balance, and black frames.

**Observation:** The reviewed versions had readable subtitles, clear narration and music, and no observed black frames. A separate AI-generated-content end card was identified as missing and was subsequently addressed in the assembly implementation.

## 3. Overall Findings

The experiments demonstrate that a structured, modular pipeline can combine multiple AI services into a coherent documentary production workflow.

The most important engineering findings were:

- Model limitations should influence storyboard design.
- A structured storyboard improves consistency between production stages.
- Caching is important when generation calls are expensive.
- Independent stages can be executed concurrently.
- Automated tests should verify failure behavior.
- Final outputs require human review beyond successful pipeline execution.

## 4. Limitations of the Experiments

These experiments were conducted as part of one production project, not as controlled scientific benchmarks.

The observations are qualitative unless supported by recorded execution data. No unsupported performance improvements, cost savings, or model-quality comparisons are claimed.