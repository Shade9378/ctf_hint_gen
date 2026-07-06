import json
from typing import Any, Dict, Optional

from common.utils import read_log, compact_log
from common.logger import Logger


class StatePlanner:
    def __init__(
        self,
        model_client: Any,
        log_folder: str = "llm/state_planner",
        max_log_entries: int = 30,
    ):
        self.model_client = model_client
        self.logger = Logger(folder_name=log_folder)
        self.max_log_entries = max_log_entries

    def analyze(
        self,
        *,
        student_log_path: str,
        challenge_context: str,
        solution_graph: Optional[dict] = None,
    ) -> Dict[str, Any]:
        entries = read_log(student_log_path)
        compact_log = compact_log(entries, max_entries=self.max_log_entries)

        prompt = self.build_prompt(
            challenge_context=challenge_context,
            compact_log=compact_log,
            solution_graph=solution_graph,
        )

        response = self.model_client.generate(prompt)

        self.logger.event(
            action_type="state_planner_response",
            output=response,
            cwd="/challenge",
        )

        return self.parse_response(response)

    def build_prompt(
        self,
        *,
        challenge_context: str,
        compact_log: list[dict],
        solution_graph: Optional[dict],
    ) -> str:
        return f"""
You are a CTF student-state planner.

Task: infer the student's current progress from the challenge context, optional solution graph, and command log.

Rules:

* Do not solve the challenge.
* Use only the provided context/log.
* Return valid JSON only.
* Choose exactly one action:

  * "matched_existing_graph": student matches a graph step.
  * "continue_from_student_state": student is on a valid path not clearly matched.
  * "start_from_scratch": log is irrelevant or unusable.

Judge:
* Are recent actions relevant?
* Is the path valid?
* What evidence has the student discovered?
* If a solution graph exists, which step is matched?

Return this exact JSON shape:

{
  "action": "matched_existing_graph | continue_from_student_state | start_from_scratch",
  "student_actions_relevant": true,
  "path_valid": true,
  "use_student_progress": true,
  "matched_step": null,
  "completed_work": [
    {
      "summary": "Brief summary of what the student has done correctly.",
      "evidence": "Concrete command/output evidence from the log."
    }
  ],
  "objective_summary": "Where the solver should continue from.",
  "suggested_next_step": "The next likely useful step.",
  "confidence": "low | medium | high"
}

- completed_work should include only correct/relevant progress.
- Do not include failed commands unless they directly prove something useful.
- evidence must quote or summarize actual command/output from the log.
- If no useful progress exists, completed_work should be [].
- If action is start_from_scratch, use_student_progress should be false.
- If action is matched_existing_graph, matched_step must not be null.
- If action is continue_from_student_state, matched_step should usually be null.

Challenge context:
{challenge_context}

Current solution graph, if available:
{json.dumps(solution_graph, indent=2)}

Student log:
{json.dumps(compact_log, indent=2)}

Return only JSON.
""".strip()

    def parse_response(self, response: str) -> Dict[str, Any]:
        if response is None or not response.strip():
            return {
                "action": "error",
                "reason": "State planner returned empty response.",
            }

        try:
            parsed = json.loads(response.strip())
        except json.JSONDecodeError as e:
            return {
                "action": "error",
                "reason": f"State planner returned invalid JSON: {e}",
                "raw_response": response,
            }

        return parsed
    