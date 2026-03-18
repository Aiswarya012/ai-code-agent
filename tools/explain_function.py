import ast
from pathlib import Path


def explain_function(path: str, function_name: str, workspace: Path) -> str:
    target = (workspace / path).resolve()
    if not str(target).startswith(str(workspace.resolve())):
        return f"Error: access denied — '{path}' is outside the workspace."

    if not target.exists():
        return f"Error: file not found — '{path}'"

    if not target.suffix == ".py":
        return f"Error: '{path}' is not a Python file."

    try:
        source = target.read_text(encoding="utf-8")
    except (OSError, PermissionError) as exc:
        return f"Error reading '{path}': {exc}"

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return f"Error parsing '{path}': {exc}"

    node = _find_function(tree, function_name)
    if node is None:
        available = _list_functions(tree)
        return (
            f"Function '{function_name}' not found in '{path}'.\n"
            f"Available: {', '.join(available) if available else '(none)'}"
        )

    lines = source.splitlines()
    start = node.lineno - 1
    end = node.end_lineno if node.end_lineno else start + 1
    func_source = "\n".join(lines[start:end])

    info_parts: list[str] = [
        f"Function: {function_name}",
        f"Location: {path}:{node.lineno}-{end}",
        f"Arguments: {_format_args(node)}",
    ]

    returns = _get_return_annotation(node)
    if returns:
        info_parts.append(f"Returns: {returns}")

    decorators = _get_decorators(node)
    if decorators:
        info_parts.append(f"Decorators: {', '.join(decorators)}")

    docstring = ast.get_docstring(node)
    if docstring:
        info_parts.append(f"Docstring: {docstring}")

    info_parts.append(f"\nSource ({end - start} lines):\n{func_source}")

    return "\n".join(info_parts)


def _find_function(tree: ast.Module, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def _list_functions(tree: ast.Module) -> list[str]:
    functions: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node.name)
    return functions


def _format_args(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    args = node.args
    parts: list[str] = []

    all_args = args.posonlyargs + args.args
    defaults_offset = len(all_args) - len(args.defaults)

    for i, arg in enumerate(all_args):
        annotation = ast.unparse(arg.annotation) if arg.annotation else ""
        name = arg.arg
        entry = f"{name}: {annotation}" if annotation else name

        default_idx = i - defaults_offset
        if default_idx >= 0 and default_idx < len(args.defaults):
            entry += f" = {ast.unparse(args.defaults[default_idx])}"

        parts.append(entry)

    if args.vararg:
        parts.append(f"*{args.vararg.arg}")
    if args.kwonlyargs:
        if not args.vararg:
            parts.append("*")
        for j, kw in enumerate(args.kwonlyargs):
            annotation = ast.unparse(kw.annotation) if kw.annotation else ""
            name = kw.arg
            entry = f"{name}: {annotation}" if annotation else name
            if j < len(args.kw_defaults) and args.kw_defaults[j]:
                entry += f" = {ast.unparse(args.kw_defaults[j])}"
            parts.append(entry)
    if args.kwarg:
        parts.append(f"**{args.kwarg.arg}")

    return f"({', '.join(parts)})"


def _get_return_annotation(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    if node.returns:
        return ast.unparse(node.returns)
    return ""


def _get_decorators(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    return [ast.unparse(d) for d in node.decorator_list]
