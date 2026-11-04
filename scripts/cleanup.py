"""Clean up stale Discord bot instances."""
import asyncio
import gc

# ================================================= #
import logging
logger = logging.getLogger(__name__)
# ================================================= # 
async def cleanup() -> int:
    """Cancel bot tasks + close all RemoteAgentBot instances. Returns count closed."""
    async def _do_cleanup():
        # 1. cancel bot tasks
        cancelled = 0
        tasks_to_wait = []
        for t in asyncio.all_tasks():
            if t is asyncio.current_task():
                continue
            coro = t.get_coro()
            name = str(coro)
            if ("Client.start" in name) or ("_start" in name and "run_colab" in name):
                logger.info("cancelling task: %s", t.get_name())
                t.cancel()
                tasks_to_wait.append(t)
                cancelled += 1
        
        if tasks_to_wait:
            await asyncio.gather(*tasks_to_wait, return_exceptions=True)
        
        # 強制讓出控制權，俾 Event Loop 處理殘留背景任務
        await asyncio.sleep(0.2)

        # 2. close bot objects
        closed = 0
        for obj in gc.get_objects():
            if type(obj).__name__ == "RemoteAgentBot":
                try:
                    if hasattr(obj, "is_closed") and not obj.is_closed():
                        await obj.close()
                        closed += 1
                        logger.info("closed stale bot: %s", getattr(obj, "user", None))
                except Exception as e:
                    logger.warning("close failed: %r", e)
        
        return cancelled, closed

    # 模擬手動行兩次 cleanup 嘅效果
    logger.info("cleanup pass 1...")
    c1, cl1 = await _do_cleanup()
    
    logger.info("cleanup pass 2...")
    c2, cl2 = await _do_cleanup()

    total_c = c1 + c2
    total_cl = cl1 + cl2
    logger.info("cleanup done: cancelled=%d closed=%d", total_c, total_cl)
    return total_cl
# ================================================= #  
def cleanup_sync() -> int:
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(cleanup())
# ================================================= # 
