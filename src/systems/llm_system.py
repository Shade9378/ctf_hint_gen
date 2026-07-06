import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from components.flag_checker import make_flag_checker
from components.llm.solution_builder import build_solution

from components.llm.controller import LLMController
from components.llm.hint_gen import LLMHintGenerator


class LLMSystem:
    """
    Top-level pure LLM hint system.

    Responsibility:
    - Load existing solution file
    - Run state planner
    - Decide whether to reuse existing solution or run solver
    - Run LLM controller only when needed
    - Handle controller status
    - Build/save solution only if solved
    - Generate all 4 hint levels
    """

    def __init__(
        self,
        *,
        model_client: Any,
        state_planner: Any,
        private_challenge_path: Union[str, Path],
        solution_path: Union[str, Path],
        max_steps: int = 30,
    ):
        self.model_client = model_client
        self.state_planner = state_planner
        self.private_challenge_path = Path(private_challenge_path)
        self.solution_path = Path(solution_path)

        flag_checker = make_flag_checker(self.private_challenge_path)

        self.controller = LLMController(
            model_client=model_client,
            max_steps=max_steps,
            flag_checker=flag_checker,
        )

        self.hint_generator = LLMHintGenerator(
            model_client=model_client,
        )

    def run(
        self,
        *,
        student_logs: List[Dict[str, Any]],
        challenge_context: str,
    ) -> Dict[str, Any]:
        """
        Main system entry point.

        Args:
            student_logs:
                Raw student command logs.

            challenge_context:
                Public challenge description/context.
                Do NOT pass private flag here.

        Returns:
            dict with status, student_state, solution, controller_result, hint_result.
        """

        existing_solution = self.load_solution()

        student_state = self.state_planner.plan(
            student_logs=student_logs,
            challenge_context=challenge_context,
            solution=existing_solution,
        )

        action = student_state.get("action")

        if action == "matched_existing_graph":
            return self.matched_existing_graph(
                student_state=student_state,
                existing_solution=existing_solution,
                challenge_context=challenge_context,
            )

        if action == "start_from_scratch":
            return self.create_solution_path(
                student_state=student_state,
                challenge_context=challenge_context,
                pass_student_state_to_controller=False,
            )

        if action == "continue_from_student_state":
            return self.create_solution_path(
                student_state=student_state,
                challenge_context=challenge_context,
                pass_student_state_to_controller=True,
            )

        return {
            "status": "failed",
            "reason": f"Unknown state planner action: {action}",
            "student_state": student_state,
            "solution": existing_solution,
            "controller_result": None,
            "hint_result": None,
        }

    def matched_existing_graph(
        self,
        *,
        student_state: Dict[str, Any],
        existing_solution: Optional[Dict[str, Any]],
        challenge_context: str,
    ) -> Dict[str, Any]:

        if existing_solution is None:
            return self.create_solution_path(
                student_state=student_state,
                challenge_context=challenge_context,
                pass_student_state_to_controller=True,
            )

        hint_result = self.hint_generator.generate(
            student_state=student_state,
            solution=existing_solution,
            challenge_context=challenge_context,
        )

        return {
            "status": "hint_generated",
            "source": "existing_solution",
            "student_state": student_state,
            "solution": existing_solution,
            "controller_result": None,
            "hint_result": hint_result,
        }

    def create_solution_path(
        self,
        *,
        student_state: Dict[str, Any],
        challenge_context: str,
        pass_student_state_to_controller: bool,
    ) -> Dict[str, Any]:

        controller_student_state: Optional[Dict[str, Any]]

        if pass_student_state_to_controller:
            controller_student_state = student_state
        else:
            controller_student_state = None

        controller_result = self.controller.run(
            challenge_context=challenge_context,
            student_state=controller_student_state,
        )

        return self.handle_controller_result(
            student_state=student_state,
            challenge_context=challenge_context,
            controller_result=controller_result,
        )

    def handle_controller_result(
        self,
        *,
        student_state: Dict[str, Any],
        challenge_context: str,
        controller_result: Dict[str, Any],
    ) -> Dict[str, Any]:

        status = controller_result.get("status")

        if status == "solved":
            solution = build_solution(
                student_state=student_state,
                controller_result=controller_result,
            )

            self.save_solution(solution)

            hint_result = self.hint_generator.generate(
                student_state=student_state,
                solution=solution,
                challenge_context=challenge_context,
            )

            return {
                "status": "hint_generated",
                "source": "new_solution",
                "student_state": student_state,
                "solution": solution,
                "controller_result": controller_result,
                "hint_result": hint_result,
            }

        if status == "failed":
            return {
                "status": "solver_failed",
                "reason": controller_result.get("reason", "Controller failed."),
                "student_state": student_state,
                "solution": None,
                "controller_result": controller_result,
                "hint_result": None,
            }

        if status == "stopped":
            return {
                "status": "solver_stopped",
                "reason": controller_result.get("reason", "Controller stopped."),
                "student_state": student_state,
                "solution": None,
                "controller_result": controller_result,
                "hint_result": None,
            }

        if status == "max_steps_reached":
            return {
                "status": "solver_max_steps_reached",
                "reason": controller_result.get("reason", "Controller reached max steps."),
                "student_state": student_state,
                "solution": None,
                "controller_result": controller_result,
                "hint_result": None,
            }

        return {
            "status": "solver_unknown_status",
            "reason": f"Unknown controller status: {status}",
            "student_state": student_state,
            "solution": None,
            "controller_result": controller_result,
            "hint_result": None,
        }

    def load_solution(self) -> Optional[Dict[str, Any]]:
        if not self.solution_path.exists():
            return None

        with self.solution_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def save_solution(self, solution: Dict[str, Any]) -> None:
        self.solution_path.parent.mkdir(parents=True, exist_ok=True)

        with self.solution_path.open("w", encoding="utf-8") as f:
            json.dump(solution, f, indent=2, ensure_ascii=False)