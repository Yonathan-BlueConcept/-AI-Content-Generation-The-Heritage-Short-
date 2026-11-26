
import unittest
from pathlib import Path
from unittest.mock import patch, call

from pipeline.run import run_pipeline


FIXTURE = Path("tests/fixtures/storyboard.test.json")


class TestPipelineOrchestration(unittest.TestCase):

    def test_pipeline_executes_stages_in_correct_order(self):
        execution_order = []

        def keyframes(*args, **kwargs):
            execution_order.append("keyframes")

        def videos(*args, **kwargs):
            execution_order.append("videos")

        def music(*args, **kwargs):
            execution_order.append("music")

        def narration(*args, **kwargs):
            execution_order.append("narration")

        def assembly(*args, **kwargs):
            execution_order.append("assembly")

        with (
            patch("pipeline.run.generate_keyframes", side_effect=keyframes),
            patch("pipeline.run.generate_videos", side_effect=videos),
            patch("pipeline.run.generate_soundtrack", side_effect=music),
            patch("pipeline.run.generate_narration", side_effect=narration),
            patch("pipeline.run.assemble_film", side_effect=assembly),
        ):
            run_pipeline(
                storyboard_path=FIXTURE,
                duration_range=(1, 90),
            )

        self.assertEqual(execution_order[0], "keyframes")
        self.assertEqual(execution_order[1], "videos")
        self.assertEqual(execution_order[-1], "assembly")

        self.assertCountEqual(
            execution_order[2:4],
            ["music", "narration"],
        )

    def test_video_failure_stops_pipeline(self):
        with (
            patch("pipeline.run.generate_keyframes"),
            patch(
                "pipeline.run.generate_videos",
                side_effect=RuntimeError("Video generation failed"),
            ),
            patch("pipeline.run.generate_soundtrack") as music,
            patch("pipeline.run.generate_narration") as narration,
            patch("pipeline.run.assemble_film") as assembly,
        ):
            with self.assertRaises(RuntimeError):
                run_pipeline(
                    storyboard_path=FIXTURE,
                    duration_range=(1, 90),
                )

        music.assert_not_called()
        narration.assert_not_called()
        assembly.assert_not_called()

    def test_music_failure_prevents_assembly(self):
        with (
            patch("pipeline.run.generate_keyframes"),
            patch("pipeline.run.generate_videos"),
            patch(
                "pipeline.run.generate_soundtrack",
                side_effect=RuntimeError("Music generation failed"),
            ),
            patch("pipeline.run.generate_narration"),
            patch("pipeline.run.assemble_film") as assembly,
        ):
            with self.assertRaises(RuntimeError):
                run_pipeline(
                    storyboard_path=FIXTURE,
                    duration_range=(1, 90),
                )

        assembly.assert_not_called()

    def test_narration_failure_prevents_assembly(self):
        with (
            patch("pipeline.run.generate_keyframes"),
            patch("pipeline.run.generate_videos"),
            patch("pipeline.run.generate_soundtrack"),
            patch(
                "pipeline.run.generate_narration",
                side_effect=RuntimeError("Narration generation failed"),
            ),
            patch("pipeline.run.assemble_film") as assembly,
        ):
            with self.assertRaises(RuntimeError):
                run_pipeline(
                    storyboard_path=FIXTURE,
                    duration_range=(1, 90),
                )

        assembly.assert_not_called()


def test_music_and_narration_run_in_parallel(self):
    import threading

    barrier = threading.Barrier(2, timeout=3)

    def wait_for_other_stage(*args, **kwargs):
        barrier.wait()

    with (
        patch("pipeline.run.generate_keyframes"),
        patch("pipeline.run.generate_videos"),
        patch(
            "pipeline.run.generate_soundtrack",
            side_effect=wait_for_other_stage,
        ),
        patch(
            "pipeline.run.generate_narration",
            side_effect=wait_for_other_stage,
        ),
        patch("pipeline.run.assemble_film") as assembly,
    ):
        run_pipeline(
            storyboard_path=FIXTURE,
            duration_range=(1, 90),
        )

    assembly.assert_called_once()


if __name__ == "__main__":
    unittest.main()
