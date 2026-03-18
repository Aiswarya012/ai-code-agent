import re
from pathlib import Path

from config import settings

MAX_MATCHES = 50


def grep_code(
    pattern: str,
    workspace: Path,
    file_glob: str = "*.py",
    context_lines: int = 2,
) -> str:
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as exc:
        return f"Error: invalid regex pattern — {exc}"

    matches: list[str] = []
    files_searched = 0

    for file_path in sorted(workspace.rglob(file_glob)):
        if any(part in settings.SKIP_DIRS for part in file_path.parts):
            continue
        if not file_path.is_file():
            continue

        files_searched += 1

        try:
            lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except (OSError, PermissionError):
            continue

        rel_path = file_path.relative_to(workspace)

        for i, line in enumerate(lines):
            if not regex.search(line):
                continue

            start = max(0, i - context_lines)
            end = min(len(lines), i + context_lines + 1)

            snippet_lines: list[str] = []
            for j in range(start, end):
                marker = ">>>" if j == i else "   "
                snippet_lines.append(f"  {marker} {j + 1:>4} | {lines[j]}")

            matches.append(f"{rel_path}:{i + 1}\n" + "\n".join(snippet_lines))

            if len(matches) >= MAX_MATCHES:
                break

        if len(matches) >= MAX_MATCHES:
            break

    if not matches:
        return f"No matches for '{pattern}' in {files_searched} files (glob: {file_glob})."

    header = f"Found {len(matches)} match(es) across {files_searched} files"
    if len(matches) >= MAX_MATCHES:
        header += f" (showing first {MAX_MATCHES})"

    return header + "\n\n" + "\n\n".join(matches)
