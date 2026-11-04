from __future__ import annotations

import os

from remote_agent.brain.base import BaseBrain, Message
# ================================================= #
import logging
logger = logging.getLogger(__name__)
# ================================================= #
class OllamaBrain(BaseBrain):
    name = "ollama"
    def __init__(self, model: str = "llama3.2", host: str | None = None):
        self.model = model
        self.max_input_tokens = 128_000
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")

        try:
            import ollama
        except ImportError as e:
            raise RuntimeError("pip install 'remote-agent[ollama]'") from e

        self._ollama = ollama
        self._client = ollama.Client(host=self.host)
# ================================================= #
    def chat(self, messages: list[Message], **kw) -> str:
        resp = self._client.chat(
            model=self.model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            **kw,
        )
        return resp["message"]["content"] 
# ================================================= #


# ================================================= #