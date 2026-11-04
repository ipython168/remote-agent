from __future__ import annotations

import os

from remote_agent.brain.base import BaseBrain, Message
# ================================================= #
import logging
logger = logging.getLogger(__name__)
# ================================================= # 
class GeminiBrain(BaseBrain):
    name = "gemini" 
    def __init__(self, model: str = "gemini-2.5-flash"):
        self.model = model
        self.max_input_tokens = 1_000_000

        try:
            from google import genai
        except ImportError as e:
            raise RuntimeError("pip install 'remote-agent[gemini]'") from e

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set")

        self._client = genai.Client(api_key=api_key)
# ================================================= #
    def _split(self, messages: list[Message]) -> tuple[str | None, list]:
        system = None
        contents = []
        for m in messages:
            if m.role == "system":
                system = m.content
            elif m.role == "user":
                contents.append({"role": "user", "parts": [{"text": m.content}]})
            elif m.role == "assistant":
                contents.append({"role": "model", "parts": [{"text": m.content}]})
        return system, contents
# ================================================= #
    def chat(self, messages: list[Message], **kw) -> str:
        system, contents = self._split(messages)
        cfg = {}
        if system:
            cfg["system_instruction"] = system
        resp = self._client.models.generate_content(
            model=self.model,
            contents=contents,
            config=cfg or None,
            **kw,
        )
        return resp.text or ""
# ================================================= # 






# ================================================= #