import json
from pathlib import Path


def read_log(log_path: str | Path) -> list[dict]:
    log_path = Path(log_path)

    entries = []

    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            entries.append(json.loads(line))

    return entries


def compact_log(entries: list[dict], max_entries: int = 30) -> list[dict]:
    """
    Keep only the most useful fields for state planning.
    """
    compact = []

    for entry in entries[-max_entries:]:
        compact.append({
            "time": entry.get("time"),
            "action_type": entry.get("action_type"),
            "cmd": entry.get("cmd"),
            "output": truncate(entry.get("output", "")),
            "exit_code": entry.get("exit_code"),
            "cwd": entry.get("cwd"),
            "system_selected": entry.get("system_selected"),
        })

    return compact


def truncate(text: str, max_chars: int = 2000) -> str:
    if len(text) <= max_chars:
        return text

    return text[:max_chars] + "\n...[truncated]..."