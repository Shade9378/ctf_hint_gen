from __future__ import annotations

import json
from pathlib import Path

from src.common.utils import read_log
from src.systems.rule_based_system import RuleBasedSystem


ROOT = Path(__file__).resolve().parents[1]


def write_test_log(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    entries = [
        {
            "time": "2026-07-09T12:00:00",
            "action_type": "student_command",
            "cmd": "ls -lh",
            "output": "-rw-r--r-- 1 ctf ctf 20M disk.img.gz",
            "exit_code": 0,
            "cwd": "/tmp/oni",
        },
        {
            "time": "2026-07-09T12:01:00",
            "action_type": "student_command",
            "cmd": "gunzip -k disk.img.gz && ls -lh",
            "output": "-rw-r--r-- 1 ctf ctf 100M disk.img",
            "exit_code": 0,
            "cwd": "/tmp/oni",
        },
        {
            "time": "2026-07-09T12:02:00",
            "action_type": "student_command",
            "cmd": "mmls disk.img",
            "output": "002: 0000206848 0000400000 0000193152 Linux (0x83)",
            "exit_code": 0,
            "cwd": "/tmp/oni",
        },
        {
            "time": "2026-07-09T12:03:00",
            "action_type": "student_command",
            "cmd": "fls -r -p -o 206848 disk.img | grep -i ssh",
            "output": "r/r 2345: root/.ssh/id_ed25519\nr/r 2346: root/.ssh/id_ed25519.pub",
            "exit_code": 0,
            "cwd": "/tmp/oni",
        },
        {
            "time": "2026-07-09T12:04:00",
            "action_type": "student_command",
            "cmd": "icat -o 206848 disk.img 2345 > key_file",
            "output": "",
            "exit_code": 0,
            "cwd": "/tmp/oni",
        },
        {
            "time": "2026-07-09T12:04:00",
            "action_type": "student_command",
            "cmd": "head key_file",
            "output": "-----BEGIN OPENSSH PRIVATE KEY-----",
            "exit_code": 0,
            "cwd": "/tmp/oni",
        },
    ]

    with path.open("w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


def print_json(title: str, data: dict) -> None:
    print(f"\n=== {title} ===")
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    log_path = ROOT / "data" / "logs" / "test_rule_based.jsonl"
    write_test_log(log_path)

    system = RuleBasedSystem(
        progress_model_path=ROOT
        / "data"
        / "challenges"
        / "private"
        / "operation_oni"
        / "solution_model.json",
        hint_template_path=ROOT / "data" / "hint_templates" / "rule_hint_templates.json",
    )

    student_logs = read_log(log_path)

    milestone_matcher_output = system.matcher.match(student_logs)
    print_json("milestone_matcher output", milestone_matcher_output)

    hint_gen_output = system.hint_generator.generate(
        milestone_matcher_output["next_milestone"]
    )
    print_json("hint_gen output", hint_gen_output)

    result = system.run(
        student_logs=student_logs,
        challenge_context=(
            "Operation Oni: Download this disk image, find the key, "
            "and log into the remote machine."
        ),
    )
    print_json("rule_based_system output", result)

    assert result["status"] == "hint_generated"
    assert result["student_state"]["next_milestone"]["milestone"] == "key_usable_for_ssh"
    assert "milestones" in result["student_state"]
    assert "next_milestone" in result["student_state"]
    assert "target_milestone" in result["hint_result"]

    hints = result["hint_result"]["hints"]
    assert set(hints.keys()) == {
        "level_1_conceptual",
        "level_2_observation",
        "level_3_method_tool",
        "level_4_bottom_out",
    }
    assert all(isinstance(value, str) for value in hints.values())

    serialized = json.dumps(result)
    assert "diagnostic" not in serialized
    assert "file_path" not in serialized
    assert "evidence_id" not in serialized
    assert "step" not in serialized
    assert "next_step" not in serialized
    assert "target_step" not in serialized

    print("\nrule_based_sys smoke test passed")