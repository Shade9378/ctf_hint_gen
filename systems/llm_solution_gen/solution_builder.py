from typing import Any, Dict, List, Optional


def build_solution(
    student_state: Optional[Dict[str, Any]],
    solved_result: Dict[str, Any],
    llm_history: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "status": solved_result.get("status"),
        "student_prefix": (
            student_state.get("completed_work", [])
            if student_state
            else []
        ),
        "llm_continuation": llm_history,
        "final_flag_found": solved_result.get("status") == "solved",
    }