import subprocess
from pathlib import Path

ALLOWED_COMMANDS = {
    "python",
    "pytest",
    "ruff",
    "mypy",
    "black",
    "pip",
    "ls",
    "wc",
    "head",
    "tail",
    "cat",
    "find",
    "tree",
}

BLOCKED_PATTERNS = {
    "rm ",
    "rm\t",
    "rmdir",
    "sudo",
    "chmod",
    "chown",
    "mv ",
    "mv\t",
    "dd ",
    "> /dev",
    "mkfs",
    "curl",
    "wget",
    "ssh",
    "scp",
    "nc ",
    "ncat",
}

MAX_OUTPUT_LENGTH = 20_000


def run_command(command: str, workspace: Path) -> str:
    base_cmd = command.strip().split()[0] if command.strip() else ""

    if base_cmd not in ALLOWED_COMMANDS:
        return (
            f"Error: '{base_cmd}' is not allowed. "
            f"Permitted commands: {', '.join(sorted(ALLOWED_COMMANDS))}"
        )

    for blocked in BLOCKED_PATTERNS:
        if blocked in command:
            return f"Error: command contains blocked pattern '{blocked.strip()}'."

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return "Error: command timed out after 30 seconds."
    except OSError as exc:
        return f"Error running command: {exc}"

    output_parts: list[str] = []

    if result.stdout.strip():
        stdout = result.stdout
        if len(stdout) > MAX_OUTPUT_LENGTH:
            stdout = stdout[:MAX_OUTPUT_LENGTH] + "\n... (truncated)"
        output_parts.append(f"STDOUT:\n{stdout}")

    if result.stderr.strip():
        stderr = result.stderr
        if len(stderr) > MAX_OUTPUT_LENGTH:
            stderr = stderr[:MAX_OUTPUT_LENGTH] + "\n... (truncated)"
        output_parts.append(f"STDERR:\n{stderr}")

    if not output_parts:
        output_parts.append("(no output)")

    exit_info = f"Exit code: {result.returncode}"
    return exit_info + "\n" + "\n".join(output_parts)
