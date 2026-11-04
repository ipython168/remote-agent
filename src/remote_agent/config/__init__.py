from importlib import import_module

_LAZY = {
    "load_settings": "remote_agent.config.loader",
    "load_persona": "remote_agent.persona.loader",
}


def __getattr__(name):
    if name in _LAZY:
        mod = import_module(_LAZY[name])
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = list(_LAZY)
