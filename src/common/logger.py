import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


LOG_ROOT = Path("data/logs")


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_session_log_path(folder_name: str) -> Path:
    """
    Create one new log file inside data/logs/<folder_name>/.

    Example:
    data/logs/student/06-29-2026_11-42-08.jsonl
    data/logs/llm/06-29-2026_11-42-08.jsonl
    """
    log_dir = LOG_ROOT / folder_name
    log_dir.mkdir(parents=True, exist_ok=True)

    filename = datetime.now().strftime("%m-%d-%Y_%H-%M-%S.jsonl")
    return log_dir / filename


class Logger:
    def __init__(self, folder_name: str, log_path: Path | None = None):
        self.folder_name = folder_name
        self.log_path = log_path or make_session_log_path(folder_name)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, entry: dict) -> dict:
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

    def event(
        self,
        *,
        action_type: str,
        cmd: str = "",
        output: str = "",
        exit_code: int | None = 0,
        cwd: str = "/challenge",
        **extra,
    ) -> dict:
        entry = {
            "time": timestamp(),
            "id": str(uuid.uuid4()),
            "action_type": action_type,
            "cmd": cmd,
            "output": output,
            "exit_code": exit_code,
            "cwd": cwd,
        }

        entry.update(extra)
        return self.write(entry)