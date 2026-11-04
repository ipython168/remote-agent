from __future__ import annotations
import os
import discord
from discord.ext import commands

from remote_agent.brain.base import get_brain
from remote_agent.config import load_settings
from remote_agent.persona import load_persona
from remote_agent.history import HistoryStore
from remote_agent.persona import render_system_prompt
# ================================================= #
import logging
logger = logging.getLogger(__name__) 
# ================================================= # 
class RemoteAgentBot(commands.Bot):
    def __init__(self, settings: dict, persona: dict):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix=settings["discord"].get("prefix", "!"), intents=intents)

        self.settings = settings
        self.persona = persona
        self.system_prompt = render_system_prompt(persona)
        self.brain = get_brain(settings)
        self.history = HistoryStore(
            base_path=settings["history"]["path"],
            max_turns=settings["history"].get("max_turns", 50),
            count_tokens=self.brain.count_tokens,
            max_tokens=int(self.brain.max_input_tokens * 0.8),

        )
        self.history.split_by_persona = settings["history"].get("split_by_persona", True)
        self.history.active_persona = settings.get("persona", {}).get("active", "default")
# ================================================= #
    async def on_ready(self) -> None:
        logger.info("logged in as %s (brain=%s, model=%s)", self.user, self.brain.name, self.brain.model)
# ================================================= # 
def run_bot() -> None:
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN not set in environment / .env")

    settings = load_settings()
    persona_cfg = settings.get("persona", {})
    persona = load_persona(persona_cfg.get("path"), active=persona_cfg.get("active"))

    bot = RemoteAgentBot(settings=settings, persona=persona)
    bot.run(token)
# ================================================= #











# ================================================= #