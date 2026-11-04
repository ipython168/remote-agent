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
            "name": "read_file",
            "description": "讀取檔案嘅部分內容。適合睇 code 或文件。大檔案請用 start_line 分開讀。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "檔案絕對路徑"},
                    "start_line": {"type": "integer", "description": "由第幾行開始 (預設 1)"},
                    "max_lines": {"type": "integer", "description": "最多讀幾多行 (預設 200)"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "列出資料夾入面有咩檔案。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "資料夾絕對路徑"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "grep",
            "description": "喺檔案入面搜尋關鍵字，會回傳行數同內容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "要搵嘅字"},
                    "path": {"type": "string", "description": "檔案絕對路徑"}
                },
                "required": ["pattern", "path"]
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
    if name == "search":
        return web_search(**arguments)
    elif name == "read_file":
        return safe_read_file(
            path_str=arguments.get("path"),
            start_line=arguments.get("start_line", 1),
            max_lines=arguments.get("max_lines", 200)
        )
            
    elif name == "list_dir":
        return safe_list_dir(path_str=arguments.get("path"))

    elif name == "grep":
        return safe_grep(
            pattern=arguments.get("pattern"),
            path_str=arguments.get("path")
        )
    elif name == "exec":
        cmd = arguments.get("cmd", "")
        if not is_command_safe(cmd):
            return f"❌ 拒絕執行：指令 `{cmd}` 含有危險字眼或嘗試修改 Google Drive，已被安全機制攔截。"
        return run_command(cmd, cwd="/content")

    return f"Error: 未知的工具 {name}"
# ================================================= # 
