from pathlib import Path

from config import settings


def list_files(directory: str, workspace: Path) -> str:
    target = (workspace / directory).resolve()
    if not str(target).startswith(str(workspace.resolve())):
        return f"Error: access denied — '{directory}' is outside the workspace."

    if not target.exists():
        return f"Error: directory not found — '{directory}'"

    if not target.is_dir():
        return f"Error: '{directory}' is not a directory."

    entries: list[str] = []
    try:
        for item in sorted(target.iterdir()):
            if item.name in settings.SKIP_DIRS:
                continue
            if item.name.startswith(".") and item.name != ".env":
                continue

            rel = item.relative_to(workspace)
            if item.is_dir():
                child_count = sum(
                    1
                    for c in item.iterdir()
                    if c.name not in settings.SKIP_DIRS and not c.name.startswith(".")
                )
                entries.append(f"  {rel}/  ({child_count} items)")
            else:
                size = item.stat().st_size
                entries.append(f"  {rel}  ({_format_size(size)})")
    except PermissionError as exc:
        return f"Error listing '{directory}': {exc}"

    if not entries:
        return f"'{directory}' is empty."

    header = f"--- {directory} ({len(entries)} entries) ---"
    return header + "\n" + "\n".join(entries)


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"
