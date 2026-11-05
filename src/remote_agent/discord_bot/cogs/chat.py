# src/remote_agent/discord_bot/cogs/chat.py
from __future__ import annotations
import asyncio
import discord
from discord.ext import commands
from discord.ext import bridge
from remote_agent.brain.base import Message
# ================================================= #
import logging
logger = logging.getLogger(__name__)
# ================================================= #
class Chat(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
# ================================================= #
    def _build_messages(self, channel_id: int, user_input: str) -> list[Message]:
        history = self.bot.history.load(channel_id)
        messages: list[Message] = []
        if self.bot.system_prompt:
            # 根據當前 Persona 決定要唔要加安全規則
            allowed_tools = self.bot.persona.get("tools", [])

            # 1. 所有人共用嘅工具/延續規則 (只要有工具就加)
            system_content = self.bot.system_prompt
            if allowed_tools:
                system_content += (
                    "\n\n## 🛠️ 通用工具規則\n"
                    "- **延續任務規則**：如果用戶只係打「繼續」、「go on」或「再做」，代表你要根據對話歷史，接住頭先未完成嘅任務繼續做（例如換個方法再試、或者行下一步），千萬唔好當係新問題重新問用戶。\n"
                )

            # 2. Coder 專屬嘅嚴格安全規則 (只限有 exec 權限)            
            if "exec" in allowed_tools:
                system_content += (
                    "\n\n## 🛡️ 系統安全與工具規則 (最高優先級)\n"
                    "- **延續任務規則**：如果用戶只係打「繼續」、「go on」或者「再做」等意思，代表你要根據對話歷史，接住頭先未完成嘅任務繼續做（例如換個方法再試、或者行下一步），千萬唔好當係新問題重新問用戶。\n"
                    "- **禁止幻覺規則**：你只可以根據 `exec` 工具回傳嘅真實結果回答用戶。如果你冇真正叫用工具，或者工具冇回傳成功，你絕對不可以假裝任務已完成或捏造檔案路徑。\n"
                    "- 你的 Google Drive 專案路徑是 `/content/drive/MyDrive/develop/Projects/`。唔好用 `find /content` 掃描全機，會 Timeout。\n"
                    "- **專案結構**：每個 repo 嘅 source code 都放喺 `Projects/{repo-name}/src/{module_name}`。例如 `ifunc` repo 嘅 code 就喺 `Projects/ifunc/src/ifunc`。\n"
                    "- 搵 Code 請用 `grep` 工具，`path` 指向 `src/ifunc`。唔好用 `grep -rn` 掃描成個 repo。\n"
                    "- 寫程式、下載檔案一律在 `/content` 進行。\n"
                    "- **工作目錄限制**：你嘅 `exec` 工具預設啟動位置永遠係 `/content`。每次 `exec` 都係一個全新嘅 Shell。\n"
                    "- **嚴禁修改 Google Drive**：只准用 `cat`, `grep`, `sed`, `ls`。不准 `rm`, `mv`, `cp`, `touch`, `>`。\n"
                    "- 安裝套件用 `exec` (例如 `pip install yt-dlp`)。\n"
                    "- 建立/修改檔案後，必須用 `cat` 或 `ls` 驗證。\n"
                ) 
                
            messages.append(Message(role="system", content=system_content))
        messages.extend(history)
        messages.append(Message(role="user", content=user_input))
        return messages
# ================================================= #
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return  # commands.Bot 會自己處理
        if not message.content.strip():
            return

        logger.info("msg from %s: %s", message.author, message.content[:80])

        async with message.channel.typing():
            messages = self._build_messages(message.channel.id, message.content)
            import asyncio
            current_loop = asyncio.get_running_loop()
            step_sent = False

            # 定義實時輸出 Callback
            async def send_step(text):
                nonlocal step_sent
                if "✅ **最終回答：**" in text:
                    step_sent = True

                await message.channel.send(text)

            try:
                from remote_agent.tools import get_tools_for_persona
                allowed_tools = self.bot.persona.get("tools", [])
                filtered_tools = get_tools_for_persona(allowed_tools)

                reply = await asyncio.to_thread(
                    self.bot.brain.chat,
                    messages,
                    max_tokens=2048,  # << 沒有 max_output_tokens
                    tools=filtered_tools,
                    on_step=send_step,
                    loop=current_loop,

                )                
                logger.info("reply: %s", reply[:80])
            except Exception as e:
                await message.reply(f"❌ Brain error: `{e}`")
                return

        # 清理可能殘留嘅 ✅ 字眼（只限普通對話）
        #if reply.startswith("✅ **最終回答：**\n"):
        #    reply = reply.replace("✅ **最終回答：**\n", "", 1)

        # 如果 AI 乜都冇回，俾個預設答案
        if not reply or not reply.strip():
            reply = "⚠️ 任務執行中斷，或者 AI 沒有給出回應。請檢查 Log 或重試。"


        self.bot.history.append(message.channel.id, Message(role="user", content=message.content))
        self.bot.history.append(message.channel.id, Message(role="assistant", content=reply))

        # 如果 on_step 已經 send 咗最終答案，就唔好重複 send
        if not step_sent:
            await self._send_long(message, reply)
# ================================================= #
    async def _send_long(self, message: discord.Message, text: str, limit: int = 1900):
        if len(text) <= limit:
            await message.reply(text)
            return
        for i in range(0, len(text), limit):
            chunk = text[i:i + limit]
            await message.channel.send(chunk)
# ================================================= #
    @commands.command(name="reset")
    async def reset(self, ctx: commands.Context):
        self.bot.history.reset(ctx.channel.id)
        await ctx.reply("🧹 History cleared.")
# ================================================= #
    @commands.command(name="persona")
    async def persona(self, ctx: commands.Context):
        await ctx.reply(f"```\n{self.bot.system_prompt}\n```")
# ================================================= #
    @commands.command(name="switch")
    async def switch(self, ctx: commands.Context, name: str): 
        logger.info("switch called: name=%s, ctx.id=%s", name, id(ctx))
        from remote_agent.persona import load_persona, render_system_prompt
        try:
            p = load_persona(self.bot.settings["persona"]["path"], active=name)
        except (KeyError, ValueError) as e:
            await ctx.reply(f"❌ {e}")
            return
        self.bot.persona = p
        self.bot.system_prompt = render_system_prompt(p)
        self.bot.history.active_persona = name
        await ctx.reply(f"✅ 已切換去 `{name}`（{p.get('name')}）")
# ================================================= #
    @commands.command(name="personas")
    async def personas(self, ctx: commands.Context):
        import yaml
        from pathlib import Path
        cfg_path = self.bot.settings["persona"]["path"]
        p = Path(cfg_path)
        if not p.is_absolute():
            from remote_agent.config.loader import REPO_ROOT
            p = REPO_ROOT / p
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        if "personas" not in data:
            await ctx.reply("呢個 persona 檔冇多個 persona")
            return
        lines = [f"- `{k}` — {v.get('name', '?')}" for k, v in data["personas"].items()]
        await ctx.reply("可用 persona：\n" + "\n".join(lines))
# ================================================= #
    @commands.command(name="history")
    async def history(self, ctx: commands.Context, n: int = 10):
        msgs = self.bot.history.load(ctx.channel.id)
        if not msgs:
            await ctx.reply("冇 history")
            return
        tail = msgs[-n:]
        lines = [f"`{m.role}`: {m.content[:80]}" for m in tail]
        await ctx.reply("\n".join(lines)[:1900])
# ================================================= #
    @commands.command(name="tokens")
    async def tokens(self, ctx: commands.Context):
        msgs = self.bot.history.load(ctx.channel.id)
        history_tokens = sum(self.bot.brain.count_tokens(m.content) for m in msgs)
        system_tokens = self.bot.brain.count_tokens(self.bot.system_prompt)
        max_tokens = self.bot.history.max_tokens or self.bot.brain.max_input_tokens
        total = history_tokens + system_tokens
        pct = total / max_tokens * 100 if max_tokens else 0

        lines = [
            f"**Persona**: `{self.bot.history.active_persona}`",
            f"**History msgs**: {len(msgs)}",
            f"**System tokens**: {system_tokens:,}",
            f"**History tokens**: {history_tokens:,}",
            f"**Total**: {total:,} / {max_tokens:,} ({pct:.1f}%)",
            f"**Brain max**: {self.bot.brain.max_input_tokens:,}",
        ]
        await ctx.reply("\n".join(lines))
# ================================================= #
    @commands.command(name="model")
    async def set_model(self, ctx: commands.Context, model_name: str = None):
        from remote_agent.brain.colab import MODEL_LIST

        """切換 AI 模型 (例如: !model google/gemini-3.8-flash)"""
        if not model_name:
            current = getattr(self.bot.brain, "model", "unknown")
            available = "\n".join([f"- `{m}`" for m in MODEL_LIST])
            await ctx.reply(f"當前模型：`{current}`\n\n**可用模型：**\n{available}\n\n用法：`!model <model_name>`")

            return

        if not hasattr(self.bot.brain, "model"):
            await ctx.reply("❌ 當前 Brain 唔支援切換 Model。")
            return

        # 檢查 Model 名有冇打錯
        if model_name not in MODEL_LIST:
            available = "\n".join([f"- `{m}`" for m in MODEL_LIST])
            await ctx.reply(f"❌ 找不到模型 `{model_name}`。\n\n**可用模型：**\n{available}")
            return

        old_model = self.bot.brain.model
        self.bot.brain.model = model_name
        await ctx.reply(f"✅ 已切換 Model：`{old_model}` ➡️ `{model_name}`\n(注意：重啟 Bot 後會還原為設定檔預設值)")
# ================================================= #
    @commands.command(name="compact")
    async def compact(self, ctx: commands.Context):
        from remote_agent.brain.base import Message

        msgs = self.bot.history.load(ctx.channel.id)
        if len(msgs) < 3:
            await ctx.reply("對話太短，唔使壓縮")
            return

        original_tokens = sum(self.bot.brain.count_tokens(m.content) for m in msgs)

        # 叫 LLM 總結
        summary_prompt = (
            "以下係一段對話紀錄。請將佢總結成重點，"
            "目標長度：中文 750-1000 字，英文對應比例（約 575-770 words）"
            "保留：人名、數字、決定、未完成嘅 task、關鍵 context。"
            "唔好加評論，唔好加開場白，直接 output 總結。"
        )

        convo_text = "\n".join(f"[{m.role}] {m.content}" for m in msgs)
        compact_messages = [
            Message(role="system", content=summary_prompt),
            Message(role="user", content=convo_text),
        ]

        async with ctx.channel.typing():
            try:
                summary = await asyncio.to_thread(
                    self.bot.brain.chat,
                    compact_messages,
                    max_tokens=8192,
                )
            except Exception as e:
                await ctx.reply(f"❌ 壓縮失敗：{e}")
                return

        # 用 summary 取代 history
        new_msgs = [Message(role="assistant", content=f"[對話總結] {summary}")]
        self.bot.history.save(ctx.channel.id, new_msgs)

        new_tokens = sum(self.bot.brain.count_tokens(m.content) for m in new_msgs)
        logger.info("compact: %d msgs (%d tok) → %d msgs (%d tok)", len(msgs), original_tokens, len(new_msgs), new_tokens)
        
        await ctx.reply(
            f"✅ 壓縮完成\n"
            f"**原本**: {len(msgs)} msgs, ~{original_tokens:,} tokens\n"
            f"**壓縮後**: {len(new_msgs)} msg, ~{new_tokens:,} tokens"
        )
# ================================================= #
    @commands.command(name="cmd")
    async def commands_list(self, ctx: commands.Context):
        cmds = [
            ("!reset", "清空當前 persona 嘅對話歷史"),
            ("!persona", "睇當前 persona system prompt"),
            ("!personas", "列出所有可用 persona"),
            ("!switch <name>", "切換 persona"),
            ("!history [n]", "睇最近 n 條對話"),
            ("!tokens", "睇當前 history token 用量"),
            ("!compact", "壓縮 history（總結成 1000 字以內）"),
            ("!exec <cmd>", "手動執行 shell command（預設喺 /content 執行）"),
            ("!clear [n]", "批量刪除頻道訊息（預設 20 條）"),
            ("!cmd", "列出所有 command"),
            ("!model", "轉 model"),            
            ("<普通訊息>", "同 AI 傾偈"),
        ]
        lines = [f"`{c}` — {d}" for c, d in cmds]
        await ctx.reply("**Commands**\n" + "\n".join(lines))
# ================================================= #
    @commands.command(name="exec")
    async def exec_cmd(self, ctx: commands.Context, *, cmd: str):
        """手動執行 shell command（預設喺 /content 執行）。"""
        from remote_agent.tools.executor import run_command

        logger.info("exec command from %s: %s", ctx.author, cmd)
        
        msg = await ctx.reply(f"⏳ 正在執行：`{cmd}` ...")
        
        # 執行 (掉去 thread 避免 block event loop)
        result = await asyncio.to_thread(run_command, cmd)

        # 因為 output 可能好長，我哋用 code block 包住
        formatted_result = f"**執行結果：**\n```bash\n{result}\n```"
       
        await msg.edit(content="✅ 執行完成。")
        await self._send_long(ctx.message, formatted_result)
# ================================================= #
    @commands.command(name="clear")
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx: commands.Context, limit: int = 20):
        """批量刪除頻道訊息（預設 20 條，最多 100 條）。"""
        limit = min(max(limit, 1), 100)  # 限制 1~100
        
        # 先刪除你打嘅 !clear 指令
        await ctx.message.delete()

        # 批量刪除
        deleted = await ctx.channel.purge(limit=limit)
        
        # 發送提示，5 秒後自動刪除
        msg = await ctx.send(f"🧹 已刪除 {len(deleted)} 條訊息。")
        await asyncio.sleep(5)
        await msg.delete()
# ================================================= #
def setup(bot: commands.Bot):
    bot.add_cog(Chat(bot))
# ================================================= #





