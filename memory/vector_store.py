import pickle
from dataclasses import dataclass, field
from pathlib import Path

import faiss
import numpy as np
from numpy.typing import NDArray
from sentence_transformers import SentenceTransformer

from config import settings


@dataclass
class ChunkMetadata:
    content: str
    file_path: str
    start_line: int
    end_line: int


@dataclass
class SearchResult:
    content: str
    file_path: str
    start_line: int
    end_line: int
    score: float


@dataclass
class VectorStore:
    data_dir: Path
    model_name: str = field(default_factory=lambda: settings.embedding_model)
    _index: faiss.IndexFlatIP | None = field(default=None, init=False, repr=False)
    _metadata: list[ChunkMetadata] = field(default_factory=list, init=False, repr=False)
    _model: SentenceTransformer | None = field(default=None, init=False, repr=False)

    @property
    def index_path(self) -> Path:
        return self.data_dir / "embeddings.index"

    @property
    def metadata_path(self) -> Path:
        return self.data_dir / "metadata.pkl"

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    @property
    def is_built(self) -> bool:
        return self.index_path.exists() and self.metadata_path.exists()

    def build_index(
        self,
        workspace: Path,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> int:
        chunk_size = chunk_size or settings.chunk_size
        chunk_overlap = chunk_overlap or settings.chunk_overlap

        chunks = self._collect_chunks(workspace, chunk_size, chunk_overlap)
        if not chunks:
            return 0

        texts = [c.content for c in chunks]
        embeddings = self._embed(texts)

        dimension = embeddings.shape[1]
        self._index = faiss.IndexFlatIP(dimension)
        self._index.add(embeddings)
        self._metadata = chunks

        self.data_dir.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(self.index_path))
        with open(self.metadata_path, "wb") as f:
            pickle.dump(self._metadata, f)

        return len(chunks)

    def load(self) -> None:
        if not self.is_built:
            msg = "Index not built. Run 'index' command first."
            raise FileNotFoundError(msg)
        self._index = faiss.read_index(str(self.index_path))
        with open(self.metadata_path, "rb") as f:
            self._metadata = pickle.load(f)  # noqa: S301

    def search(self, query: str, top_k: int | None = None) -> list[SearchResult]:
        top_k = top_k or settings.top_k
        if self._index is None:
            self.load()

        query_embedding = self._embed([query])
        assert self._index is not None
        scores, indices = self._index.search(query_embedding, top_k)

        results: list[SearchResult] = []
        for score, idx in zip(scores[0], indices[0], strict=False):
            if idx < 0:
                continue
            meta = self._metadata[idx]
            results.append(
                SearchResult(
                    content=meta.content,
                    file_path=meta.file_path,
                    start_line=meta.start_line,
                    end_line=meta.end_line,
                    score=float(score),
                )
            )
        return results

    def _embed(self, texts: list[str]) -> NDArray[np.float32]:
        embeddings = self.model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
        return np.array(embeddings, dtype=np.float32)

    def _collect_chunks(
        self,
        workspace: Path,
        chunk_size: int,
        chunk_overlap: int,
    ) -> list[ChunkMetadata]:
        chunks: list[ChunkMetadata] = []

        for file_path in self._iter_files(workspace):
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except (OSError, PermissionError):
                continue

            lines = content.splitlines()
            if not lines:
                continue

            rel_path = str(file_path.relative_to(workspace))
            step = max(1, chunk_size - chunk_overlap)

            for start in range(0, len(lines), step):
                end = min(start + chunk_size, len(lines))
                chunk_content = "\n".join(lines[start:end])
                if chunk_content.strip():
                    chunks.append(
                        ChunkMetadata(
                            content=chunk_content,
                            file_path=rel_path,
                            start_line=start + 1,
                            end_line=end,
                        )
                    )
                if end >= len(lines):
                    break

        return chunks

    def _iter_files(self, workspace: Path) -> list[Path]:
        files: list[Path] = []
        for item in workspace.rglob("*"):
            if any(part in settings.SKIP_DIRS for part in item.parts):
                continue
            if item.is_file() and item.suffix in settings.FILE_EXTENSIONS:
                files.append(item)
        return sorted(files)
