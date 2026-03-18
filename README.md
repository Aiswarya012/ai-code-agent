# AI Code Agent

CLI-based AI codebase assistant powered by Groq API (Llama 3.3 70B). Understands, searches, and modifies code using tool-calling and RAG.

## Architecture

```
User (CLI)
    │
    ▼
┌──────────────────┐
│   Agent Core     │  ← reasoning loop (max 10 iterations)
│   (agent/core)   │
├──────────────────┤
│   Tool Layer     │  ← read_file, write_file, search_code, git_commit, git_diff
│   (tools/)       │
├──────────────────┤
│   Memory Layer   │  ← chat history (JSON) + vector store (FAISS)
│   (memory/)      │
├──────────────────┤
│   LLM            │  ← Groq API (OpenAI-compatible tool calling)
└──────────────────┘
```

**Agent Loop:**
1. User query → Groq with tool definitions
2. LLM responds with text OR tool calls
3. Tool calls are executed, results sent back to Groq
4. Loop repeats until LLM produces a final text response

## Features

- **Semantic code search** — FAISS + sentence-transformers embeddings over the entire codebase
- **File operations** — read and write files with diff previews for modifications
- **Git integration** — commit changes and view diffs directly from the agent
- **Conversation memory** — JSON-backed chat history persists across sessions
- **Multi-iteration reasoning** — agent can chain multiple tool calls per query
- **Workspace isolation** — each project gets its own index and memory (`.ai_agent/` directory)
- **Path sandboxing** — file operations are restricted to the workspace

## Setup

```bash
cd ai_code_agent

python3.11 -m venv .venv
source .venv/bin/activate

pip install -e .
```

Set your API key:

```bash
export GROQ_API_KEY="gsk_..."
```

Or create a `.env` file in the project root:

```
GROQ_API_KEY=gsk_...
```

## Usage

### Build the vector index (required before `search_code` works)

```bash
python main.py index --workspace /path/to/your/project
```

### Ask a question

```bash
python main.py ask "Explain the architecture of this project" -w /path/to/your/project
```

### Interactive chat mode

```bash
python main.py chat -w /path/to/your/project
```

### Clear conversation memory

```bash
python main.py clear -w /path/to/your/project
```

### Examples

```bash
python main.py ask "What does the train_pipeline.py do?"
python main.py ask "Find where API endpoints are defined"
python main.py ask "Refactor config.py to use Pydantic settings"
python main.py ask "Add type hints to all functions in src/models/train.py"
```

## Configuration

Environment variables:

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | (required) | Groq API key |
| `MODEL` | `llama-3.3-70b-versatile` | Groq model ID |
| `MAX_TOKENS` | `4096` | Max response tokens |
| `MAX_AGENT_ITERATIONS` | `10` | Max tool-call loops |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformer model |
| `CHUNK_SIZE` | `80` | Lines per code chunk |
| `CHUNK_OVERLAP` | `20` | Overlap between chunks |
| `TOP_K` | `5` | Search results to return |

## Project Structure

```
ai_code_agent/
├── main.py                 # CLI entry point (typer)
├── config.py               # Pydantic settings
├── agent/
│   ├── core.py             # Agent reasoning loop
│   ├── prompt.py           # System prompt + Groq tool definitions
│   └── parser.py           # Tool execution registry
├── tools/
│   ├── file_reader.py      # read_file
│   ├── file_writer.py      # write_file (with diff)
│   ├── code_search.py      # search_code (FAISS)
│   └── git_ops.py          # git_commit, git_diff
├── memory/
│   ├── chat_memory.py      # JSON conversation history
│   └── vector_store.py     # FAISS index + embeddings
├── utils/
│   └── logger.py           # Logging with rich
├── pyproject.toml
├── requirements.txt
└── README.md
```

## How the Vector Index Works

1. Scans workspace for source files (`.py`, `.js`, `.ts`, `.go`, `.rs`, `.java`, `.yaml`, `.yml`, `.toml`, `.json`, `.md`, `.sh`, `.sql`)
2. Skips `.git`, `__pycache__`, `venv`, `node_modules`, etc.
3. Chunks files by lines (default 80 lines, 20 overlap)
4. Embeds with `all-MiniLM-L6-v2` (384 dimensions)
5. Stores in FAISS `IndexFlatIP` (cosine similarity via normalized vectors)
6. Persists to `{workspace}/.ai_agent/embeddings.index` + `metadata.pkl`
