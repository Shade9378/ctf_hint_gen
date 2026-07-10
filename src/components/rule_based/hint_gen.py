from __future__ import annotations

from typing import Any, Dict, Optional


class _SafeFormatDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


class HintGenerator:
    def __init__(self, templates: Dict[str, Any]):
        self.templates = templates
        self.levels = templates.get("levels", {})

    def generate(self, milestone: Optional[Dict[str, Any]]) -> Dict[str, str]:
        """
        Expected shape:
        {
          "level_1_conceptual": "...",
          "level_2_observation": "...",
          "level_3_method_tool": "...",
          "level_4_bottom_out": "..."
        }
        """
        if milestone is None:
            return {level_key: "" for level_key in self.levels.keys()}

        context = _SafeFormatDict(milestone)
        hints: Dict[str, str] = {}

        for level_key, level_config in self.levels.items():
            template = level_config.get("template", "")
            hints[level_key] = template.format_map(context)

        return hints
