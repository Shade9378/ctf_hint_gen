import json
import shlex
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path


CONTAINER_NAME = "student_shell" # container file name should be an args
LOG_DIR = Path("data/logs")


def make_session_log_path() -> Path:
    """
    Create one new log file each time client_shell.py starts.

    Format:
    month-date-year_hour-minute-second.jsonl

    Example:
    06-29-2026_11-42-08.jsonl
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    filename = datetime.now().strftime("%m-%d-%Y_%H-%M-%S.jsonl")
    return LOG_DIR / filename

class DockerShellLogger:
    def __init__(self, container_name: str = CONTAINER_NAME):
        self.container_name = container_name
        self.cwd = "/challenge"
        self.log_path = make_session_log_path()

        self.write_log({
            "time": self.timestamp(),
            "id": str(uuid.uuid4()),
            "action_type": "system_start",
            "cmd": "",
            "output": f"Client shell started. Container={self.container_name}",
            "exit_code": 0,
            "cwd": self.cwd,
        })

    def timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def run_command(self, cmd: str) -> dict:
        action_id = str(uuid.uuid4())

        script = f"""
cd {shlex.quote(self.cwd)} 2>/dev/null || cd /challenge
{cmd}
rc=$?
printf '\\n__LOGGER_EXIT_CODE__:%s\\n' "$rc"
printf '__LOGGER_PWD__:%s\\n' "$PWD"
"""

        result = subprocess.run(
            ["docker", "exec", self.container_name, "bash", "-lc", script],
            capture_output=True,
            text=True,
        )

        raw_stdout = result.stdout
        stderr = result.stderr

        exit_code = None
        new_cwd = self.cwd

        output_lines = []
        for line in raw_stdout.splitlines():
            if line.startswith("__LOGGER_EXIT_CODE__:"):
                try:
                    exit_code = int(line.split(":", 1)[1])
                except ValueError:
                    exit_code = None
            elif line.startswith("__LOGGER_PWD__:"):
                new_cwd = line.split(":", 1)[1]
            else:
                output_lines.append(line)

        self.cwd = new_cwd

        output = "\n".join(output_lines)

        if stderr.strip():
            output = output + ("\n" if output else "") + stderr.strip()

        log_entry = {
            "time": self.timestamp(),
            "id": action_id,
            "action_type": "shell_command",
            "cmd": cmd,
            "output": output,
            "exit_code": exit_code,
            "cwd": self.cwd,
        }

        self.write_log(log_entry)
        return log_entry

    def write_log(self, entry: dict):
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def repl(self):
        print("Client shell started. Type commands. Type 'exit' to quit.")
        print(f"Logging to: {self.log_path}")

        while True:
            try:
                cmd = input(f"ctf:{self.cwd}$ ").strip()
            except EOFError:
                self.write_log({
                    "time": self.timestamp(),
                    "id": str(uuid.uuid4()),
                    "action_type": "system_exit",
                    "cmd": "",
                    "output": "Client shell exited with EOF.",
                    "exit_code": 0,
                    "cwd": self.cwd,
                })
                break

            if not cmd:
                continue

            if cmd in {"exit", "quit"}:
                self.write_log({
                    "time": self.timestamp(),
                    "id": str(uuid.uuid4()),
                    "action_type": "system_exit",
                    "cmd": cmd,
                    "output": "Client shell exited by user.",
                    "exit_code": 0,
                    "cwd": self.cwd,
                })
                print("Exiting client shell.")
                break

            parts = shlex.split(cmd)

            if parts and parts[0] == "hint":
                entry = self.handle_hint_request(cmd)
            else:
                entry = self.run_command(cmd)

            if entry["output"]:
                print(entry["output"])

    def handle_hint_request(self, cmd: str) -> dict:
        parts = shlex.split(cmd)

        system_requested = None
        system_type = "trad"  # default fallback

        if "--sys" in parts:
            sys_index = parts.index("--sys")

            if sys_index + 1 < len(parts):
                system_requested = parts[sys_index + 1]

                if system_requested in {"llm", "hybrid", "trad"}:
                    system_type = system_requested

        hint_text = (
            f"[debug] requested_system={system_requested or '(none)'}; "
            f"selected_system={system_type}"
        )

        log_entry = {
            "time": self.timestamp(),
            "id": str(uuid.uuid4()),
            "action_type": "hint_request",
            "cmd": cmd,
            "output": hint_text,
            "exit_code": 0,
            "cwd": self.cwd,
            "system_requested": system_requested,
            "system_selected": system_type,
        }

        self.write_log(log_entry)
        return log_entry


if __name__ == "__main__":
    shell = DockerShellLogger()
    shell.repl()