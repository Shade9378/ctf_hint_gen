from typing import Any, Dict


def build_solution(
    *,
    controller_result: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "status": controller_result.get("status"),
        "history": controller_result.get("history", []),
        "final_flag_found": controller_result.get("status") == "solved",
    }