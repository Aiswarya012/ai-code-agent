from memory.vector_store import SearchResult, VectorStore


def search_code(query: str, vector_store: VectorStore, top_k: int = 5) -> str:
    try:
        results: list[SearchResult] = vector_store.search(query, top_k=top_k)
    except FileNotFoundError:
        return "Error: vector index not built. Run 'python main.py index' first."
    except Exception as exc:
        return f"Error during search: {exc}"

    if not results:
        return "No relevant code found for the query."

    output_parts: list[str] = []
    for i, r in enumerate(results, 1):
        header = f"[{i}] {r.file_path} (lines {r.start_line}-{r.end_line}) — score: {r.score:.3f}"
        output_parts.append(f"{header}\n{r.content}")

    return "\n\n---\n\n".join(output_parts)
