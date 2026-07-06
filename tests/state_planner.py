import json
from pathlib import Path

from src.components.llm.state_planner import StatePlanner
from tests.fake_model import FakeModelClient


if __name__ == "__main__":
    log_path = Path("data/logs/test_student_log.jsonl")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    fake_logs = [
        {
            "time": "2026-07-06T00:00:00Z",
            "action_type": "student_command",
            "cmd": "ls -la",
            "output": "total 8\n-rw-r--r-- 1 user user 123 challenge.txt\n-rwxr-xr-x 1 user user 456 vuln",
            "exit_code": 0,
            "cwd": "/challenge",
        },
        {
            "time": "2026-07-06T00:00:01Z",
            "action_type": "student_command",
            "cmd": "file vuln",
            "output": "vuln: ELF 64-bit LSB executable",
            "exit_code": 0,
            "cwd": "/challenge",
        },
    ]

    with log_path.open("w", encoding="utf-8") as f:
        for entry in fake_logs:
            f.write(json.dumps(entry) + "\n")

    fake_model = FakeModelClient(
        responses=[
            {
                "action": "continue_from_student_state",
                "student_actions_relevant": True,
                "path_valid": True,
                "use_student_progress": True,
                "matched_step": None,
                "completed_work": [
                    {
                        "summary": "Student listed files and identified the binary.",
                        "evidence": "Commands included ls -la and file vuln; output showed an ELF executable.",
                    }
                ],
                "objective_summary": "Continue from binary inspection.",
                "suggested_next_step": "Inspect the binary behavior or protections.",
                "confidence": "medium",
            }
        ]
    )

    planner = StatePlanner(
        model_client=fake_model,
        max_log_entries=30,
    )

    result = planner.analyze(
        student_log_path=str(log_path),
        challenge_context="Fake binary exploitation challenge.",
        solution_graph=None,
    )

    print("\nState planner result:")
    print(json.dumps(result, indent=2))