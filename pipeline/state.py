from typing import Any, TypedDict


class PipelineState(TypedDict):
    storyboard_path: str
    storyboard: dict[str, Any]
    outputs_dir: str
    run_log_path: str
    assembled_path: str