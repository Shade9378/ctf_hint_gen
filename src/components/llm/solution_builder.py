from typing import Any, Dict, Optional


def build_solution(
    *,
    student_state: Optional[Dict[str, Any]],
    controller_result: Dict[str, Any],
) -> Dict[str, Any]:
    history = controller_result.get("history", [])

    return {
        "status": controller_result.get("status"),
        "student_prefix": (
            student_state.get("completed_work", [])
            if student_state
            else []
        ),
        "history": history,
        "final_flag_found": controller_result.get("status") == "solved",
    }
