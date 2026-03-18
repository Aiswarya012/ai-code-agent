# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run

```bash
pip install -r requirements.txt
pip install -e ".[dev]"

python main.py ask "your question" -w /path/to/codebase
python main.py index -w /path/to/codebase
python main.py chat -w /path/to/codebase
python main.py clear -w /path/to/codebase
```

## Lint, Type Check, Test

```bash
ruff check .
ruff format --check .
mypy agent/ tools/ memory/ utils/ config.py main.py --ignore-missing-imports
pytest tests/ -v --tb=short
pytest tests/test_tools.py::test_read_file_returns_content -v  # single test
```

## Architecture

**Agent loop** (`agent/core.py`): `AgentCore.run()` builds a message list (system prompt + chat memory + user query), calls Groq LLM, processes tool calls in a loop (max 10 iterations), then saves the exchange to memory. Includes a recovery mechanism for Groq's known bug where Llama generates malformed XML-style tool calls instead of proper JSON — regex-parses the failed generation from the error body and re-injects results.

**Tool system** (`agent/parser.py` + `tools/`): `ToolExecutor` uses a registry pattern mapping tool names to handler functions. 9 tools: `read_file`, `write_file`, `search_code`, `list_files`, `grep_code`, `run_command`, `explain_function`, `git_commit`, `git_diff`. Tool definitions in OpenAI function-calling format live in `agent/prompt.py`. All tool output is truncated at 50KB.

**RAG** (`memory/vector_store.py`): FAISS `IndexFlatIP` with `all-MiniLM-L6-v2` sentence-transformers embeddings. Chunks files by lines (80 lines, 20 overlap). Index and metadata persisted to `.ai_agent/` inside the target workspace.

**Configuration** (`config.py`): Pydantic Settings with `.env` support. Key env var: `GROQ_API_KEY`. Model defaults to `llama-3.3-70b-versatile`.

**Per-workspace isolation**: All agent state (vector index, metadata, chat memory, logs) lives in `<workspace>/.ai_agent/`.

## Key Constraints

- Groq SDK's `chat.completions.create()` has strict overloads that don't match `list[dict[str, Any]]` — use `# type: ignore[call-overload,no-any-return]` on those calls.
- `run_command` tool uses an allowlist/blocklist for shell commands — update `tools/run_command.py` when adding permitted commands.
- CI uses `pip install -r requirements.txt` (not editable install) to avoid package name validation issues with mypy.
- Package name is `ai_code_agent` (underscore) in `pyproject.toml` — do not use hyphens.
