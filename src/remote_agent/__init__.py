from importlib import import_module

_LAZY = {
    "__version__": "remote_agent.__version__",
}


def __getattr__(name):
    if name in _LAZY:
        mod = import_module(_LAZY[name])
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = list(_LAZY)
