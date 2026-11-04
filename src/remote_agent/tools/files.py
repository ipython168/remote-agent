# src/remote_agent/tools/files.py
from __future__ import annotations

# ================================================= #
import logging
logger = logging.getLogger(__name__)
# ================================================= #
from pathlib import Path
import subprocess
# ================================================= # 
# 限制工作目錄
WORKSPACE = Path("/content").resolve()

# 允許讀取嘅敏感路徑
SENSITIVE_PATHS = [
    "/content/drive/MyDrive/develop/Projects/remote-agent/.env",
    "/content/drive/MyDrive/develop/Projects/ifunc/.env",
]
# ================================================= #
def safe_read_file(path_str: str, start_line: int = 1, max_lines: int = 200) -> str:
    """安全讀取檔案內容。限制只能讀取 .env 以外嘅檔案。"""
    p = Path(path_str).resolve()
    
    # 1. 阻擋敏感檔案
    if str(p) in SENSITIVE_PATHS or p.name == ".env":
        return "❌ Error: 禁止讀取敏感檔案 (.env)。"

    # 2. 檢查存在
    if not p.exists():
        return f"❌ Error: 檔案不存在 {p}"
    if p.is_dir():
        return f"❌ Error: 這是一個資料夾，請使用 list_dir。"
    if p.stat().st_size > 5 * 1024 * 1024:
        return f"❌ Error: 檔案太大 (>5MB)，請使用 grep 或 sed 提取部分內容。"

    # 3. 讀取內容 (按行)
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            
        total_lines = len(lines)
        end_line = min(start_line + max_lines - 1, total_lines)
        
        # 抽取出指定範圍
        chunk = lines[start_line-1:end_line]
        
        header = f"📄 檔案：{p} (顯示第 {start_line} 至 {end_line} 行，共 {total_lines} 行)\n"
        header += "```\n"
        footer = "\n```"
        
        return header + "".join(chunk) + footer
    except Exception as e:
        return f"❌ Error: 讀取失敗：{e}"
# ================================================= #
def safe_list_dir(path_str: str) -> str:
    """列出資料夾內容 (只准 ls)。"""
    p = Path(path_str).resolve()
    if not p.exists() or not p.is_dir():
        return f"❌ Error: 資料夾不存在 {p}"
    
    try:
        files = []
        for f in p.iterdir():
            icon = "📁" if f.is_dir() else "📄"
            files.append(f"{icon} {f.name}")
        files.sort()
        return f"📂 {p} 內容：\n" + "\n".join(files)
    except Exception as e:
        return f"❌ Error: {e}"
# ================================================= #
def safe_grep(pattern: str, path_str: str) -> str:
    """喺檔案或資料夾入面搵字。"""
    p = Path(path_str).resolve()
    if not p.exists():
        return f"❌ Error: 檔案或資料夾不存在 {p}"
    
    try:
        if p.is_file():
            cmd = ["grep", "-n", "-i", pattern, str(p)]
        else:
            # 如果係 folder，用 -r 但限制喺該 folder
            cmd = ["grep", "-r", "-n", "-i", pattern, str(p)]

        # 限制最多 15 秒，防止 GDrive 卡死
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=15
        )
        if result.returncode == 1:
            return "🔍 搵唔到匹配結果。"
        if result.returncode > 1:
            return f"❌ Error: {result.stderr[:500]}"
        
        # 限制 output 長度
        out = result.stdout[:3000]
        return f"🔍 grep 結果：\n```\n{out}\n```"
    except subprocess.TimeoutExpired:
        return "❌ Error: 搜尋超時 (15秒限制)。請縮窄範圍（例如指明 src/ifunc 入面邊個資料夾）。"
    except Exception as e:
        return f"❌ Error: {e}"
# ================================================= #
