import json
from pathlib import Path
from typing import Any, Dict, List, Union


JsonInput = Union[Dict[str, Any], List[Dict[str, Any]], str, Path]


class LLMMilestoneGenerator:
    """
    Generate a rule-based milestone model from an existing solution artifact.

    The generated model is intended to match the shape consumed by
    MilestoneMatcher, for example data/challenges/private/operation_oni/
    solution_model.json.
    """

    REQUIRED_TOP_LEVEL_FIELDS = {
        "challenge_id",
        "challenge_name",
        "success_evidence",
        "milestones",
    }

    REQUIRED_MILESTONE_FIELDS = {
        "milestone",
        "goal",
        "concept",
        "tool_used",
        "observation",
        "next_cmd",
    }

    def __init__(self, model_client: Any):
        self.model_client = model_client

    def generate(
        self,
        *,
        solution: JsonInput,
        challenge_id: str | None = None,
        challenge_name: str | None = None,
        challenge_context: str = "",
    ) -> Dict[str, Any]:
        solution_data = self.load_json_input(solution)

        prompt = self.build_prompt(
            solution=solution_data,
            challenge_id=challenge_id,
            challenge_name=challenge_name,
            challenge_context=challenge_context,
        )

        llm_response = self.model_client.generate(prompt)
        milestone_model = self.parse_response(llm_response)
        return self.validate_model(milestone_model)

    def generate_to_file(
        self,
        *,
        solution: JsonInput,
        output_path: str | Path,
        challenge_id: str | None = None,
        challenge_name: str | None = None,
        challenge_context: str = "",
    ) -> Dict[str, Any]:
        milestone_model = self.generate(
            solution=solution,
            challenge_id=challenge_id,
            challenge_name=challenge_name,
            challenge_context=challenge_context,
        )

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8") as f:
            json.dump(milestone_model, f, indent=2, ensure_ascii=False)

        return milestone_model

    def load_json_input(self, value: JsonInput) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        if isinstance(value, (dict, list)):
            return value

        path = Path(value)

        if path.suffix == ".jsonl":
            entries = []
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entries.append(json.loads(line))
            return entries

        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def build_prompt(
        self,
        *,
        solution: Union[Dict[str, Any], List[Dict[str, Any]]],
        challenge_id: str | None,
        challenge_name: str | None,
        challenge_context: str,
    ) -> str:
        return f"""
You are generating a rule-based CTF progress model from a known solution.

Your job is to convert the solution into ordered milestones that can be detected
from student command logs. The output will be used by a regex-based milestone
matcher, so every evidence field must be a valid Python regular expression.

Input evidence vs output evidence:
- Use input_evidence for meaningful commands or silent attempts that may produce
  no output, such as extraction commands with output redirection.
- Use output_evidence for confirmed observations or results visible in stdout or
  stderr, such as discovered filenames, offsets, key headers, shell prompts, or
  flags.
- A milestone may include both input_evidence and output_evidence when either
  command input or visible output can reasonably prove that progress.
- Name attempt-only milestones clearly, for example "private_key_extraction_attempted".
- Do not use the final flag value as evidence. Use a generic flag regex instead.

Evidence regex rules:
- Prefer robust patterns over exact one-off strings.
- Escape literal dots and braces.
- Avoid overly broad patterns that match unrelated output.
- For the final success_evidence and flag_found milestone, use a generic CTF flag
  pattern such as "picoCTF\\{{[^}}]+\\}}" when appropriate.

Return only valid JSON. Do not include markdown or explanatory text.

Return JSON in this exact shape:

{{
  "challenge_id": "{challenge_id or 'short_snake_case_challenge_id'}",
  "challenge_name": "{challenge_name or 'Human Readable Challenge Name'}",
  "success_evidence": "regex that indicates the final flag or success condition",
  "milestones": [
    {{
      "milestone": "short_snake_case_milestone_name",
      "input_evidence": "optional regex for student command input",
      "output_evidence": "optional regex for student-visible output",
      "goal": "what this milestone confirms or attempts",
      "concept": "underlying concept the student should learn",
      "tool_used": "tool or method category, not necessarily an exact command",
      "observation": "what evidence the student should notice",
      "next_cmd": "student-facing next action, safe as a bottom-out hint"
    }}
  ]
}}

Rules:
- Include 5 to 12 milestones.
- Keep milestones ordered from first useful progress to final flag/success.
- Each milestone must include at least one of input_evidence or output_evidence.
- Each milestone must include milestone, goal, concept, tool_used, observation, and next_cmd.
- Do not include private flag values in the output.
- Do not include full exploit scripts or full payloads.

Challenge context:
{challenge_context}

Known solution:
{json.dumps(solution, indent=2)}
""".strip()

    def parse_response(self, llm_response: str) -> Dict[str, Any]:
        if llm_response is None:
            raise ValueError("Milestone generator returned None.")

        text = llm_response.strip()

        if not text:
            raise ValueError("Milestone generator returned an empty response.")

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Milestone generator returned invalid JSON: {e}") from e

        if not isinstance(data, dict):
            raise ValueError("Milestone generator JSON response must be an object.")

        return data

    def validate_model(self, model: Dict[str, Any]) -> Dict[str, Any]:
        missing_top_level = self.REQUIRED_TOP_LEVEL_FIELDS - set(model)
        if missing_top_level:
            missing = ", ".join(sorted(missing_top_level))
            raise ValueError(f"Milestone model missing top-level fields: {missing}")

        milestones = model.get("milestones")
        if not isinstance(milestones, list) or not milestones:
            raise ValueError("Milestone model must contain a non-empty milestones list.")

        for index, milestone in enumerate(milestones):
            if not isinstance(milestone, dict):
                raise ValueError(f"Milestone at index {index} must be an object.")

            missing_fields = self.REQUIRED_MILESTONE_FIELDS - set(milestone)
            if missing_fields:
                missing = ", ".join(sorted(missing_fields))
                raise ValueError(
                    f"Milestone at index {index} missing required fields: {missing}"
                )

            has_input = bool(milestone.get("input_evidence"))
            has_output = bool(milestone.get("output_evidence"))
            if not has_input and not has_output:
                raise ValueError(
                    "Milestone at index "
                    f"{index} must include input_evidence or output_evidence."
                )

        return model