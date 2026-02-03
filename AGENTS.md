## Project Summary
The Assistant Brain is a modular multi-agent system designed to act as a "Second Brain." It listens for input via Telegram (voice and text), routes requests to specialized agents (Archivist, Researcher, Writer), and processes tasks asynchronously using Redis. It stores knowledge in a hybrid system: SQLite for metadata and ChromaDB for semantic vector search (RAG).

## Tech Stack
- **Language**: Python
- **Framework**: PydanticAI (Agents), python-telegram-bot (Interface)
- **Database**: SQLite (Metadata), ChromaDB (Vector Store)
- **Queue**: Redis (Task Distribution)
- **Process Management**: PM2 (ecosystem.config.js)
- **Tools**: Playwright (Web Browsing), OpenAI Whisper (STT)

## Architecture
- `/main.py`: The Orchestrator/Producer. Handles Telegram input, STT, and routes intents to the task queue.
- `/worker.py`: The Consumer. Pops jobs from Redis, dynamically loads agent classes, executes them, and handles retries.
- `/agents/`: Contains specialized agent logic (archivist, researcher, writer).
- `/common/`: Shared contracts (Pydantic models), database utilities, and configuration.
- `/data/`: Local storage for SQLite and ChromaDB files.

## User Preferences
- No Obsidian integration.
- Use local ChromaDB/SQLite for simplicity.
- Reuse STT logic and API keys from previous voice journal app.
- Asynchronous task processing with job IDs.

## Project Guidelines
- Keep agent logic modular inside `/agents/`.
- Use Pydantic models for all data exchange (contracts).
- Implement backtracking and error handling in the worker (max 3 retries).
- Notify users via Telegram on task completion or failure.

## Common Patterns
- **Dynamic Agent Loading**: The worker loads agents by name using `importlib`.
- **RAG (Retrieval-Augmented Generation)**: All agents can query the `Archivist` for context from the semantic index.
- **Intent Routing**: A centralized LLM-based router in `main.py` determines the best agent for each request.
