from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from src.components.rule_based.hint_gen import HintGenerator
from src.components.rule_based.milestone_matcher import MilestoneMatcher

class RuleBasedSystem:
    def __init__(self, progress_model_path: str | Path, hint_template_path: str | Path):
        self.progress_model_path = Path(progress_model_path)
        self.hint_template_path = Path(hint_template_path)
        self.progress_model = self._load_json(self.progress_model_path)
        self.hint_templates = self._load_json(self.hint_template_path)

        self.matcher = MilestoneMatcher(self.progress_model)
        self.hint_generator = HintGenerator(self.hint_templates)

    def run(
        self,
        *,
        student_logs: List[Dict[str, Any]],
        challenge_context: str = "",
    ) -> Dict[str, Any]:
        match_result = self.matcher.match(student_logs)

        if match_result["solved"]:
            status = "solved"
            target_milestone = None
            hints = self.hint_generator.generate(None)
        else:
            status = "hint_generated"
            target_milestone = match_result["next_milestone"]
            hints = self.hint_generator.generate(target_milestone)

        return {
            "status": status,
            "source": "rule_based_output_milestone_system",
            "challenge_id": self.progress_model.get("challenge_id"),
            "student_state": {
                "solved": match_result["solved"],
                "success_match": match_result["success_match"],
                "milestones": match_result["milestones"],
                "next_milestone": target_milestone,
            },
            "solution": {
                "progress_model_path": str(self.progress_model_path),
                "policy": self.progress_model.get("policy", {}),
                "challenge_context": challenge_context,
            },
            "controller_result": None,
            "hint_result": {
                "status": "no_hint_needed" if target_milestone is None else "hints_generated",
                "target_milestone": None if target_milestone is None else target_milestone.get("milestone"),
                "hints": hints,
            },
        }

    def _load_json(self, path: Path) -> Dict[str, Any]:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
