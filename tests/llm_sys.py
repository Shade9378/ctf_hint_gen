import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.systems.llm_system import LLMSystem
from tests.fake_model import FakeModelClient


class FakeStatePlanner:
    def plan(
        self,
        *,
        student_logs: List[Dict[str, Any]],
        challenge_context: str,
        solution: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        return {
            "action": "start_from_scratch",
            "student_actions_relevant": False,
            "path_valid": True,
            "use_student_progress": False,
            "matched_step": None,
            "completed_work": [],
            "objective_summary": "Start from initial challenge inspection.",
            "suggested_next_step": "Begin by inspecting the challenge files.",
            "confidence": "medium",
        }


if __name__ == "__main__":
    private_path = Path("data/challenges/private/test_challenge.json")
    solution_path = Path("data/solutions/test_solution.json")

    private_path.parent.mkdir(parents=True, exist_ok=True)
    solution_path.parent.mkdir(parents=True, exist_ok=True)

    with private_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "flag": "picoCTF{fake_flag}",
                "description": "Private fake challenge data.",
            },
            f,
            indent=2,
        )

    if solution_path.exists():
        solution_path.unlink()

    fake_model = FakeModelClient(
        responses=[
            {
                "action": "submit_flag",
                "flag": "picoCTF{fake_flag}",
                "summary": "Fake model directly submits the known test flag.",
            },
            {
                "matched_step": None,
                "next_step": "Inspect the challenge files.",
                "student_state_summary": "The student has not made meaningful progress yet.",
                "hints": {
                    "level_1_conceptual": "Start by understanding what kind of artifact the challenge gives you.",
                    "level_2_observation": "Pay attention to file names, formats, and any unusual metadata.",
                    "level_3_method_tool": "Use basic file inspection methods before trying to solve the challenge.",
                    "level_4_bottom_out": "List the files in the challenge directory and identify their types.",
                },
                "leakage_risk": "low",
                "leakage_notes": "The hints only guide initial inspection and do not reveal the flag.",
            },
        ]
    )

    system = LLMSystem(
        model_client=fake_model,
        state_planner=FakeStatePlanner(),
        private_challenge_path=private_path,
        solution_path=solution_path,
        max_steps=5,
    )

    result = system.run(
        student_logs=[],
        challenge_context="Public fake challenge context.",
    )

    print("\nLLMSystem result:")
    print(json.dumps(result, indent=2))

    print("\nSaved solution:")
    with solution_path.open("r", encoding="utf-8") as f:
        print(f.read())