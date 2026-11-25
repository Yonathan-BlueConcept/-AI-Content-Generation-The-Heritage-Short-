import hashlib
import json
import time
from pathlib import Path
from jsonschema import validate
from langgraph.graph import END, START, StateGraph

from pipeline.state import PipelineState


def _append_run_log(run_log_path: str, record: dict) -> None:
    path = Path(run_log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def validate_storyboard_node(state: PipelineState) -> PipelineState:
    t0 = time.perf_counter()
    schema_path = Path("schema/storyboard.schema.json")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    storyboard = json.loads(Path(state["storyboard_path"]).read_text(encoding="utf-8"))
    validate(instance=storyboard, schema=schema)

    _append_run_log(state["run_log_path"], {
        "stage": "validate_storyboard",
        "model": "schema_validator",
        "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
        "cost_usd": 0.0,
        "status": "ok",
    })
    return {**state, "storyboard": storyboard}


def generate_stage_node(state: PipelineState) -> PipelineState:
    out_dir = Path(state["outputs_dir"]) / "draft_manifest"
    out_dir.mkdir(parents=True, exist_ok=True)

    for shot in state["storyboard"]["shots"]:
        t0 = time.perf_counter()
        payload = json.dumps(shot, sort_keys=True)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
        artifact = out_dir / f"{shot['id']}_{digest}.json"

        # Cache hit check: skip work if this exact shot input hash already exists
        cached = artifact.exists()
        if not cached:
            artifact.write_text(json.dumps({
                "shot_id": shot["id"],
                "hash": digest,
                "duration_sec": shot["duration_sec"],
                "narration": shot["narration"],
                "visual_prompt": shot["visual_prompt"],
            }, indent=2), encoding="utf-8")

        _append_run_log(state["run_log_path"], {
            "stage": "generate_stage",
            "shot_id": shot["id"],
            "cache_hit": cached,
            "model": "stub_or_provider_model",
            "seed": None,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
            "cost_usd": 0.0,
        })

    return state


def assemble_node(state: PipelineState) -> PipelineState:
    t0 = time.perf_counter()
    out_dir = Path(state["outputs_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    assembled = out_dir / "v0_plan.json"
    assembled.write_text(json.dumps({
        "title": state["storyboard"]["title"],
        "shot_count": len(state["storyboard"]["shots"]),
        "status": "assembled_v0",
    }, indent=2), encoding="utf-8")

    _append_run_log(state["run_log_path"], {
        "stage": "assemble",
        "model": "assembler_v0",
        "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
        "cost_usd": 0.0,
        "output": str(assembled),
    })
    return {**state, "assembled_path": str(assembled)}


def build_graph():
    builder = StateGraph(PipelineState)
    builder.add_node("validate_storyboard", validate_storyboard_node)
    builder.add_node("generate_stage", generate_stage_node)
    builder.add_node("assemble", assemble_node)

    builder.add_edge(START, "validate_storyboard")
    builder.add_edge("validate_storyboard", "generate_stage")
    builder.add_edge("generate_stage", "assemble")
    builder.add_edge("assemble", END)
    return builder.compile()