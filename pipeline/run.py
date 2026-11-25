import argparse
from pipeline.graph import build_graph


def main() -> None:
    parser = argparse.ArgumentParser(description="Run minimal agentic pipeline")
    parser.add_argument("--storyboard", default="storyboard.json")
    parser.add_argument("--outputs", default="outputs")
    parser.add_argument("--runs", default="runs.jsonl")
    args = parser.parse_args()

    app = build_graph()
    result = app.invoke({
        "storyboard_path": args.storyboard,
        "storyboard": {},
        "outputs_dir": args.outputs,
        "run_log_path": args.runs,
        "assembled_path": "",
    })
    print(f"Done. Output: {result['assembled_path']}")


if __name__ == "__main__":
    main()