from pathlib import Path
from typing import Any


def build_system_prompt(workspace: Path) -> str:
    return f"""You are an expert AI code assistant operating on a codebase at: {workspace}

Your capabilities:
- Read and analyze source files
- Write and modify files (always show diffs for existing files)
- Search the codebase semantically using vector embeddings
- List directory contents to explore project structure
- Grep for patterns across files with context
- Run safe shell commands (pytest, ruff, mypy, etc.)
- Extract and analyze individual Python functions with full metadata
- Commit changes to git
- View git diff status

Rules:
- Always read a file before modifying it.
- When modifying code, preserve the existing style and conventions.
- When searching, use specific technical queries for best results.
- Explain your reasoning before making changes.
- If a task is ambiguous, ask for clarification.
- For write_file, provide the COMPLETE file content — not partial patches.
- Paths are relative to the workspace root.
- Use list_files to explore before reading specific files.
- Use grep_code for exact pattern matching, search_code for semantic/conceptual search.
- Use explain_function to inspect a specific function before modifying it.

IMPORTANT: When you need to use a tool, use the provided function calling mechanism.
Do NOT write tool calls as XML tags like <function=name>.
Do NOT write tool calls as plain text.
Use the structured tool/function calling interface provided by the API.
"""


def get_tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": (
                    "Read the contents of a file in the workspace. "
                    "Returns the file content with line numbers. "
                    "Use this before modifying any file."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": (
                                "Relative path to the file from workspace root. "
                                "Example: 'config.py' or 'agent/core.py'"
                            ),
                        },
                    },
                    "required": ["path"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": (
                    "Write content to a file in the workspace. "
                    "Creates the file if it doesn't exist. "
                    "If the file exists, a unified diff is generated and returned. "
                    "Always provide the COMPLETE file content."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": (
                                "Relative path to the file from workspace root. "
                                "Example: 'config.py' or 'agent/core.py'"
                            ),
                        },
                        "content": {
                            "type": "string",
                            "description": "Complete file content to write.",
                        },
                    },
                    "required": ["path", "content"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_code",
                "description": (
                    "Semantic search across the codebase using vector embeddings. "
                    "Best for conceptual queries like 'error handling' or 'database connection'. "
                    "Returns top-k results with file paths, line numbers, and scores. "
                    "Requires the index to be built first."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language or code search query.",
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Number of results to return.",
                            "default": 5,
                        },
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": (
                    "List contents of a directory in the workspace. "
                    "Shows files with sizes and directories with item counts. "
                    "Use this to explore the project structure."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "directory": {
                            "type": "string",
                            "description": (
                                "Relative path to directory. Use '.' for workspace root. "
                                "Example: '.', 'agent', 'tools'"
                            ),
                            "default": ".",
                        },
                    },
                    "required": [],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "grep_code",
                "description": (
                    "Search for a regex pattern across files in the workspace. "
                    "Returns matching lines with surrounding context. "
                    "Best for exact pattern matching like function names, imports, or strings. "
                    "Use search_code instead for conceptual/semantic queries."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": (
                                "Regex pattern to search for. Case-insensitive. "
                                "Example: 'def run_agent', 'import faiss', 'TODO'"
                            ),
                        },
                        "file_glob": {
                            "type": "string",
                            "description": "File glob pattern to filter files.",
                            "default": "*.py",
                        },
                        "context_lines": {
                            "type": "integer",
                            "description": "Number of lines of context around each match.",
                            "default": 2,
                        },
                    },
                    "required": ["pattern"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "run_command",
                "description": (
                    "Run a shell command in the workspace directory. "
                    "Only safe commands are allowed: python, pytest, ruff, mypy, black, "
                    "pip, ls, wc, head, tail, cat, find, tree. "
                    "Destructive commands (rm, sudo, chmod, etc.) are blocked. "
                    "Timeout: 30 seconds."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": (
                                "Shell command to execute. "
                                "Example: 'pytest tests/ -v', 'ruff check src/'"
                            ),
                        },
                    },
                    "required": ["command"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "explain_function",
                "description": (
                    "Extract and analyze a specific Python function from a file. "
                    "Returns the function signature, arguments, return type, "
                    "decorators, docstring, and full source code. "
                    "If the function is not found, lists all available functions."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": (
                                "Relative path to the Python file. Example: 'agent/core.py'"
                            ),
                        },
                        "function_name": {
                            "type": "string",
                            "description": (
                                "Name of the function to analyze. Example: 'run_agent', '__init__'"
                            ),
                        },
                    },
                    "required": ["path", "function_name"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "git_commit",
                "description": (
                    "Stage all changes and create a git commit with the given message."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Commit message.",
                        },
                    },
                    "required": ["message"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "git_diff",
                "description": ("Show current staged and unstaged changes in the workspace."),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                    "additionalProperties": False,
                },
            },
        },
    ]
