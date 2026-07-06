import json
from typing import Any, Callable, Dict, List, Optional

from src.common.executor import DockerExecutor
from src.common.logger import Logger

from src.common.utils import truncate

import shlex

class LLMController:
    """
    Controller for the LLM solver.

    Flow:
        1. Build prompt from challenge context + command history
        2. Ask LLM for next structured action
        3. Parse the action JSON
        4. Execute commands inside llm_shell using DockerExecutor
        5. Log LLM responses, commands, outputs, and flag checks
        6. Repeat until solved, stopped, or max_steps reached
    """

    def __init__(
        self,
        model_client: Any,
        container_name: str = "llm_shell",
        log_folder: str = "llm/solver",
        max_steps: int = 30,
        flag_checker: Optional[Callable[[str], bool]] = None,
    ):
        """
        Args:
            model_client:
                Any object with a .generate(prompt: str) -> str method.

            container_name:
                Docker container used by the LLM solver.

            log_folder:
                Folder under data/logs/ where LLM logs are stored.

            max_steps:
                Maximum number of LLM actions before stopping.

            flag_checker:
                Optional function that takes candidate flag string and returns True/False.
                Example:
                    def checker(flag: str) -> bool:
                        return flag == real_flag
        """
        self.model_client = model_client
        self.executor = DockerExecutor(container_name=container_name)
        self.logger = Logger(folder_name=log_folder)
        self.max_steps = max_steps
        self.flag_checker = flag_checker

        self.history: List[Dict[str, Any]] = []

    def run(self, challenge_context: str, student_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Main solving loop.

        Returns:
            {
                "status": "solved" | "stopped" | "failed" | "max_steps_reached",
                "flag": "... optional ...",
                "reason": "... optional ..."
            }
        """
        self.logger.event(
            action_type="system_start",
            output=f"LLM controller started. Container={self.executor.container_name}",
            cwd=self.executor.cwd,
            container=self.executor.container_name,
            max_steps=self.max_steps,
        )

        for step in range(1, self.max_steps + 1):
            prompt = self.build_prompt(challenge_context=challenge_context, student_state=student_state)

            llm_response = self.model_client.generate(prompt)

            self.logger.event(
                action_type="llm_response",
                output=llm_response,
                cwd=self.executor.cwd,
                step=step,
            )

            action = self.parse_response(llm_response)

            if action["action"] == "error":
                self.logger.event(
                    action_type="llm_error",
                    output=action["reason"],
                    exit_code=1,
                    cwd=self.executor.cwd,
                    step=step,
                )

                return {
                    "status": "failed",
                    "reason": action["reason"],
                    "history": self.history.copy()
                }

            if action["action"] == "run_command":
                result = self.handle_run_command(action, step)
                self.history.append(result)
                continue

            if action["action"] == "submit_flag":
                return self.handle_submit_flag(action, step)

            if action["action"] == "stop":
                reason = action.get("reason", "LLM chose to stop.")

                self.logger.event(
                    action_type="llm_stop",
                    output=reason,
                    cwd=self.executor.cwd,
                    step=step,
                )

                return {
                    "status": "stopped",
                    "reason": reason,
                    "history": self.history.copy()
                }

            self.logger.event(
                action_type="llm_error",
                output=f"Unknown action: {action}",
                exit_code=1,
                cwd=self.executor.cwd,
                step=step,
            )

            return {
                "status": "failed",
                "reason": f"Unknown action: {action}",
                "history": self.history.copy()
            }

        self.logger.event(
            action_type="max_steps_reached",
            output=f"Stopped after reaching max_steps={self.max_steps}.",
            exit_code=1,
            cwd=self.executor.cwd,
        )

        return {
            "status": "max_steps_reached",
            "reason": f"Stopped after reaching max_steps={self.max_steps}.",
            "history": self.history.copy()
        }

    def handle_run_command(self, action: Dict[str, Any], step: int) -> Dict[str, Any]:
        cmd = action.get("cmd", "").strip()
        summary = action.get("summary", "")

        if not cmd:
            result = {
                "step": step,
                "action": "run_command",
                "cmd": cmd,
                "output": "Rejected empty command.",
                "exit_code": 1,
                "cwd": self.executor.cwd,
                "summary": summary,
            }

            self.logger.event(
                action_type="llm_command_rejected",
                cmd=cmd,
                output="Rejected empty command.",
                exit_code=1,
                cwd=self.executor.cwd,
                step=step,
                summary=summary,
            )

            return result

        allowed, reason = self.validate_command(cmd)

        if not allowed:
            result = {
                "step": step,
                "action": "run_command",
                "cmd": cmd,
                "output": f"Command rejected: {reason}",
                "exit_code": 1,
                "cwd": self.executor.cwd,
                "summary": summary,
            }

            self.logger.event(
                action_type="llm_command_rejected",
                cmd=cmd,
                output=f"Command rejected: {reason}",
                exit_code=1,
                cwd=self.executor.cwd,
                step=step,
                summary=summary,
            )

            return result

        result = self.executor.run(cmd)

        self.logger.event(
            action_type="llm_command",
            cmd=result["cmd"],
            output=result["output"],
            exit_code=result["exit_code"],
            cwd=result["cwd"],
            container=result["container"],
            step=step,
            summary=summary,
        )

        return {
            "step": step,
            "action": "run_command",
            "cmd": result["cmd"],
            "output": truncate(result["output"]),
            "exit_code": result["exit_code"],
            "cwd": result["cwd"],
            "summary": summary,
        }

    def handle_submit_flag(self, action: Dict[str, Any], step: int) -> Dict[str, Any]:
        candidate_flag = action.get("flag", "").strip()

        if not candidate_flag:
            self.logger.event(
                action_type="flag_submission",
                output="Rejected empty flag submission.",
                exit_code=1,
                cwd=self.executor.cwd,
                step=step,
            )

            return {
                "status": "failed",
                "reason": "LLM submitted an empty flag.",
                "history": self.history.copy()
            }

        if self.flag_checker is None:
            self.logger.event(
                action_type="flag_submission",
                output=f"Candidate flag submitted but no checker is attached: {candidate_flag}",
                exit_code=0,
                cwd=self.executor.cwd,
                step=step,
            )

            return {
                "status": "stopped",
                "flag": candidate_flag,
                "reason": "Candidate flag found, but no flag checker is attached.",
                "history": self.history.copy()
            }

        is_correct = self.flag_checker(candidate_flag)

        self.logger.event(
            action_type="flag_check",
            output=f"Candidate flag: {candidate_flag}; correct={is_correct}",
            exit_code=0 if is_correct else 1,
            cwd=self.executor.cwd,
            step=step,
        )

        if is_correct:
            return {
                "status": "solved",
                "flag": candidate_flag,
                "history": self.history.copy()
            }

        self.history.append({
            "step": step,
            "action": "submit_flag",
            "flag": candidate_flag,
            "output": "Flag checker says incorrect.",
            "exit_code": 1,
            "cwd": self.executor.cwd,
        })

        return {
            "status": "failed",
            "flag": candidate_flag,
            "reason": "Flag checker says incorrect.",
            "history": self.history.copy()
        }

    def build_prompt(self, challenge_context: str, student_state: Optional[Dict[str, Any]] = None) -> str:
        recent_history = self.history[-10:]

        student_state_exp = ""

        if student_state:
            student_state_exp = """
        Before choosing your next action, use the student_state as the starting checkpoint.

        student_state fields:
        - completed_work: correct/relevant work already done by the student, with evidence.
        - objective_summary: where the solver should continue from.
        - suggested_next_step: likely next useful solving step.
        - confidence: planner confidence: low, medium, or high.

        Do not redo completed_work unless verification is necessary.
        """

        return f"""
        You are now solving a CTF challenge inside a Docker sandbox.

        You are allowed to inspect files, run commands, write small scripts, and analyze outputs.
        You must solve the challenge step by step.

        You will be provided:
        - Challenge description
        - Student progress state (if available) 

        {student_state_exp}

        Important rules:
        - Return only valid JSON.
        - Do not return markdown.
        - Do not include extra text outside the JSON.
        - Do not ask the user questions.
        - Do not claim the flag is correct unless you submit it using the submit_flag action.
        - If you need to inspect something, use run_command.
        - If you find a candidate flag, use submit_flag.
        - If you are stuck, use stop.

        Available actions:

        1. Run a shell command:

        {{
        "action": "run_command",
        "cmd": "ls -la",
        "summary": "Brief reason for this command."
        }}

        2. Submit a candidate flag:

        {{
        "action": "submit_flag",
        "flag": "picoCTF{{...}}",
        "summary": "Brief reason this looks like the flag."
        }}

        3. Stop:

        {{
        "action": "stop",
        "reason": "Brief reason for stopping."
        }}

        Challenge context:
        {challenge_context}

        Student progress state:
        {json.dumps(student_state, indent=2) if student_state else "student progress state not available"}

        Your recent command history:
        {json.dumps(recent_history, indent=2)}

        Return the next action as JSON only.
        """.strip()

    def parse_response(self, llm_response: str) -> Dict[str, Any]:
        if llm_response is None:
            return {
                "action": "error",
                "reason": "LLM response was None.",
            }

        text = llm_response.strip()

        if not text:
            return {
                "action": "error",
                "reason": "LLM returned empty response.",
            }

        try:
            action = json.loads(text)
        except json.JSONDecodeError as e:
            return {
                "action": "error",
                "reason": f"LLM returned invalid JSON: {e}",
            }

        if not isinstance(action, dict):
            return {
                "action": "error",
                "reason": "LLM JSON response was not an object.",
            }

        if "action" not in action:
            return {
                "action": "error",
                "reason": "LLM JSON missing required field: action.",
            }

        valid_actions = {"run_command", "submit_flag", "stop"}

        if action["action"] not in valid_actions:
            return {
                "action": "error",
                "reason": f"Invalid action: {action['action']}",
            }

        if action["action"] == "run_command" and "cmd" not in action:
            return {
                "action": "error",
                "reason": "run_command action missing required field: cmd.",
            }

        if action["action"] == "submit_flag" and "flag" not in action:
            return {
                "action": "error",
                "reason": "submit_flag action missing required field: flag.",
            }

        return action

    def validate_command(self, cmd: str) -> tuple:
        blocked_exact = {
            "exit",
            "logout",
            "reboot",
            "shutdown",
            "poweroff",
        }

        blocked_programs = {
            "docker",
            "sudo",
            "su",
            "ssh",
            "scp",
            "bash",
            "sh",
            "zsh",
            "fish",
            "vim",
            "vi",
            "nano",
            "emacs",
            "less",
            "more",
            "top",
            "htop",
            "watch",
        }

        stripped = cmd.strip()

        if stripped in blocked_exact:
            return False, "Command exits or controls the environment."

        try:
            parts = shlex.split(stripped)
        except ValueError as e:
            return False, f"Could not parse command: {e}"

        if not parts:
            return False, "Empty command."

        executable = parts[0]

        if executable in blocked_programs:
            return False, f"Interactive or unsafe command blocked: {executable}"

        if executable == "nc" and "-l" in parts:
            return False, "Listening netcat commands are blocked."

        if executable in {"python", "python3"} and "-i" in parts:
            return False, "Interactive Python is blocked."

        return True, "ok"