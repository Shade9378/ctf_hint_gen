import json
from pathlib import Path
from typing import Any, Dict, List, Union

JsonInput = Union[Dict[str, Any], List[Dict[str, Any]], str, Path]


class LLMHintGenerator:
    def __init__(self, model_client: Any):
        self.model_client = model_client

    def generate(
        self,
        *,
        student_state: JsonInput,
        solution: JsonInput,
        challenge_context: str,
    ) -> Dict[str, Any]:

        student_state_data = self.load_json_input(student_state)
        solution_data = self.load_json_input(solution)

        prompt = self.build_prompt(
            student_state=student_state_data,
            solution=solution_data,
            challenge_context=challenge_context,
        )

        llm_response = self.model_client.generate(prompt)

        return self.parse_response(llm_response)

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
        student_state: Union[Dict[str, Any], List[Dict[str, Any]]],
        solution: Union[Dict[str, Any], List[Dict[str, Any]]],
        challenge_context: str,
    ) -> str:
        return f"""
You are now a CTF hint generator.

Your job is to generate helpful next-step hints for a student.
The hints should guide the student toward the next correct step without directly giving away the full solution.

You will be provided:

1. student_state

student_state may be one of two formats:

Format A: Raw student log
- Usually a list of log entries.
- Entries may contain fields such as:
- action_type
- cmd
- output
- exit_code
- cwd
- Commands show what the student attempted.
- Outputs show what the student actually discovered.
- Do not mark progress as completed just because the student ran a command.
- Mark progress as completed only when the output or observed result provides concrete evidence.

Format B: Milestone matcher output
- Usually a dict containing fields such as:
- solved
- success_match
- milestones
- next_milestone
- If student_state contains "milestones" and "next_milestone", treat it as rule-based milestone matcher output.
- In this case, trust the reached/unreached milestone statuses unless they obviously contradict the solution.
- Use next_milestone as the target for the hints.

2. solution

solution is the known solution trajectory, generated solution trace, or writeup-derived solution.
It may contain:
- history
- milestones
- commands
- inputs
- outputs
- final_flag_found

3. challenge_context

challenge_context is the public challenge description/context.

Important:
- Generate all four hint levels in one response.
- Do not reveal the final flag.
- Do not reveal a full exploit script.
- Do not reveal a full payload.
- Do not reveal the complete solve sequence.
- Do not include markdown.
- Return only valid JSON.

Your process:
1. Determine whether student_state is raw log format or milestone matcher format.
2. Identify what the student has already completed.
3. Identify the next unresolved step.
4. If milestone matcher output is available, prefer student_state["next_milestone"] as the next target.
5. If only raw logs are available, compare the logs against the solution trajectory to infer the next target.
6. Generate four hints for the next target, one for each hint level.
7. Keep all hints student-facing, helpful, and non-leaky.

Hint levels:

Level 1: Conceptual hint
Give a high-level concept or idea. Do not mention exact commands, tools, filenames, payloads, addresses, offsets, or solution steps.

Level 2: Observation hint
Point out what kind of evidence the student should notice in their current output or challenge artifact. Do not name the exact command.

Level 3: Tool-usage hint
Suggest the type of tool or method that would help, but do not provide a complete command unless the command is generic and non-revealing.

Level 4: Bottom-out hint
Give the most direct next step that is still safe. You may provide a concrete next action, but do not reveal the final flag, full exploit script, full payload, or complete solve sequence.

Challenge context:
{challenge_context}

Student state:
{json.dumps(student_state, indent=2)}

Solution:
{json.dumps(solution, indent=2)}

Return JSON in this exact shape:

{{
"student_state_format": "raw_log | milestone_matcher | unknown",
"matched_step": "step id, step number, milestone name, or null",
"next_step": "next step id, step number, milestone name, or brief next-step description",
"student_state_summary": "brief summary of what the student has already done",
"hints": {{
    "level_1_conceptual": "hint text",
    "level_2_observation": "hint text",
    "level_3_method_tool": "hint text",
    "level_4_bottom_out": "hint text"
}},
"leakage_risk": "low | medium | high",
"leakage_notes": "brief explanation of why the hints are safe or risky"
}}
""".strip()

    def parse_response(self, llm_response: str) -> Dict[str, Any]:
        if llm_response is None:
            return {
                "status": "failed",
                "reason": "LLM response was None.",
            }

        text = llm_response.strip()

        if not text:
            return {
                "status": "failed",
                "reason": "LLM returned empty response.",
            }

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            return {
                "status": "failed",
                "reason": f"LLM returned invalid JSON: {e}",
                "raw_response": text,
            }

        if not isinstance(data, dict):
            return {
                "status": "failed",
                "reason": "LLM response JSON was not an object.",
                "raw_response": data,
            }

        return data