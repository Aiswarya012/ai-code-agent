from pathlib import Path

from config import Settings


class TestSettings:
    def test_defaults(self) -> None:
        s = Settings(groq_api_key="test-key")
        assert s.model == "llama-3.3-70b-versatile"
        assert s.max_tokens == 4096
        assert s.max_agent_iterations == 10
        assert s.top_k == 5
        assert s.chunk_size == 80
        assert s.chunk_overlap == 20

    def test_resolve_data_dir(self) -> None:
        s = Settings(groq_api_key="test-key")
        ws = Path("/tmp/project")
        assert s.resolve_data_dir(ws) == Path("/tmp/project/.ai_agent")

    def test_skip_dirs(self) -> None:
        s = Settings(groq_api_key="test-key")
        assert ".git" in s.SKIP_DIRS
        assert "__pycache__" in s.SKIP_DIRS
        assert "node_modules" in s.SKIP_DIRS
