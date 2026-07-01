import shlex
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory

from common.executor import DockerExecutor
from common.logger import Logger


CONTAINER_NAME = "student_shell"


class StudentShell:
    def __init__(self, container_name: str = CONTAINER_NAME):
        self.shell = DockerExecutor(container_name=container_name)
        self.logger = Logger(folder_name="student")

        self.logger.event(
            action_type="system_start",
            output=f"Client shell started. Container={container_name}",
            cwd=self.shell.cwd,
            container=container_name,
        )

    def run_command(self, cmd: str) -> dict:
        result = self.shell.run(cmd)

        return self.logger.event(
            action_type="shell_command",
            cmd=result["cmd"],
            output=result["output"],
            exit_code=result["exit_code"],
            cwd=result["cwd"],
            container=result["container"],
        )

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

        return self.logger.event(
            action_type="hint_request",
            cmd=cmd,
            output=hint_text,
            exit_code=0,
            cwd=self.shell.cwd,
            system_requested=system_requested,
            system_selected=system_type,
        )

    def repl(self):
        print("Client shell started. Type commands. Type 'exit' to quit.")
        print(f"Logging to: {self.logger.log_path}")

        history_path = Path("data/logs/.client_shell_history")
        history_path.parent.mkdir(parents=True, exist_ok=True)

        session = PromptSession(
            history=FileHistory(str(history_path))
        )

        while True:
            try:
                cmd = session.prompt(f"ctf:{self.shell.cwd}$ ").strip()
            except EOFError:
                self.logger.event(
                    action_type="system_exit",
                    output="Client shell exited with EOF.",
                    exit_code=0,
                    cwd=self.shell.cwd,
                )
                break

            if not cmd:
                continue

            if cmd in {"exit", "quit"}:
                self.logger.event(
                    action_type="system_exit",
                    cmd=cmd,
                    output="Client shell exited by user.",
                    exit_code=0,
                    cwd=self.shell.cwd,
                )
                print("Exiting client shell.")
                break

            try:
                parts = shlex.split(cmd)
            except ValueError as e:
                print(f"Parse error: {e}")
                continue

            if parts and parts[0] == "hint":
                entry = self.handle_hint_request(cmd)
            else:
                entry = self.run_command(cmd)

            if entry["output"]:
                print(entry["output"])


if __name__ == "__main__":
    shell = StudentShell()
    shell.repl()