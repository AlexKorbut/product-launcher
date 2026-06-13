"""Command-line entry point.

Phase 0 commands work with no external services:
  morning-paper list-themes
  morning-paper render-proto --theme times-classic --out issue.pdf

Later-phase commands (build-profile, run-issue, connect-telegram) are scaffolded.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

app = typer.Typer(add_completion=False, help="Morning Paper CLI")


@app.command("list-themes")
def list_themes() -> None:
    """List installed themes and their key visual parameters."""
    from .render.themes import list_manifests

    manifests = list_manifests()
    if not manifests:
        typer.echo("no themes found")
        raise typer.Exit(code=1)
    for m in manifests:
        typer.echo(
            f"{m.id:16}  {m.format.page:10} {m.grid.columns}col  "
            f"{m.format.color_mode:8}  {m.display_name}"
        )


@app.command("render-proto")
def render_proto(
    theme: str = typer.Option("times-classic", help="theme id"),
    out: Path = typer.Option(Path("issue.pdf"), help="output PDF path"),
    locale: str = typer.Option("ru", help="output language"),
    dump_html: bool = typer.Option(False, help="also write composed inputs as JSON"),
) -> None:
    """Render the sample issue into a themed PDF (no LLM/DB/network)."""
    from .render.renderer import NodeRenderer, RenderError
    from .sample import sample_render_document

    doc = sample_render_document(theme, locale=locale)
    if dump_html:
        Path("render_document.json").write_text(
            json.dumps(doc.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8"
        )

    try:
        result = NodeRenderer().render(doc, out_path=out)
    except RenderError as e:
        typer.secho(f"render failed: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    typer.secho(
        f"wrote {result.pdf_path} ({result.page_count} pages)", fg=typer.colors.GREEN
    )


@app.command("build-profile")
def build_profile(user: str = typer.Option(..., help="user id")) -> None:
    """Build an interest profile from the user's enabled sources (Phase 1)."""
    typer.echo(f"[scaffold] build-profile for {user}: wire sources -> profile.builder")


@app.command("run-issue")
def run_issue(
    user: str = typer.Option(..., help="user id"),
    theme: str = typer.Option("times-classic"),
) -> None:
    """Run the full pipeline (s1..s8) for a user (Phase 1)."""
    typer.echo(f"[scaffold] run-issue for {user} with theme {theme}")


@app.command("connect-telegram")
def connect_telegram(user: str = typer.Option(..., help="user id")) -> None:
    """Begin Telegram auth (Telethon) for a user (Phase 1)."""
    typer.echo(f"[scaffold] connect-telegram for {user}")


if __name__ == "__main__":
    app()
