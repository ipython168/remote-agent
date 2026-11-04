from __future__ import annotations
import json
from pathlib import Path

from remote_agent.brain.base import Message
# ================================================= #
class HistoryStore:
    def __init__(self, base_path: str | Path, max_turns: int = 50, count_tokens=None, max_tokens: int | None = None):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.max_turns = max_turns
        self.count_tokens = count_tokens
        self.max_tokens = max_tokens
        self.split_by_persona = False
        self.active_persona = None
# ================================================= #
    def _file(self, channel_id: str | int) -> Path:
        if self.split_by_persona and self.active_persona:
            return self.base_path / f"{channel_id}_{self.active_persona}.json"
        return self.base_path / f"{channel_id}.json"
# ================================================= #
    def load(self, channel_id: str | int) -> list[Message]:
        f = self._file(channel_id)
        if not f.exists():
            return []
        raw = json.loads(f.read_text(encoding="utf-8"))
        return [Message(role=m["role"], content=m["content"]) for m in raw]
# ================================================= #
    def save(self, channel_id: str | int, messages: list[Message]) -> None:
        trimmed = self._trim(messages)
        f = self._file(channel_id)
        f.write_text(
            json.dumps(
                [{"role": m.role, "content": m.content} for m in trimmed],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
# ================================================= #
    def append(self, channel_id: str | int, message: Message) -> list[Message]:
        msgs = self.load(channel_id)
        msgs.append(message)
        self.save(channel_id, msgs)
        return self.load(channel_id)
# ================================================= #
    def reset(self, channel_id: str | int) -> None:
        f = self._file(channel_id)
        if f.exists():
            f.unlink()
# ================================================= #
    def _trim(self, messages: list[Message]) -> list[Message]:
        # 保留 system message，其餘按 max_turns 計
        system = [m for m in messages if m.role == "system"]
        rest = [m for m in messages if m.role != "system"]
        max_msgs = self.max_turns * 2  # user + assistant 各一
        if len(rest) > max_msgs:
            rest = rest[-max_msgs:]
        if self.count_tokens and self.max_tokens:
            rest = self._trim_by_tokens(system, rest)
        return system + rest
# ================================================= #
    def _trim_by_tokens(self, system: list[Message], rest: list[Message]) -> list[Message]:
        budget = self.max_tokens - sum(self.count_tokens(m.content) for m in system)
        kept: list[Message] = []
        for m in reversed(rest):
            cost = self.count_tokens(m.content)
            if budget - cost < 0:
                break
            budget -= cost
            kept.append(m)
        return list(reversed(kept))
# ================================================= #





# ================================================= #
