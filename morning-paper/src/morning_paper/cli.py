"""Command-line entry point for Morning Paper.

Zero-config commands (no external services):
  morning-paper list-themes
  morning-paper render-proto --theme times-classic --out issue.pdf
  morning-paper fetch-fonts

Set up your interests (each is an independent, optional source):
  morning-paper add-interest --user me --text "AI, typography, Central Asia"
  morning-paper add-interest --user me --topic технологии --topic культура
  morning-paper set-interests-file --user me --file prefs.md
  morning-paper import-telegram-export --user me --file result.json
  morning-paper import-instagram --user me --dir ./instagram-export
  morning-paper connect-telegram --user me            # live Telegram (Telethon)

Preferences:
  morning-paper set-theme --user me --theme old-russian
  morning-paper set-lang  --user me --lang ru
  morning-paper set-delivery --user me --channel telegram
  morning-paper set-tz --user me --tz Europe/Moscow

Run the pipeline:
  morning-paper build-profile --user me               # ingest -> profile
  morning-paper run-issue --user me                    # full s1..s8 -> PDF -> deliver
  morning-paper schedule --user me --at 05:00          # nightly cron line / runner
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

app = typer.Typer(add_completion=False, help="Morning Paper CLI")


# --------------------------------------------------------------------------- #
# Themes / rendering (no external services)
# --------------------------------------------------------------------------- #
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


@app.command("sources")
def sources() -> None:
    """List all registered interest sources."""
    from . import sources as _sources  # noqa: F401  (triggers registration)
    from .sources import registry

    for sid in registry.all_source_ids():
        cls = registry._REGISTRY[sid]
        auth = "auth" if getattr(cls, "requires_auth", False) else "no-auth"
        typer.echo(f"{sid:18} {auth:8} {getattr(cls, 'display_name', '')}")


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
    typer.secho(f"wrote {result.pdf_path} ({result.page_count} pages)", fg=typer.colors.GREEN)


@app.command("fetch-fonts")
def fetch_fonts(theme: str = typer.Option("", help="limit to one theme id")) -> None:
    """Download the OFL fonts each theme needs (via scripts/fetch_fonts.py)."""
    import subprocess
    import sys

    from .config import PROJECT_ROOT

    script = PROJECT_ROOT / "scripts" / "fetch_fonts.py"
    cmd = [sys.executable, str(script)]
    if theme:
        cmd += ["--theme", theme]
    raise typer.Exit(code=subprocess.call(cmd))


# --------------------------------------------------------------------------- #
# Accounts / preferences
# --------------------------------------------------------------------------- #
@app.command("accounts")
def show_accounts(user: str = typer.Option("me", help="user id")) -> None:
    """Show a user's configured sources and preferences."""
    from . import accounts as acc_mod

    acc = acc_mod.load(user)
    typer.echo(f"user={acc.user_id} lang={acc.output_lang} theme={acc.theme} "
               f"tz={acc.tz} deliver={acc.deliver_channel}")
    if not acc.sources:
        typer.echo("  (no sources configured — manual/rss defaults will be used)")
    for sid, sa in acc.sources.items():
        keys = ", ".join(sa.options.keys()) or "-"
        state = "on" if sa.enabled else "off"
        typer.echo(f"  {sid:18} {state:3} options[{keys}] cursor={sa.cursor or '-'}")


@app.command("add-interest")
def add_interest(
    user: str = typer.Option("me", help="user id"),
    text: str = typer.Option("", help="free-text description of your interests"),
    topic: list[str] = typer.Option([], "--topic", help="topic you care about (repeatable)"),
) -> None:
    """Add manual interests (free text and/or topics). Zero-config, no login."""
    from . import accounts

    if not text and not topic:
        typer.secho("provide --text and/or --topic", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    acc = accounts.load(user)
    existing = acc.sources.get("manual")
    opts = dict(existing.options) if existing else {}
    if text:
        prior = opts.get("free_text", "")
        opts["free_text"] = (prior + "\n" + text).strip() if prior else text
    if topic:
        opts["survey_topics"] = sorted(set(opts.get("survey_topics", [])) | set(topic))
    accounts.set_source(user, "manual", options=opts, merge_options=False)
    typer.secho(f"manual interests updated for {user}", fg=typer.colors.GREEN)


@app.command("set-interests-file")
def set_interests_file(
    user: str = typer.Option("me", help="user id"),
    file: Path = typer.Option(..., "--file", help="path to a Markdown interests file"),
) -> None:
    """Point the markdown_prefs source at a .md file describing your interests."""
    from . import accounts

    if not file.exists():
        typer.secho(f"no such file: {file}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    accounts.set_source(user, "markdown_prefs", options={"path": str(file.resolve())})
    typer.secho(f"markdown_prefs -> {file}", fg=typer.colors.GREEN)


@app.command("import-telegram-export")
def import_telegram_export(
    user: str = typer.Option("me", help="user id"),
    file: Path = typer.Option(..., "--file", help="Telegram Desktop export result.json"),
    include_private: bool = typer.Option(False, "--include-private", help="include personal chat text"),
) -> None:
    """Use an exported Telegram chat history (result.json) as an interest source."""
    from . import accounts

    if not file.exists():
        typer.secho(f"no such file: {file}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    accounts.set_source(
        user,
        "telegram_export",
        options={"path": str(file.resolve()), "include_private": include_private},
    )
    typer.secho(f"telegram_export -> {file} (private={include_private})", fg=typer.colors.GREEN)


@app.command("import-instagram")
def import_instagram(
    user: str = typer.Option("me", help="user id"),
    dir: Path = typer.Option(..., "--dir", help="unzipped Instagram data-export folder"),
) -> None:
    """Use an Instagram 'Download Your Information' export as an interest source."""
    from . import accounts

    if not dir.exists():
        typer.secho(f"no such dir: {dir}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    accounts.set_source(user, "instagram", options={"export_dir": str(dir.resolve())})
    typer.secho(f"instagram -> {dir}", fg=typer.colors.GREEN)


@app.command("connect-telegram")
def connect_telegram(
    user: str = typer.Option("me", help="user id"),
    phone: str = typer.Option(..., help="phone number in international format, e.g. +49..."),
    use_private_chats: bool = typer.Option(False, help="also read personal chats"),
) -> None:
    """Log in to live Telegram via Telethon and store the session for nightly fetch."""
    import asyncio

    from . import accounts
    from .config import get_settings
    from .sources.telegram import interactive_login

    s = get_settings().secrets
    if not s.telegram_api_id or not s.telegram_api_hash:
        typer.secho(
            "set TELEGRAM_API_ID and TELEGRAM_API_HASH in .env first (https://my.telegram.org)",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    code_cb = lambda: typer.prompt("Enter the login code Telegram sent you")  # noqa: E731
    pw_cb = lambda: typer.prompt("Two-step password (blank if none)", default="", hide_input=True)  # noqa: E731
    try:
        session = asyncio.run(
            interactive_login(
                int(s.telegram_api_id), s.telegram_api_hash,
                phone=phone, code_cb=code_cb, password_cb=pw_cb,
            )
        )
    except Exception as exc:
        typer.secho(f"telegram login failed: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    accounts.set_source(
        user,
        "telegram",
        options={"session_string": session, "use_private_chats": use_private_chats},
    )
    typer.secho(f"telegram connected for {user}", fg=typer.colors.GREEN)


@app.command("set-theme")
def set_theme(user: str = typer.Option("me"), theme: str = typer.Option(..., "--theme")) -> None:
    """Set the newspaper style for a user's issues."""
    from . import accounts

    acc = accounts.load(user)
    acc.theme = theme
    accounts.save(acc)
    typer.secho(f"theme={theme} for {user}", fg=typer.colors.GREEN)


@app.command("set-lang")
def set_lang(user: str = typer.Option("me"), lang: str = typer.Option(..., "--lang")) -> None:
    """Set the output language for a user's issues."""
    from . import accounts

    acc = accounts.load(user)
    acc.output_lang = lang
    accounts.save(acc)
    typer.secho(f"lang={lang} for {user}", fg=typer.colors.GREEN)


@app.command("set-delivery")
def set_delivery(
    user: str = typer.Option("me"),
    channel: str = typer.Option(..., "--channel", help="file | telegram | email"),
) -> None:
    """Set how finished issues are delivered."""
    from . import accounts

    acc = accounts.load(user)
    acc.deliver_channel = channel
    accounts.save(acc)
    typer.secho(f"deliver={channel} for {user}", fg=typer.colors.GREEN)


@app.command("set-tz")
def set_tz(user: str = typer.Option("me"), tz: str = typer.Option(..., "--tz")) -> None:
    """Set the user's timezone (IANA name, e.g. Europe/Moscow) for scheduling."""
    from . import accounts

    acc = accounts.load(user)
    acc.tz = tz
    accounts.save(acc)
    typer.secho(f"tz={tz} for {user}", fg=typer.colors.GREEN)


# --------------------------------------------------------------------------- #
# Pipeline
# --------------------------------------------------------------------------- #
@app.command("init-db")
def init_db() -> None:
    """Create database tables (Postgres if MP_DB_URL set, else local SQLite)."""
    try:
        from .db.repository import init_db as _init
    except Exception as exc:  # pragma: no cover
        typer.secho(f"db layer unavailable: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    _init()
    typer.secho("database initialized", fg=typer.colors.GREEN)


@app.command("build-profile")
def build_profile(
    user: str = typer.Option("me", help="user id"),
    lang: str = typer.Option("", help="output language (defaults to saved pref)"),
) -> None:
    """Ingest the user's sources and build/update their interest profile."""
    from . import accounts
    from .pipeline.run import run_issue as _run

    acc = accounts.load(user)
    ctx = _run(
        user,
        output_lang=(lang or acc.output_lang or "ru"),
        from_stage=1,
        until_stage=2,
    )
    prof = ctx.profile
    if prof is None:
        typer.secho("no profile produced", fg=typer.colors.YELLOW)
        raise typer.Exit(code=1)
    top_topics = sorted(prof.topics.items(), key=lambda kv: -kv[1])[:8]
    top_entities = sorted(prof.entities.items(), key=lambda kv: -kv[1])[:8]
    typer.secho(f"profile for {user}: {len(ctx.signals)} signals", fg=typer.colors.GREEN)
    typer.echo("  topics:   " + ", ".join(f"{k} {v:.2f}" for k, v in top_topics))
    typer.echo("  entities: " + ", ".join(f"{k} {v:.2f}" for k, v in top_entities))
    # Best-effort persistence.
    try:
        from .db.repository import save_profile, save_signals

        save_signals(ctx.signals)
        save_profile(prof)
    except Exception:
        pass


@app.command("run-issue")
def run_issue(
    user: str = typer.Option("me", help="user id"),
    theme: str = typer.Option("", "--theme", help="theme id (defaults to saved pref)"),
    lang: str = typer.Option("", "--lang", help="output language (defaults to saved pref)"),
    out: Path = typer.Option(Path(".data"), "--out"),
    from_stage: int = typer.Option(1, "--from-stage"),
    until_stage: int = typer.Option(8, "--until-stage"),
    feeds: list[str] = typer.Option([], "--feed", help="RSS feed URLs to include"),
    deliver: str = typer.Option("", "--deliver", help="override delivery channel"),
) -> None:
    """Run the full issue pipeline (or a slice of it) for a user."""
    from .pipeline.run import run_issue as _run

    kwargs = {}
    if deliver:
        kwargs["deliver_channel"] = deliver
    ctx = _run(
        user,
        theme_id=theme or None,
        output_lang=lang or None,
        out_dir=out,
        from_stage=from_stage,
        until_stage=until_stage,
        feed_urls=feeds,
        **kwargs,
    )
    where = ctx.delivery_location or ctx.pdf_path or "n/a"
    typer.secho(f"Issue {ctx.issue_id} ({ctx.theme_id}) -> {where}", fg=typer.colors.GREEN)


@app.command("schedule")
def schedule(
    user: str = typer.Option("me", help="user id"),
    at: str = typer.Option("05:00", help="local time HH:MM"),
    run: bool = typer.Option(False, "--run", help="start a blocking in-process scheduler"),
) -> None:
    """Print the cron line for a nightly run, or run a blocking scheduler with --run."""
    from . import accounts
    from .scheduler import cron_expr, next_run_local

    hour, minute = (int(x) for x in at.split(":"))
    tz = accounts.load(user).tz or "UTC"
    typer.echo(f"cron: {cron_expr(hour, minute)}   (interpret in TZ={tz})")
    typer.echo(f"next run: {next_run_local(hour, minute, tz).isoformat()}")
    typer.echo(
        "crontab line:\n"
        f"  {cron_expr(hour, minute)} cd {Path.cwd()} && "
        f"morning-paper run-issue --user {user}"
    )
    if run:
        from .scheduler import IssueScheduler
        from .pipeline.run import run_issue as _run

        sched = IssueScheduler()
        sched.schedule_user(user, hour=hour, minute=minute, tz=tz, job=lambda: _run(user))
        typer.secho("scheduler running (Ctrl-C to stop)", fg=typer.colors.GREEN)
        sched.start()


if __name__ == "__main__":
    app()
