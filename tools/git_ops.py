import subprocess
from pathlib import Path


def git_commit(message: str, workspace: Path) -> str:
    try:
        _run_git(["add", "-A"], workspace)
    except RuntimeError as exc:
        return f"Error staging files: {exc}"

    status = _run_git(["status", "--porcelain"], workspace)
    if not status.strip():
        return "Nothing to commit — working tree clean."

    try:
        output = _run_git(["commit", "-m", message], workspace)
    except RuntimeError as exc:
        return f"Error committing: {exc}"

    return f"Committed successfully.\n{output}"


def git_diff(workspace: Path) -> str:
    try:
        staged = _run_git(["diff", "--cached", "--stat"], workspace)
        unstaged = _run_git(["diff", "--stat"], workspace)
    except RuntimeError as exc:
        return f"Error getting diff: {exc}"

    parts: list[str] = []
    if staged.strip():
        parts.append(f"Staged:\n{staged}")
    if unstaged.strip():
        parts.append(f"Unstaged:\n{unstaged}")
    if not parts:
        return "No changes detected."
    return "\n".join(parts)


def _run_git(args: list[str], cwd: Path) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        msg = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(msg)
    return result.stdout
