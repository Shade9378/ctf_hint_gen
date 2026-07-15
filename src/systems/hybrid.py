from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from src.common.utils import read_log
from src.components.llm.hint_gen import LLMHintGenerator
from src.components.rule_based.milestone_matcher import MilestoneMatcher


class HybridSystem:
    def __init__(
        self,
        *,
        model_client: Any,
        milestone_path: str | Path,
        solution_path: str | Path,
        hint_template_path: str | Path | None = None,
    ):
        self.model_client = model_client
        self.milestone_path = Path(milestone_path)
        self.solution_path = Path(solution_path)
        self.hint_template_path = (
            Path(hint_template_path)
            if hint_template_path is not None
            else None
        )

        self.milestone_model = self._load_json(self.milestone_path)
        self.matcher = MilestoneMatcher(self.milestone_model)
        self.hint_generator = LLMHintGenerator(model_client=model_client)

    def run(
        self,
        *,
        student_log_path: str | Path,
        challenge_context: str = "",
    ) -> Dict[str, Any]:
        student_logs = read_log(student_log_path)
        milestone_match = self.matcher.match(student_logs)

        hint_template = (
            self.hint_template_path
            if self.hint_template_path is not None
            else None
        )

        hint_result = self.hint_generator.generate(
            student_state=milestone_match,
            solution=self.solution_path,
            challenge_context=challenge_context,
            hint_template=hint_template,
        )

        return {
            "status": "solved" if milestone_match["solved"] else "hint_generated",
            "source": "hybrid_milestone_matcher_llm_hint_system",
            "student_log_path": str(student_log_path),
            "milestone_path": str(self.milestone_path),
            "solution_path": str(self.solution_path),
            "student_state": milestone_match,
            "solution": str(self.solution_path),
            "controller_result": None,
            "hint_result": hint_result,
        }

    def _load_json(self, path: Path) -> Dict[str, Any]:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
