from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

# ================================================= #
@dataclass
class Message:
    role: str  # "system" | "user" | "assistant"
    content: str
# ================================================= #
class BaseBrain:
    """Brain 基礎類，提供 default count_tokens 實作。
    子類可 override。
    """
    name: str = "base"
    model: str = ""
    max_input_tokens: int = 0

    def chat(self, messages: list[Message], **kw) -> str:
        raise NotImplementedError
# ================================================= #
    def count_tokens(self, text: str) -> int:
        """粗略估算：CJK 1 字 ≈ 1 token，英文 4 char ≈ 1 token。"""
        cjk = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
        other = len(text) - cjk
        return cjk + other // 4
# ================================================= #
@runtime_checkable
class Brain(Protocol):
    name: str
    model: str
    max_input_tokens: int

    def chat(self, messages: list[Message], **kw) -> str: ...

    def count_tokens(self, text: str) -> int: ...
# ================================================= #
def get_brain(settings: dict) -> Brain:
    cfg = settings.get("brain", {})
    backend = cfg.get("backend", "colab")
    model = cfg.get("model", "google/gemini-3.5-flash")

    if backend == "colab":
        from remote_agent.brain.colab import ColabBrain
        return ColabBrain(model=model)
    if backend == "openai":
        from remote_agent.brain.openai import OpenAIBrain
        return OpenAIBrain(model=model)
    if backend == "gemini":
        from remote_agent.brain.gemini import GeminiBrain
        return GeminiBrain(model=model)
    if backend == "ollama":
        from remote_agent.brain.ollama import OllamaBrain
        return OllamaBrain(model=model)

    raise ValueError(f"Unknown brain backend: {backend}")
