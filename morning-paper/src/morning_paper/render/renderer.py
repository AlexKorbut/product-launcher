"""The Python<->Node renderer boundary.

Python never touches Chromium. It writes a RenderDocument JSON to a temp file and
invokes `renderer/render.mjs`, which composes HTML (base template + theme) and
prints a PDF via Paged.js + Playwright. The contract is versioned by
RenderDocument.schema_version so the two runtimes can evolve independently.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel

from ..config import RENDERER_DIR, THEMES_DIR, get_settings
from ..models import RenderDocument


class RenderResult(BaseModel):
    pdf_path: str
    page_count: int | None = None
    warnings: list[str] = []


class RenderError(RuntimeError):
    pass


class Renderer(Protocol):
    def render(self, doc: RenderDocument, *, out_path: Path) -> RenderResult: ...


class NodeRenderer:
    """Invokes the Node renderer as a stateless subprocess (one Chromium launch)."""

    def __init__(
        self,
        *,
        renderer_dir: Path = RENDERER_DIR,
        themes_dir: Path = THEMES_DIR,
        node_bin: str = "node",
    ) -> None:
        self.renderer_dir = renderer_dir
        self.themes_dir = themes_dir
        self.node_bin = node_bin

    def render(self, doc: RenderDocument, *, out_path: Path) -> RenderResult:
        if shutil.which(self.node_bin) is None:
            raise RenderError(
                f"`{self.node_bin}` not found. Install Node and run "
                "`make install-node` in morning-paper/renderer."
            )
        entry = self.renderer_dir / "render.mjs"
        if not entry.exists():
            raise RenderError(f"renderer entry not found: {entry}")

        assets_root = _object_store_root()
        out_path = out_path.resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8"
        ) as fh:
            json.dump(doc.model_dump(), fh, ensure_ascii=False)
            in_path = Path(fh.name)

        cmd = [
            self.node_bin,
            str(entry),
            "--in", str(in_path),
            "--out", str(out_path),
            "--themes", str(self.themes_dir),
            "--assets", str(assets_root),
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True)
        finally:
            in_path.unlink(missing_ok=True)

        if proc.returncode != 0:
            raise RenderError(
                f"renderer failed (exit {proc.returncode}):\n{proc.stderr.strip()}"
            )

        result = _parse_stdout(proc.stdout)
        return RenderResult(pdf_path=str(out_path), **result)


def _object_store_root() -> Path:
    url = get_settings().secrets.mp_object_store_url
    if url.startswith("file://"):
        return Path(url[len("file://") :]).resolve()
    return Path(".data/objects").resolve()


def _parse_stdout(stdout: str) -> dict:
    """The renderer prints a single JSON line of metadata on success."""
    for line in reversed(stdout.strip().splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                data = json.loads(line)
                return {
                    "page_count": data.get("page_count"),
                    "warnings": data.get("warnings", []),
                }
            except json.JSONDecodeError:
                break
    return {"page_count": None, "warnings": []}
