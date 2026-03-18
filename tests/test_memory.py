from pathlib import Path

import pytest

from memory.chat_memory import ChatMemory


@pytest.fixture()
def memory(tmp_path: Path) -> ChatMemory:
    return ChatMemory(tmp_path / "memory.json")


class TestChatMemory:
    def test_add_and_retrieve(self, memory: ChatMemory) -> None:
        memory.add_user("hello")
        memory.add_assistant("hi")
        messages = memory.get_messages()
        assert len(messages) == 2
        assert messages[0] == {"role": "user", "content": "hello"}
        assert messages[1] == {"role": "assistant", "content": "hi"}

    def test_persistence(self, tmp_path: Path) -> None:
        path = tmp_path / "mem.json"
        m1 = ChatMemory(path)
        m1.add_user("test")
        m1.add_assistant("response")

        m2 = ChatMemory(path)
        assert m2.message_count == 2

    def test_clear(self, memory: ChatMemory) -> None:
        memory.add_user("x")
        memory.clear()
        assert memory.message_count == 0

    def test_trim(self, tmp_path: Path) -> None:
        memory = ChatMemory(tmp_path / "mem.json", max_messages=4)
        for i in range(10):
            memory.add_user(f"msg {i}")
        assert memory.message_count == 4

    def test_get_returns_copy(self, memory: ChatMemory) -> None:
        memory.add_user("original")
        messages = memory.get_messages()
        messages.append({"role": "user", "content": "injected"})
        assert memory.message_count == 1
