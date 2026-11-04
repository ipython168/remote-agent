from importlib import import_module

_LAZY = {
    "web_search": "remote_agent.tools.search",
    "get_tools_schema": "remote_agent.tools.schema",
    "get_tools_for_persona": "remote_agent.tools.schema",
    "execute_tool": "remote_agent.tools.schema",
}

def __getattr__(name):
    if name in _LAZY:
        mod = import_module(_LAZY[name])
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = list(_LAZY)
