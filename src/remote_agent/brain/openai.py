from __future__ import annotations

import os
from remote_agent.brain.base import BaseBrain, Message
# ================================================= #
import logging
logger = logging.getLogger(__name__)
# ================================================= # 
class OpenAIBrain(BaseBrain):
    name = "openai" 
    def __init__(self, model: str = "gpt-4o-mini", base_url: str | None = None):
        self.model = model
        self.max_input_tokens = 128_000

        try:
            from openai import OpenAI
        except ImportError as e:
            raise RuntimeError("pip install 'remote-agent[openai]'") from e

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set")

        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url or os.getenv("OPENAI_BASE_URL") or None,
        )
# ================================================= #
    def chat(self, messages: list[Message], **kw) -> str:
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            **kw,
        )
        return resp.choices[0].message.content or ""
# ================================================= #
    def count_tokens(self, text: str) -> int:
        try:
            import tiktoken
            enc = tiktoken.encoding_for_model(self.model)
            return len(enc.encode(text))
        except Exception:
            return super().count_tokens(text)
# ================================================= #



