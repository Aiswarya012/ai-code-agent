import json
from pathlib import Path
from typing import Any


class ChatMemory:
    def __init__(self, storage_path: Path, max_messages: int = 50) -> None:
        self._path = storage_path
        self._max_messages = max_messages
        self._messages: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            self._messages = raw if isinstance(raw, list) else []

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._messages, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def add_user(self, content: str) -> None:
        self._messages.append({"role": "user", "content": content})
        self._trim()
        self._save()

    def add_assistant(self, content: str) -> None:
        self._messages.append({"role": "assistant", "content": content})
        self._trim()
        self._save()

    def get_messages(self) -> list[dict[str, Any]]:
        return [dict(m) for m in self._messages]

    def clear(self) -> None:
        self._messages = []
        self._save()

    def _trim(self) -> None:
        if len(self._messages) > self._max_messages:
            self._messages = self._messages[-self._max_messages :]

    @property
    def message_count(self) -> int:
        return len(self._messages)
