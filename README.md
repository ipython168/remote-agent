# Remote Agent: Multi-Agent AI System with Discord Control

A production-grade, asynchronous multi-agent AI system. It allows a user to control a remote worker machine (Windows/Linux) via a Discord bot, leveraging LLMs for reasoning, tool execution, and stateful conversation management.

## 🏗️ System Architecture
The system is built with a highly modular architecture, following the **Adapter Pattern** and **Event-Driven** principles.

- **Brain Abstraction Layer (`brain/`)**: Supports multiple LLM providers (OpenAI, Gemini, Ollama, Colab) via a unified interface. Easily swappable at runtime.
- **Tool Execution Engine (`tools/`)**: Implements dynamic Function Calling (ReAct pattern). The AI can autonomously decide to execute shell commands, read/write files, or perform web searches.
- **Stateful History (`history/`)**: Persists conversation context and tool outputs using JSON storage, handling long-term memory per Discord channel/user.
- **Persona Management (`persona/`)**: Configurable YAML-based system prompts to change the AI's behavior (e.g., "Coder", "Trader", "Imager").
- **Discord Integration (`discord_bot/`)**: Built with `discord.py` Cogs, utilizing asynchronous event loops to handle multiple concurrent requests without blocking.

## 🛠️ Tech Stack & Skills Demonstrated
- **Languages & Frameworks**: Python 3.10+, `discord.py` (Async/Await), `pydantic` (Data validation).
- **AI/LLM**: OpenAI API, Google Gemini, Ollama, Prompt Engineering, ReAct (Reasoning + Acting) paradigm.
- **Software Architecture**: Object-Oriented Design (OOP), Adapter Pattern, Dependency Injection.
- **DevOps**: Modular package structure (`pyproject.toml`), Environment Variables (`.env`), Logging (`logging.yaml`).

## 🚀 Quick Start
1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -e .
   ```
3. Configure your `.env` (API keys) and `configs/settings.yaml`.
4. Run the bot:
   ```bash
   python -m remote_agent
   ```

## 📌 Roadmap
- **Stage 1 (Completed)**: Text chat, memory, and persona management.
- **Stage 2 (Completed)**: Single-step agent execution with Discord UI buttons for human-in-the-loop confirmation.
- **Stage 3 (In Progress)**: Fully autonomous loop (ReAct) with long-running task planning and error recovery.





