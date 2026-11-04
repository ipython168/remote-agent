from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
# ================================================= #
def _resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else REPO_ROOT / p
# ================================================= #
def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
# ================================================= #
def load_settings(path: str | Path | None = None) -> dict[str, Any]:
    cfg_path = _resolve(str(path)) if path else REPO_ROOT / "configs" / "settings.yaml"
    return _read_yaml(cfg_path)
# ================================================= #



# ================================================= #


