from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from config import settings
from utils.logger import setup_logger

app = typer.Typer(
    name="ai-agent",
    help="AI Codebase Assistant — understand, search, and modify code using Groq.",
    add_completion=False,
)
console = Console()


def _resolve_workspace(workspace: str | None) -> Path:
    path = Path(workspace) if workspace else Path.cwd()
    resolved = path.resolve()
    if not resolved.is_dir():
        console.print(f"[red]Error:[/red] '{resolved}' is not a valid directory.")
        raise typer.Exit(code=1)
    return resolved


@app.command()
def ask(
    query: str = typer.Argument(..., help="Question or instruction for the agent."),
    workspace: str = typer.Option(None, "--workspace", "-w", help="Target codebase directory."),
) -> None:
    ws = _resolve_workspace(workspace)
    data_dir = settings.resolve_data_dir(ws)
    setup_logger("ai_agent", log_dir=data_dir)

    if not settings.groq_api_key:
        console.print("[red]Error:[/red] GROQ_API_KEY is not set.")
        raise typer.Exit(code=1)

    from agent.core import AgentCore

    agent = AgentCore(workspace=ws)

    with console.status("[bold cyan]Thinking...", spinner="dots"):
        response = agent.run(query)

    console.print()
    console.print(Panel(Markdown(response), title="Agent Response", border_style="green"))


@app.command()
def index(
    workspace: str = typer.Option(None, "--workspace", "-w", help="Target codebase directory."),
) -> None:
    ws = _resolve_workspace(workspace)
    data_dir = settings.resolve_data_dir(ws)
    setup_logger("ai_agent", log_dir=data_dir)

    from memory.vector_store import VectorStore

    store = VectorStore(data_dir=data_dir)

    console.print(f"[cyan]Indexing codebase at:[/cyan] {ws}")
    with console.status("[bold cyan]Building vector index...", spinner="dots"):
        count = store.build_index(ws)

    if count == 0:
        console.print("[yellow]No indexable files found in the workspace.[/yellow]")
    else:
        console.print(f"[green]Indexed {count} chunks.[/green] Saved to {data_dir}")


@app.command()
def clear(
    workspace: str = typer.Option(None, "--workspace", "-w", help="Target codebase directory."),
) -> None:
    ws = _resolve_workspace(workspace)
    data_dir = settings.resolve_data_dir(ws)

    from memory.chat_memory import ChatMemory

    memory = ChatMemory(data_dir / "memory.json")
    memory.clear()
    console.print("[green]Chat memory cleared.[/green]")


@app.command()
def chat(
    workspace: str = typer.Option(None, "--workspace", "-w", help="Target codebase directory."),
) -> None:
    ws = _resolve_workspace(workspace)
    data_dir = settings.resolve_data_dir(ws)
    setup_logger("ai_agent", log_dir=data_dir)

    if not settings.groq_api_key:
        console.print("[red]Error:[/red] GROQ_API_KEY is not set.")
        raise typer.Exit(code=1)

    from agent.core import AgentCore

    agent = AgentCore(workspace=ws)

    console.print(
        Panel(
            f"AI Code Agent — workspace: [cyan]{ws}[/cyan]\n"
            "Type [bold]exit[/bold] or [bold]quit[/bold] to end.",
            title="Interactive Mode",
            border_style="blue",
        )
    )

    while True:
        try:
            query = console.input("[bold green]>>> [/bold green]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye.[/dim]")
            break

        if not query:
            continue
        if query.lower() in {"exit", "quit"}:
            console.print("[dim]Goodbye.[/dim]")
            break

        with console.status("[bold cyan]Thinking...", spinner="dots"):
            response = agent.run(query)

        console.print()
        console.print(Panel(Markdown(response), title="Agent", border_style="green"))
        console.print()


if __name__ == "__main__":
    app()
