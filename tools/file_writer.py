import difflib
from pathlib import Path


def write_file(path: str, content: str, workspace: Path) -> str:
    target = (workspace / path).resolve()
    if not str(target).startswith(str(workspace.resolve())):
        return f"Error: access denied — '{path}' is outside the workspace."

    diff_output = ""
    if target.exists():
        try:
            old_content = target.read_text(encoding="utf-8", errors="replace")
        except (OSError, PermissionError) as exc:
            return f"Error reading existing file '{path}': {exc}"

        diff_lines = list(
            difflib.unified_diff(
                old_content.splitlines(keepends=True),
                content.splitlines(keepends=True),
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
                lineterm="",
            )
        )
        if diff_lines:
            diff_output = "\n".join(diff_lines)
        else:
            return f"No changes — '{path}' already has the same content."

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    except (OSError, PermissionError) as exc:
        return f"Error writing '{path}': {exc}"

    result = f"Successfully wrote {len(content.splitlines())} lines to '{path}'."
    if diff_output:
        result += f"\n\nDiff:\n{diff_output}"
    else:
        result += " (new file created)"

    return result
