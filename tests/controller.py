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


    result = controller.run(
        challenge_context="Fake challenge context for testing."
    )

    print("\nFinal result:")
    print(result)