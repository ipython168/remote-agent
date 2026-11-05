# src/remote_agent/brain/colab.py
from __future__ import annotations

from remote_agent.brain.base import BaseBrain, Message
# ================================================= #
import logging
logger = logging.getLogger(__name__)
# ================================================= #

# 定義可用嘅 Colab 模型清單 (可隨時更新)
MODEL_LIST = [
    "google/gemini-3.8-flash",
    "google/gemini-3.5-flash-lite",
    "google/gemini-2.5-flash",
]

class ColabBrain(BaseBrain):
    name = "colab"

    def __init__(self, model: str = "google/gemini-3.5-flash-lite"):
        self.model = model
        self.fallback_model = "google/gemini-2.5-flash"
        self.max_input_tokens = 1_000_000
        try:
            from google.colab import ai as _ai
            self._ai = _ai
        except ImportError as e:
            raise RuntimeError("ColabBrain only works inside Google Colab.") from e

        self._client = self._try_make_client()
        logger.info("colab brain init: client = %s", self._client)

    def _try_make_client(self):
        try:
            from openai import OpenAI
            token = self._ai._get_model_proxy_token()
            host = self._ai._get_model_proxy_host()
            if not token or not host:
                return None
            return OpenAI(base_url=f"{host}/models/openapi", api_key=token)
        except Exception as e:
            logger.warning("failed to create colab proxy client: %r", e)
            return None

    def _render(self, messages: list[Message]) -> str:
        return "\n".join(f"[{m.role}] {m.content}" for m in messages)

    def chat(self, messages: list[Message], **kw) -> str:
        prompt = self._render(messages)

        if self._client is None:
            return self._ai.generate_text(prompt=prompt, model_name=self.model, stream=False)

        kw.setdefault("max_tokens", 2048)
        tools = kw.pop("tools", None)
        on_step = kw.pop("on_step", None)
        loop = kw.pop("loop", None)

        if tools:
            return self._react_loop(messages, tools, on_step=on_step, loop=loop, **kw)
        else:
            return self._plain_chat(messages, **kw)

    def _plain_chat(self, messages: list[Message], **kw) -> str:
        msgs = [{"role": m.role, "content": m.content} for m in messages]
        resp = self._call_api(msgs, tools=None, **kw)
        return resp.choices[0].message.content or ""

    def _react_loop(self, messages: list[Message], tools: list, on_step=None, loop=None, **kw) -> str:
        from remote_agent.tools import execute_tool
        from datetime import datetime
        import json
        import re

        msgs = [{"role": m.role, "content": m.content} for m in messages]
        user_query = msgs[-1]["content"]
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        time_prompt = f"(系統提示：今天是 {current_time}，請以此為基準。)\n"
        msgs.insert(1, {"role": "system", "content": time_prompt})

        trace = []
        max_steps = 8

        for step in range(max_steps):
            logger.info("ReAct Loop step %d (Model: %s)", step + 1, self.model)
            
            try:
                resp = self._call_api(msgs, tools=tools, **kw)
                msg = resp.choices[0].message
            except Exception as e:
                return f"❌ AI 思考出錯：{e}"
            
            has_tools = bool(getattr(msg, "tool_calls", None))
            logger.info("🔥 [React Loop] Step %d 收到回應: has_tool_calls = %s", step + 1, has_tools)

            # 任務完成（冇 tool_calls 就當完結）
            if not getattr(msg, "tool_calls", None):
                final_ans = msg.content or "✅ 任務完成。"
  
                # 🚨 終極攔截：如果佢用文字作假，用 Regex 抽出指令強制執行！
                if "🛠️ **執行工具：**" in final_ans and "```json" in final_ans:
                    logger.warning("🚨 偵測到 AI 用文字造假！強制解析並執行...")
                    try:
                        match = re.search(r"```json\n(.*?)\n```", final_ans, re.DOTALL)
                        if match:
                            fake_args = json.loads(match.group(1))
                            logger.info("🔥 成功從文字中提取參數: %s", fake_args)
                            
                            # 建立一個假嘅 Tool Call 物件
                            class FakeTC:
                                def __init__(self, name, args):
                                    self.function = type('obj', (object,), {'name': name, 'arguments': json.dumps(args)})
                            
                            # 用 setattr 安全塞入，避免 NoneType 報錯
                            setattr(msg, "tool_calls", [FakeTC("exec", fake_args)])
                            setattr(msg, "content", "我幫你執行...")
                    except Exception as e:
                        logger.error("❌ 提取失敗，跳過攔截: %s", e)

                # 如果攔截完依然冇 tool_calls，先當真係答完
                if not getattr(msg, "tool_calls", None):
                    logger.info("🔥 [React Loop] 冇 tool_calls，AI 直接回覆: %s", repr(final_ans)[:100])
                    if step == 0 and not trace:
                        return final_ans
                    if on_step:
                        self._run_callback(on_step, f"✅ **最終回答：**\n{final_ans}", loop)
                    return "\n\n".join(trace) + f"\n\n✅ **最終回答：**\n{final_ans}"

            # 記錄思考
            if msg.content:
                trace.append(f"🤔 **AI 思考 (Step {step+1})：**\n{msg.content}")
                if on_step:
                    self._run_callback(on_step, f"🤔 **AI 思考 (Step {step+1})：**\n{msg.content}", loop)

            # 執行工具
            tool_results = []
            for tc in msg.tool_calls:
                logger.info("🔥 [React Loop] 準備執行 Tool: %s", tc.function.name)

                try:
                    args = json.loads(tc.function.arguments)
                    logger.info("🔥 解析參數成功: %s", args)
                except Exception as e:
                    logger.error("❌ 解析參數失敗: %s", e)
                    args = {}
                
                trace.append(f"🛠️ **執行工具：** `{tc.function.name}`\n```json\n{tc.function.arguments}\n```")
                if on_step:
                    self._run_callback(on_step, f"🛠️ **執行工具：** `{tc.function.name}`\n```json\n{tc.function.arguments}\n```", loop)
                
                try:
                    logger.info("🔥 開始呼叫 execute_tool...")
                    result = execute_tool(tc.function.name, args)
                    logger.info("🔥 工具執行完畢，回傳長度: %d", len(str(result)))
                except Exception as e:
                    logger.exception("❌ 執行工具發生錯誤")
                    result = f"❌ 執行工具發生錯誤：{e}"
                    
                tool_results.append(f"工具 {tc.function.name} 執行結果：\n{result}")
                
                res_preview = result[:300] + "..." if len(result) > 300 else result
                trace.append(f"📥 **工具結果：**\n```\n{res_preview}\n```")
                if on_step:
                    self._run_callback(on_step, f"📥 **工具結果：**\n```\n{res_preview}\n```", loop)

            # 準備下一次 Loop 嘅 Context
            tool_context = "\n\n---\n".join(tool_results)
            recent_context = "\n\n---\n".join(tool_results[-3:]) if len(tool_results) > 3 else tool_context
            
            msgs = [
                {"role": "system", "content": time_prompt + (messages[0].content if messages[0].role == "system" else "")},
                {"role": "user", "content": user_query},
                {"role": "user", "content": f"【系統：你剛才要求執行工具，以下是執行結果】\n{recent_context}\n\n請決定下一步。如已完成，直接輸出最終答案。"}
            ]

        timeout_msg = "⚠️ **已達到最大執行步數 (8步)，任務中斷。**"
        trace.append(timeout_msg)
        full_trace = "\n\n".join(trace)
        if on_step:
            self._run_callback(on_step, f"✅ **最終回答：**\n{full_trace}", loop)
        return full_trace

    def _call_api(self, msgs: list, tools: list = None, **kw):
        """統一處理 API Call 同 Fallback 邏輯，唔會再改寫 self.model"""
        
        def _do_call(model_name):
            current_tools = tools 

            # 只有 2.5 系列先剝走 tools
            if "-2.5-" in model_name:
                logger.info("Model %s: disabling tools completely to avoid 400 error.", model_name)
                current_tools = None

            kwargs = {"model": model_name, "messages": msgs, **kw}
            if current_tools:
                kwargs["tools"] = current_tools

            resp = self._client.chat.completions.create(**kwargs)
            msg = resp.choices[0].message
            logger.info("🔥 [_call_api] 收到 AI 回應: content=%s, tool_calls=%s", 
                        repr(msg.content)[:50], "有" if msg.tool_calls else "冇")
            return resp

        try:
            return _do_call(self.model)

        except Exception as e:
            logger.warning("Model %s failed: %s", self.model, e)
            if self.model != self.fallback_model:
                logger.info("Switching to fallback model: %s", self.fallback_model)
                return _do_call(self.fallback_model)

            raise e

    def _run_callback(self, callback, text: str, loop=None):
        import asyncio
        if not loop: return
        try:
            asyncio.run_coroutine_threadsafe(callback(text), loop)
        except Exception as e:
            logger.warning("callback failed: %r", e)

    def count_tokens(self, text: str) -> int:
        return super().count_tokens(text)
