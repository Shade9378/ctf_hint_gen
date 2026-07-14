import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from src.components.flag_checker import make_flag_checker
from src.components.llm.solution_builder import build_solution

from src.components.llm.controller import LLMController
from src.components.llm.hint_gen import LLMHintGenerator


StudentState = Union[Dict[str, Any], List[Dict[str, Any]]]


class LLMSystem:
    """
    Top-level LLM hint system.

    Responsibility:
    - Load existing solution file if available
    - If no solution exists, run controller to create one
    - Save sanitized solution only if solved
    - Generate all 4 hint levels from:
        student_state + solution + challenge_context

    student_state can be:
    - raw student logs
    - milestone matcher output
    """

    def __init__(
        self,
        *,
        model_client: Any,
        private_challenge_path: Union[str, Path],
        solution_path: Union[str, Path],
        max_steps: int = 30,
    ):
        self.model_client = model_client
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
        student_state: StudentState,
        challenge_context: str,
    ) -> Dict[str, Any]:
        """
        Main system entry point.

        Args:
            student_state:
                Either raw student logs or milestone matcher output.

            challenge_context:
                Public challenge description/context.
                Do NOT pass private flag here.

        Returns:
            dict containing solution, optional controller_result, and hint_result.
        """

        solution = self.load_solution()
        controller_result = None
        source = "existing_solution"

        if solution is None:
            controller_result = self.controller.run(
                challenge_context=challenge_context,
            )

            if controller_result.get("status") != "solved":
                return {
                    "status": "solver_failed",
                    "reason": controller_result.get("reason", "Controller did not solve the challenge."),
                    "student_state": student_state,
                    "solution": None,
                    "controller_result": controller_result,
                    "hint_result": None,
                }

            solution = build_solution(
                controller_result=controller_result,
            )

            self.save_solution(solution)
            source = "new_solution"

        hint_result = self.hint_generator.generate(
            student_state=student_state,
            solution=solution,
            challenge_context=challenge_context,
        )

        return {
            "status": "hint_generated",
            "source": source,
            "student_state": student_state,
            "solution": solution,
            "controller_result": controller_result,
            "hint_result": hint_result,
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