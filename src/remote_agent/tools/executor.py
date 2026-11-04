from __future__ import annotations

# ================================================= #
import logging
logger = logging.getLogger(__name__)
# ================================================= #

import subprocess
import shlex

def is_command_safe(cmd: str) -> bool:
    """檢查指令有冇包含危險字眼或針對 Google Drive 嘅修改。"""
    try:
        parts = shlex.split(cmd)
        if not parts:
            logger.warning("exec blocked: empty command")
            return False
        main_cmd = parts[0].lower()
    except Exception as e:
        logger.warning("exec blocked: failed to parse command %r (%r)", cmd, e)
        return False

    # 黑名單（完全禁止）
    blacklist = ["rm", "mv", "cp", "sudo", "chmod", "chown", "wget", "curl", "apt", "apt-get"]
    if main_cmd in blacklist:
        logger.warning("exec blocked: command '%s' is in blacklist", main_cmd)
        return False

    # 針對 Google Drive 嘅防護（如果包含 drive，唔准有寫入符號或修改指令）
    if "/content/drive" in cmd:
        unsafe_symbols = [">", ">>", "touch", "mkdir", "rm", "mv"]
        for sym in unsafe_symbols:
            if sym in cmd:
                logger.warning("exec blocked: Google Drive write attempt detected (%s)", sym)
                return False

    # 禁止 cd 入 Drive 執行任何嘢（防止喺 Drive 執行 pip / python）
    if "cd " in cmd and "/content/drive" in cmd:
        # 如果佢用 cd 入 Drive 並且後面有 && 或者其他指令，直接攔截
        if "&&" in cmd or ";" in cmd:
            logger.warning("exec blocked: cd into GDrive with chained command")
            return False

    return True

def run_command(cmd: str, cwd: str = "/content") -> str:
    """喺指定目錄執行 shell command，回傳 stdout + stderr。"""
    try:
        logger.info("executing: %s (cwd=%s)", cmd, cwd)
         
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        
        output = []
        if result.stdout:
            output.append(result.stdout)
        if result.stderr:
            output.append(f"\n[STDERR]\n{result.stderr}")
            
        if not output:
            return "✅ 執行成功，無輸出。"
            
        return "".join(output)
    except subprocess.TimeoutExpired:
        logger.warning("exec timeout: %s", cmd)
        return "❌ Error: 指令超時 (30 秒限制)。請檢查是否用了 `grep -r` 掃描全機，或者改用精確路徑。"
    except Exception as e:
        logger.exception("exec failed: %s", cmd)
        return f"❌ Error: {e}"
