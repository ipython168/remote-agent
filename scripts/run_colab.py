# scripts/run_colab.py
"""Launcher for Colab notebook cell.

Usage (in a Colab cell):
    from scripts.run_colab import start
    task = start()
"""
import warnings
import asyncio
import os
import sys
from pathlib import Path
# 熄滅 Jupyter / ddgs 內部嘅 deprecation warning
warnings.filterwarnings("ignore", category=DeprecationWarning)
# ---- remote_agent fallback ----
try:
    import remote_agent  # noqa: F401
except ImportError:
    REPO_SRC = "/content/drive/MyDrive/develop/Projects/remote-agent/src"
    if Path(REPO_SRC).exists():
        sys.path.append(REPO_SRC)
        
# ---- ifunc fallback ----
try:
    import ifunc  # noqa: F401
except ImportError:
    IFUNC_SRC = "/content/drive/MyDrive/develop/Projects/ifunc/src"
    if Path(IFUNC_SRC).exists():
        sys.path.append(IFUNC_SRC)

# ---- 確保 dependencies 裝咗（用 ifunc.Tools.try_import）----
from ifunc.utils.tools import Tools  # noqa: E402

_REQUIRED = [
    ("discord", "py-cord>=2.6.0"),
    ("nest_asyncio", "nest-asyncio>=1.6.0"),
    ("yaml", "pyyaml>=6.0.2"),
    ("dotenv", "python-dotenv>=1.0.1"),
    ("openai", "openai>=1.0.0"),
]

for _mod, _spec in _REQUIRED:
    if Tools.try_import(_mod, _spec) is None:
        raise RuntimeError(f"Failed to install {_spec}")

# ---- load .env ----
from dotenv import load_dotenv  # noqa: E402
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# ---- logging via ifunc ----
from ifunc.utils.logging import setup_logging  # noqa: E402
setup_logging(
    config_path=Path(__file__).resolve().parents[1] / "configs" / "logging.yaml",
    tz_str="Asia/Hong_Kong",
)
# ================================================= #
import logging
logger = logging.getLogger(__name__)
# ================================================= #

_current_task: asyncio.Task | None = None


def start() -> asyncio.Task:
    """Start bot in background. Auto cancel previous + cleanup stale bots."""
    global _current_task

    # 1. cancel 上一次 task
    if _current_task and not _current_task.done():
        logger.info("cancelling previous task")
        _current_task.cancel()
        # 唔喺呢度 await（因為呢個係 sync function）
        # 交俾 _start() 入面 cleanup() 處理

    import nest_asyncio
    nest_asyncio.apply()

    from scripts.cleanup import cleanup
    from remote_agent.config import load_settings
    from remote_agent.persona import load_persona
    from remote_agent.discord_bot.bot import RemoteAgentBot

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN not set in .env")

    async def _start():
        await cleanup()

        settings = load_settings()
        persona_cfg = settings["persona"]
        persona = load_persona(persona_cfg["path"], active=persona_cfg["active"])
        bot = RemoteAgentBot(settings=settings, persona=persona)
        bot.load_extension("remote_agent.discord_bot.cogs.chat")
        await bot.start(token)

    _current_task = asyncio.create_task(_start())
    logger.info("bot task created")
    return _current_task


if __name__ == "__main__":
    start()
