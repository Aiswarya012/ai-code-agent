from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    groq_api_key: str = Field(default="")
    model: str = Field(default="llama-3.3-70b-versatile")
    max_tokens: int = Field(default=4096)
    max_agent_iterations: int = Field(default=10)
    embedding_model: str = Field(default="all-MiniLM-L6-v2")
    chunk_size: int = Field(default=80)
    chunk_overlap: int = Field(default=20)
    top_k: int = Field(default=5)
    workspace: Path = Field(default_factory=Path.cwd)
    data_dir: Path = Field(default=Path("data"))

    SKIP_DIRS: set[str] = {
        ".git", "__pycache__", ".venv", "venv", "node_modules",
        ".mypy_cache", ".ruff_cache", ".pytest_cache", "dist",
        "build", ".eggs", ".tox", "data",
    }
    FILE_EXTENSIONS: set[str] = {
        ".py", ".js", ".ts", ".go", ".rs", ".java", ".yaml",
        ".yml", ".toml", ".json", ".md", ".sh", ".sql",
    }

    def resolve_data_dir(self, workspace: Path) -> Path:
        return workspace / ".ai_agent"


settings = Settings()
