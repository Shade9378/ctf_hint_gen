import json
from typing import Any, Dict, List


class FakeModelClient:
    def __init__(self, responses: List[Dict[str, Any]]):
        self.responses = responses
        self.index = 0

    def generate(self, prompt: str) -> str:
        print("\n--- PROMPT PREVIEW ---")
        print(prompt)
        print("--- END PROMPT PREVIEW ---\n")

        if self.index >= len(self.responses):
            return json.dumps({
                "action": "stop",
                "reason": "No more fake responses."
            })

        response = self.responses[self.index]
        self.index += 1
        return json.dumps(response)