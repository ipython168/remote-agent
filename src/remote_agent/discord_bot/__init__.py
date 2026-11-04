from importlib import import_module

_LAZY = {
    "RemoteAgentBot": "remote_agent.discord_bot.bot",
    "run_bot": "remote_agent.discord_bot.bot",
}


def __getattr__(name):
    if name in _LAZY:
        mod = import_module(_LAZY[name])
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = list(_LAZY)
