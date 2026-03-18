from pathlib import Path

import pytest

from tools.explain_function import explain_function
from tools.file_reader import read_file
from tools.file_writer import write_file
from tools.grep_code import grep_code
from tools.list_files import list_files
from tools.run_command import run_command


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    (tmp_path / "sample.py").write_text(
        "def hello():\n    return 'world'\n\ndef add(a, b):\n    return a + b\n"
    )
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "nested.py").write_text("import os\n")
    return tmp_path


class TestReadFile:
    def test_read_existing(self, workspace: Path) -> None:
        result = read_file("sample.py", workspace)
        assert "def hello" in result
        assert "2 lines" not in result

    def test_read_missing(self, workspace: Path) -> None:
        result = read_file("nope.py", workspace)
        assert "Error" in result

    def test_read_outside_workspace(self, workspace: Path) -> None:
        result = read_file("../../etc/passwd", workspace)
        assert "Error" in result


class TestWriteFile:
    def test_write_new(self, workspace: Path) -> None:
        result = write_file("new.py", "print('hi')\n", workspace)
        assert "Successfully wrote" in result
        assert (workspace / "new.py").read_text() == "print('hi')\n"

    def test_write_existing_with_diff(self, workspace: Path) -> None:
        result = write_file("sample.py", "changed\n", workspace)
        assert "Diff" in result

    def test_write_no_change(self, workspace: Path) -> None:
        content = (workspace / "sample.py").read_text()
        result = write_file("sample.py", content, workspace)
        assert "No changes" in result

    def test_write_outside_workspace(self, workspace: Path) -> None:
        result = write_file("../../evil.py", "bad", workspace)
        assert "Error" in result


class TestListFiles:
    def test_list_root(self, workspace: Path) -> None:
        result = list_files(".", workspace)
        assert "sample.py" in result
        assert "sub/" in result

    def test_list_missing(self, workspace: Path) -> None:
        result = list_files("nope", workspace)
        assert "Error" in result


class TestGrepCode:
    def test_grep_match(self, workspace: Path) -> None:
        result = grep_code("def hello", workspace)
        assert "sample.py:1" in result

    def test_grep_no_match(self, workspace: Path) -> None:
        result = grep_code("zzz_nonexistent", workspace)
        assert "No matches" in result

    def test_grep_invalid_regex(self, workspace: Path) -> None:
        result = grep_code("[invalid", workspace)
        assert "Error" in result


class TestRunCommand:
    def test_allowed_command(self, workspace: Path) -> None:
        result = run_command("python --version", workspace)
        assert "Exit code: 0" in result

    def test_blocked_command(self, workspace: Path) -> None:
        result = run_command("rm -rf /", workspace)
        assert "not allowed" in result

    def test_blocked_pattern(self, workspace: Path) -> None:
        result = run_command("python -c 'import os; os.remove(\"x\")'", workspace)
        assert "Exit code" in result or "Error" in result


class TestExplainFunction:
    def test_existing_function(self, workspace: Path) -> None:
        result = explain_function("sample.py", "hello", workspace)
        assert "Function: hello" in result
        assert "return 'world'" in result

    def test_missing_function(self, workspace: Path) -> None:
        result = explain_function("sample.py", "nope", workspace)
        assert "not found" in result
        assert "hello" in result

    def test_missing_file(self, workspace: Path) -> None:
        result = explain_function("nope.py", "foo", workspace)
        assert "Error" in result
