from __future__ import annotations

from remote_agent.tools.search import web_search
from remote_agent.tools.files import safe_read_file, safe_list_dir, safe_grep
from remote_agent.tools.executor import run_command, is_command_safe
# ================================================= #
# 定義俾 LLM 睇嘅 tools 清單
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "search",
            "description": "搜尋即時網頁資料。當你需要最新資訊、新聞、股票價格或你不知道的知識時使用。請使用『最新』、『今年』等詞彙。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜尋關鍵字。"
                    }
                },
                "required": ["query"]
            }
        }
    }, 
    {
        "type": "function",
        "function": {
            "name": "exec",
            "description": "喺 /content 執行 Shell 指令。適合安裝套件、下載檔案、執行 python 腳本。",
            "parameters": {
                "type": "object",
                "properties": {
                    "cmd": {"type": "string", "description": "要執行嘅完整 shell command"}
                },
                "required": ["cmd"]
            }
        }
    },
]
# ================================================= # 
def get_tools_schema() -> list:
    return TOOLS_SCHEMA
# ================================================= # 
def get_tools_for_persona(allowed_tools: list) -> list:
    """根據 persona 允許嘅工具清單過濾。"""
    if not allowed_tools:
        return TOOLS_SCHEMA
    return [t for t in TOOLS_SCHEMA if t["function"]["name"] in allowed_tools]
# ================================================= # 

def execute_tool(name: str, arguments: dict) -> str:
    """根據 LLM 的要求執行對應嘅工具。"""
    # 呢度加 Log，確保真係有入嚟
    import logging
    logger = logging.getLogger(__name__)
    logger.info("🔥 [execute_tool] 收到請求: name=%s, args=%s", name, arguments)

    if name == "search":
        return web_search(**arguments)
    elif name == "exec":
        cmd = arguments.get("cmd")
        if not is_command_safe(cmd):
            logger.warning("❌ [execute_tool] 被安全規則攔截: %s", cmd)
            return f"❌ 安全攔截：指令被拒絕執行 (包含危險字眼或違反 Drive 保護規則)。"
        return run_command(cmd)
    
    logger.warning("❌ [execute_tool] 未知的工具: %s", name)
    return f"❌ Error: 未知的工具 {name}"
# ================================================= # 
