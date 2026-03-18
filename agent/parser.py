import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from memory.vector_store import VectorStore
from tools.code_search import search_code
from tools.explain_function import explain_function
from tools.file_reader import read_file
from tools.file_writer import write_file
from tools.git_ops import git_commit, git_diff
from tools.grep_code import grep_code
from tools.list_files import list_files
from tools.run_command import run_command

logger = logging.getLogger("ai_agent.parser")

MAX_TOOL_OUTPUT_LENGTH = 50_000


class ToolExecutor:
    def __init__(self, workspace: Path, vector_store: VectorStore) -> None:
        self._workspace = workspace
        self._vector_store = vector_store
        self._registry: dict[str, Callable[..., str]] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register("read_file", self._read_file)
        self.register("write_file", self._write_file)
        self.register("search_code", self._search_code)
        self.register("list_files", self._list_files)
        self.register("grep_code", self._grep_code)
        self.register("run_command", self._run_command)
        self.register("explain_function", self._explain_function)
        self.register("git_commit", self._git_commit)
        self.register("git_diff", self._git_diff)

    def register(self, name: str, fn: Callable[..., str]) -> None:
        self._registry[name] = fn

    @property
    def available_tools(self) -> list[str]:
        return list(self._registry.keys())

    def execute(self, name: str, arguments: dict[str, Any]) -> str:
        if name not in self._registry:
            return f"Error: unknown tool '{name}'. Available: {', '.join(self.available_tools)}"

        logger.debug("Executing tool=%s args=%s", name, arguments)

        try:
            result = self._registry[name](**arguments)
        except TypeError as exc:
            return f"Error: invalid arguments for '{name}' — {exc}"
        except Exception as exc:
            return f"Error executing '{name}': {exc}"

        if len(result) > MAX_TOOL_OUTPUT_LENGTH:
            result = result[:MAX_TOOL_OUTPUT_LENGTH] + "\n\n... (output truncated)"

        logger.debug("Tool %s returned %d chars", name, len(result))
        return result

    def _read_file(self, path: str) -> str:
        return read_file(path, self._workspace)

    def _write_file(self, path: str, content: str) -> str:
        return write_file(path, content, self._workspace)

    def _search_code(self, query: str, top_k: int = 5) -> str:
        return search_code(query, self._vector_store, top_k=top_k)

    def _list_files(self, directory: str = ".") -> str:
        return list_files(directory, self._workspace)

    def _grep_code(
        self, pattern: str, file_glob: str = "*.py", context_lines: int = 2
    ) -> str:
        return grep_code(pattern, self._workspace, file_glob, context_lines)

    def _run_command(self, command: str) -> str:
        return run_command(command, self._workspace)

    def _explain_function(self, path: str, function_name: str) -> str:
        return explain_function(path, function_name, self._workspace)

    def _git_commit(self, message: str) -> str:
        return git_commit(message, self._workspace)

    def _git_diff(self) -> str:
        return git_diff(self._workspace)
