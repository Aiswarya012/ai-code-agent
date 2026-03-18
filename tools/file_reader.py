from pathlib import Path


def read_file(path: str, workspace: Path) -> str:
    target = (workspace / path).resolve()
    if not str(target).startswith(str(workspace.resolve())):
        return f"Error: access denied — '{path}' is outside the workspace."

    if not target.exists():
        return f"Error: file not found — '{path}'"

    if not target.is_file():
        return f"Error: '{path}' is not a file."

    try:
        content = target.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError) as exc:
        return f"Error reading '{path}': {exc}"

    lines = content.splitlines()
    numbered = [f"{i + 1:>4} | {line}" for i, line in enumerate(lines)]
    return f"--- {path} ({len(lines)} lines) ---\n" + "\n".join(numbered)
