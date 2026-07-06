import json
import re
from pathlib import Path


def load_private_challenge(path: str | Path) -> dict:
    path = Path(path)

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def extract_flag(challenge_data: dict) -> str:
    """
    Prefer explicit flag field.

    Example:
    {
        "flag": "picoCTF{example}"
    }

    Fallback:
    {
        "description": "... picoCTF{example} ..."
    }
    """
    if "flag" in challenge_data:
        return challenge_data["flag"].strip()

    description = challenge_data.get("description", "")
    match = re.search(r"picoCTF\{[^}]+\}", description)

    if match is None:
        raise ValueError("Could not find flag in private challenge data.")

    return match.group(0).strip()


def make_flag_checker(private_challenge_path: str | Path):
    """
    Load the private flag once and return a checker function.
    """
    challenge_data = load_private_challenge(private_challenge_path)
    correct_flag = extract_flag(challenge_data)

    def check_flag(candidate_flag: str) -> bool:
        return candidate_flag.strip() == correct_flag

    return check_flag