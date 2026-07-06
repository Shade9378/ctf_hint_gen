import json
from pathlib import Path
from typing import Any, Dict, Union


class LLMHintGenerator:
    """
    LLM-based CTF hint generator.

    Takes:
        - student_state
        - solution file or solution dict
        - challenge_context

    Returns:
        Structured hint JSON.
    """

    def __init__(self, model_client: Any):
        self.model_client = model_client # Add log for hint_gen 

    def generate(
        self,
        *,
        student_state: Dict[str, Any],
        solution: Union[Dict[str, Any], str, Path],
        challenge_context: str
    ) -> Dict[str, Any]:

        solution_data = self.load_solution(solution)

        prompt = self.build_prompt(
            student_state=student_state,
            solution=solution_data,
            challenge_context=challenge_context,
        )

        llm_response = self.model_client.generate(prompt)

        return self.parse_response(llm_response)

    def load_solution(
        self,
        solution: Union[Dict[str, Any], str, Path],
    ) -> Dict[str, Any]:
        if isinstance(solution, dict):
            return solution

        solution_path = Path(solution)

        with solution_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def build_prompt(
        self,
        *,
        student_state: Dict[str, Any],
        solution: Dict[str, Any],
        challenge_context: str
    ) -> str:
        return f"""
You are now a CTF hint generator.

Your job is to generate a helpful next-step hint. The hint should guide the student toward the next correct step without directly giving away the full solution.

You will be provided:
- student_state: a compact summary of the student's valid progress.
- solution: the known solution trajectory. It may contain:
  - student_prefix: valid work already completed by the student.
  - history: the LLM solver's continuation after the student state.
  - llm_history: the LLM solver's continuation after the student state.
  - final_flag_found: whether the solver found the final flag.
- challenge_context: public challenge description/context.

Important:
- Do not reveal the final flag.
- Do not reveal a full exploit script.
- Do not reveal a full payload.
- Do not reveal the complete solve sequence.
- Do not include markdown.
- Return only valid JSON.

Your process:
1. Read student_state and identify what the student has already completed.
2. Read the solution trajectory and locate the student's current position.
3. Identify the next unresolved step.
4. Generate four hints for the next unresolved step, one for each hint level.
5. Select the hint that corresponds to the requested hint level.
6. If the student's path appears invalid or unclear, redirect them toward the earliest relevant unresolved step.

Hint levels:

Level 1: Conceptual hint
Give a high-level concept or idea. Do not mention exact commands, tools, filenames, payloads, or solution steps.

Level 2: Observation hint
Point out what kind of evidence the student should notice in their current output or challenge artifact. Do not name the exact tool or command.

Level 3: Tool-usage hint
Suggest the type of tool or method that would help, but do not provide a complete command unless the command is very generic and does not reveal the solution.

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
  "matched_step": "step id, step number, or null",
  "next_step": "next step id, step number, or brief next-step description",
  "student_state_summary": "brief summary of what the student has already done",
  "selected_hint": "the hint matching the requested hint level",
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