from src.components.llm.controller import LLMController
from tests.fake_model import FakeModelClient


if __name__ == "__main__":
    fake_model = FakeModelClient(
        responses=[
            {
                "action": "run_command",
                "cmd": "ls -la",
                "summary": "Inspect the challenge directory.",
            },
            {
                "action": "run_command",
                "cmd": "pwd",
                "summary": "Check current directory.",
            },
            {
                "action": "stop",
                "reason": "Fake test completed.",
            },
        ]
    )

    controller = LLMController(
        model_client=fake_model,
        container_name="llm_shell",
        max_steps=5,
    )

    student_state = {
        "action": "continue_from_student_state",
        "student_actions_relevant": True,
        "path_valid": True,
        "use_student_progress": True,
        "matched_step": None,
        "completed_work": [
            {
                "summary": "Student already listed the challenge files.",
                "evidence": "Student ran ls and saw the challenge artifacts.",
            }
        ],
        "objective_summary": "Continue from basic file inspection.",
        "suggested_next_step": "Inspect the available files more closely.",
        "confidence": "medium",
    }

    result = controller.run(
        challenge_context="Fake challenge context for testing.",
        student_state=student_state,
    )

    print("\nFinal result:")
    print(result)