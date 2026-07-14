from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class MilestoneMatch:
    milestone: str
    reached: bool

    input_evidence: Optional[str] = None
    output_evidence: Optional[str] = None

    matched_source: Optional[str] = None
    matched_text: Optional[str] = None
    entry_index: Optional[int] = None
    cmd: Optional[str] = None


class MilestoneMatcher:
    OUTPUT_FIELDS = ("output", "stdout", "stderr")

    def __init__(self, progress_model: Dict[str, Any]):
        self.progress_model = progress_model
        self.milestones: List[Dict[str, Any]] = progress_model.get("milestones", [])
        self.success_evidence: Optional[str] = progress_model.get("success_evidence")

    def match(self, student_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        milestone_matches: List[MilestoneMatch] = []

        for milestone in self.milestones:
            milestone_matches.append(self._match_milestone(milestone, student_logs))

        success_match = None
        solved = False

        if self.success_evidence:
            success_match = self._search_outputs(self.success_evidence, student_logs)
            solved = success_match is not None

        next_milestone = None
        if not solved:
            for milestone, match in zip(self.milestones, milestone_matches):
                if not match.reached:
                    next_milestone = milestone
                    break

        return {
            "solved": solved,
            "success_match": success_match,
            "milestones": [self._milestone_match_to_dict(m) for m in milestone_matches],
            "next_milestone": next_milestone,
        }

    def _match_milestone(
        self,
        milestone: Dict[str, Any],
        student_logs: List[Dict[str, Any]],
    ) -> MilestoneMatch:
        milestone_name = milestone["milestone"]

        input_pattern = milestone.get("input_evidence")
        output_pattern = milestone.get("output_evidence", milestone.get("evidence"))

        if input_pattern:
            input_result = self._search_inputs(input_pattern, student_logs)
            if input_result is not None:
                return MilestoneMatch(
                    milestone=milestone_name,
                    reached=True,
                    input_evidence=input_pattern,
                    output_evidence=output_pattern,
                    matched_source="input",
                    matched_text=input_result["matched_text"],
                    entry_index=input_result["entry_index"],
                    cmd=input_result.get("cmd"),
                )

        if output_pattern:
            output_result = self._search_outputs(output_pattern, student_logs)
            if output_result is not None:
                return MilestoneMatch(
                    milestone=milestone_name,
                    reached=True,
                    input_evidence=input_pattern,
                    output_evidence=output_pattern,
                    matched_source="output",
                    matched_text=output_result["matched_text"],
                    entry_index=output_result["entry_index"],
                    cmd=output_result.get("cmd"),
                )

        return MilestoneMatch(
            milestone=milestone_name,
            reached=False,
            input_evidence=input_pattern,
            output_evidence=output_pattern,
        )

    def _search_inputs(
        self,
        pattern: str,
        student_logs: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        if not pattern:
            return None

        regex = re.compile(pattern, flags=re.IGNORECASE | re.MULTILINE)

        for idx, entry in enumerate(student_logs):
            cmd = entry.get("cmd")
            if cmd is None:
                continue
            if not isinstance(cmd, str):
                cmd = str(cmd)

            match = regex.search(cmd)
            if match:
                return {
                    "entry_index": idx,
                    "cmd": cmd,
                    "matched_text": match.group(0),
                }

        return None

    def _search_outputs(
        self,
        pattern: str,
        student_logs: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        if not pattern:
            return None

        regex = re.compile(pattern, flags=re.IGNORECASE | re.MULTILINE)

        for idx, entry in enumerate(student_logs):
            visible_output = self._visible_output(entry)
            if not visible_output:
                continue

            match = regex.search(visible_output)
            if match:
                return {
                    "entry_index": idx,
                    "cmd": entry.get("cmd"),
                    "matched_text": match.group(0),
                }

        return None

    def _visible_output(self, entry: Dict[str, Any]) -> str:
        parts: List[str] = []

        for field in self.OUTPUT_FIELDS:
            value = entry.get(field)
            if value is None:
                continue
            if not isinstance(value, str):
                value = str(value)
            parts.append(value)

        return "\n".join(parts)

    def _milestone_match_to_dict(self, match: MilestoneMatch) -> Dict[str, Any]:
        return {
            "milestone": match.milestone,
            "reached": match.reached,
            "input_evidence": match.input_evidence,
            "output_evidence": match.output_evidence,
            "matched_source": match.matched_source,
            "matched_text": match.matched_text,
            "entry_index": match.entry_index,
            "cmd": match.cmd,
        }