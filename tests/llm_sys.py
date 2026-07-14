import json
from pathlib import Path

from src.systems.llm_system import LLMSystem

# If running with: python tests/llm_sys.py
from fake_model import FakeModelClient

# If running with: python -m tests.llm_sys
# from tests.fake_model import FakeModelClient


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
                "student_state_format": "raw_log",
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
        private_challenge_path=private_path,
        solution_path=solution_path,
        max_steps=5,
    )

    result = system.run(
        student_state=[],
        challenge_context="Public fake challenge context.",
    )

    print("\nLLMSystem result:")
    print(json.dumps(result, indent=2))

    print("\nSaved solution:")
    with solution_path.open("r", encoding="utf-8") as f:
        print(f.read())