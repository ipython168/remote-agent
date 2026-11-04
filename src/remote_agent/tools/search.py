from __future__ import annotations

# ================================================= #
import logging
logger = logging.getLogger(__name__)
# ================================================= # 
import os
import httpx
from ifunc.utils.tools import Tools
# ================================================= #
def _tavily_search(query: str, max_results: int = 3) -> str:
    """用 Tavily API 搜尋（專為 AI 設計，回傳正文）。"""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY not set")

    url = "https://api.tavily.com/search"
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "include_answer": False,
        "max_results": max_results,
    }
    
    resp = httpx.post(url, json=payload, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    output = [f"以下是關於「{query}」的搜尋結果：\n"]
    for i, r in enumerate(data.get("results", []), 1):
        output.append(f"[{i}] {r.get('title', '')}")
        output.append(f"內容：{r.get('content', '')}")
        output.append(f"來源：{r.get('url', '')}\n")
    return "\n".join(output)


def _ddgs_search(query: str, max_results: int = 5) -> str:
    """用 DuckDuckGo 搜尋（免費 fallback）。"""
    ddgs = Tools.try_import("ddgs", "ddgs")
    if not ddgs:
        return "Error: 無法安裝 ddgs 套件"

    results = ddgs.DDGS().text(query, max_results=max_results)
    if not results:
        return f"搵唔到關於「{query}」嘅結果。"

    output = [f"以下是關於「{query}」的搜尋結果：\n"]
    for i, r in enumerate(results, 1):
        output.append(f"[{i}] {r.get('title', '')}")
        output.append(f"內容：{r.get('body', '')}")
        output.append(f"來源：{r.get('href', '')}\n")
    return "\n".join(output)


def web_search(query: str, max_results: int = 5) -> str:
    """根據環境變數決定用 Tavily 定 DuckDuckGo。"""
    try:
        if os.getenv("TAVILY_API_KEY"):
            logger.info("using Tavily for search: %s", query)
            return _tavily_search(query, max_results=3)
        else:
            logger.info("using DuckDuckGo for search: %s", query)
            return _ddgs_search(query, max_results=max_results)
    except Exception as e:
        logger.exception("search failed")
        return f"搜尋出錯：{e}"
