from dotenv import load_dotenv
load_dotenv()

from remote_agent.discord_bot import run_bot  # noqa: E402
# ================================================= #
if __name__ == "__main__":
    run_bot()
# ================================================= #
