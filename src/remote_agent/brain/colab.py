from __future__ import annotations

from remote_agent.brain.base import BaseBrain, Message
# ================================================= #
import logging
logger = logging.getLogger(__name__)
# ================================================= #

class ColabBrain(BaseBrain):
    name = "colab"

    def __init__(self, model: str = "google/gemini-3.5-flash"):
        self.model = model
        self.max_input_tokens = 1_000_000
        try:
            from google.colab import ai as _ai
            self._ai = _ai
        except ImportError as e:
            raise RuntimeError(
                "ColabBrain only works inside Google Colab. "
                "Use another backend (openai / gemini / ollama)."
            ) from e

        self._client = self._try_make_client()
        logger.info("colab brain init: client = %s", self._client)

        if self._client is None:
            logger.warning(
                "google.colab.ai private API 改咗，fallback 去 ai.generate_text()。"
                "唔可以 set max_tokens，大 prompt 會 403。請更新 ColabBrain。"
            )

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
        lines = []
        for m in messages:
            lines.append(f"[{m.role}] {m.content}")
        return "\n".join(lines)

    def chat(self, messages: list[Message], **kw) -> str:
        prompt = self._render(messages)

        logger.info("colab chat: using self._client = %s", self._client is not None)

        if self._client is not None:
            kw.setdefault("max_tokens", 2048)
            tools = kw.pop("tools", None)
            on_step = kw.pop("on_step", None)
            loop = kw.pop("loop", None)
            
            if tools:
                return self._chat_with_tools(messages, tools, on_step=on_step, loop=loop, **kw)

            try:
                resp = self._client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    **kw,
                )
                return resp.choices[0].message.content or ""
            except Exception as e:
                logger.exception("colab proxy chat failed")
                raise

        # fallback: 官方 ai.generate_text（唔收 max_tokens）
        return self._ai.generate_text(
            prompt=prompt,
            model_name=self.model,
            stream=False,
        )

    def _chat_with_tools(self, messages: list[Message], tools: list, on_step=None, loop=None, **kw) -> str:
        from remote_agent.tools import execute_tool
        from datetime import datetime
        import json

        # 1. 轉換 messages 格式
        msgs = [{"role": m.role, "content": m.content} for m in messages]
        user_query = msgs[-1]["content"]

        # 塞入當前時間
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        time_prompt = f"(系統提示：今天是 {current_time}，請以此為基準。)\n"
        msgs.insert(1, {"role": "system", "content": time_prompt})

        trace = []
        max_steps = 8
        
        for step in range(max_steps):
            logger.info("ReAct Loop step %d", step + 1)
            
            try:
                resp = self._client.chat.completions.create(
                    model=self.model,
                    messages=msgs,
                    tools=tools,
                    **kw,
                )
                msg = resp.choices[0].message
            except Exception as e:
                logger.exception("brain call failed at step %d", step + 1)
                return f"❌ AI 思考出錯：{e}"

            # 任務完成
            if not msg.tool_calls:
                final_ans = msg.content or "✅ 任務完成。"
                if on_step:
                    self._run_callback(on_step, f"✅ **最終回答：**\n{final_ans}", loop)
                # 將 Trace 同最終答案夾埋一齊回傳，咁 history 就會有紀錄
                if trace:
                    return "\n\n".join(trace) + f"\n\n✅ **最終回答：**\n{final_ans}"
                return final_ans

            # 記錄佢嘅思考
            if msg.content:
                trace.append(f"🤔 **AI 思考 (Step {step+1})：**\n{msg.content}")
                if on_step:
                    self._run_callback(on_step, f"🤔 **AI 思考 (Step {step+1})：**\n{msg.content}", loop)

            # 執行工具
            tool_results = []
            for tc in msg.tool_calls:
                logger.info("executing tool: %s with %s", tc.function.name, tc.function.arguments)
                try:
                    args = json.loads(tc.function.arguments)
                except:
                    args = {}
                
                trace.append(f"🛠️ **執行工具：** `{tc.function.name}`\n```json\n{tc.function.arguments}\n```")
                if on_step:
                    self._run_callback(on_step, f"🛠️ **執行工具：** `{tc.function.name}`\n```json\n{tc.function.arguments}\n```", loop)

                # 加 Try-Except 防止 Tool 拋出 Exception 搞死個 Loop
                try:
                    result = execute_tool(tc.function.name, args)
                except Exception as e:
                    logger.exception("tool execution failed")
                    result = f"❌ 執行工具發生錯誤：{e}"
                
                tool_results.append(f"工具 {tc.function.name} 執行結果：\n{result}")
                
                res_preview = result[:300] + "..." if len(result) > 300 else result
                trace.append(f"📥 **工具結果：**\n```\n{res_preview}\n```")

                if on_step:
                    self._run_callback(on_step, f"📥 **工具結果：**\n```\n{res_preview}\n```", loop)

            # 關鍵：用「新嘅 User Prompt」將結果掟返俾佢，逼佢做總結
            tool_context = "\n\n---\n".join(tool_results)
            msgs = [
                {"role": "system", "content": time_prompt + (messages[0].content if messages[0].role == "system" else "")},
                {"role": "user", "content": user_query},
                {"role": "user", "content": (
                    f"【系統：你剛才要求執行工具，以下是執行結果】\n"
                    + tool_context +
                    "\n\n請根據以上結果決定下一步。\n"
                    "【極度重要警告】：\n"
                    "1. 你剛才已經真正呼叫了工具，上面是真實的系統回傳結果。\n"
                    "2. 你絕對不可以自己捏造、假裝或重複之前的工具結果。\n"
                    "3. 如果結果顯示失敗，請嘗試換方法。如果成功，請直接回答用戶。\n"
                    "4. 如果你冇再叫用工具，請直接輸出最終答案。"

                )}
            ]

        # ================================================= #
        # 如果跳出迴圈（代表達到 8 步上限）
        timeout_msg = "⚠️ **已達到最大執行步數 (8步)，任務中斷。**"
        trace.append(timeout_msg)
        full_trace = "\n\n".join(trace)
        
        if on_step:
            # 加綠 tick，等 chat.py 知道已經 send 咗，唔好再重複
            self._run_callback(on_step, f"✅ **最終回答：**\n{full_trace}", loop)
            
        return full_trace

    def _run_callback(self, callback, text: str, loop=None):
        import asyncio
        if not loop:
            return
        try:
            asyncio.run_coroutine_threadsafe(callback(text), loop)
        except Exception as e:
            logger.warning("callback failed: %r", e)

    def count_tokens(self, text: str) -> int:
        return super().count_tokens(text)
