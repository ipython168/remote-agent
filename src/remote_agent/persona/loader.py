from __future__ import annotations

from pathlib import Path
from typing import Any
import yaml
# ================================================= #
def load_persona(path: str | Path, active: str | None = None) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Persona not found: {p}")
    with p.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    # 兼容舊格式（直接 persona dict）同新格式（personas: {...}）
    if "personas" not in data:
        return data

    if not active:
        raise ValueError("必須指定 active persona")
    key = active

    if key not in data["personas"]:
        raise KeyError(f"Persona '{key}' 唔存在（可用：{list(data['personas'])})")
    return data["personas"][key]
# ================================================= #
def render_system_prompt(persona: dict[str, Any]) -> str:
    if persona.get("system_prompt"):
        return persona["system_prompt"].strip()

    parts: list[str] = []
    if persona.get("name"):
        parts.append(f"你叫 {persona['name']}。")
    if persona.get("role"):
        parts.append(f"角色：{persona['role']}。")
    if persona.get("language"):
        parts.append(f"語言：{persona['language']}。")
    if persona.get("tone"):
        parts.append(f"風格：{persona['tone']}。")
    if persona.get("rules"):
        parts.append("規則：")
        for r in persona["rules"]:
            parts.append(f"- {r}")

    return "\n".join(parts)
# ================================================= #





