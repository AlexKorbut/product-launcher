"""Renderer contract: the Node renderer turns a RenderDocument into a PDF.

Skips automatically when Node or the renderer's npm deps aren't installed, so the
pure-Python suite stays green in CI without a Node toolchain. Run
`make install-node` to exercise this end-to-end.
"""

import shutil
from pathlib import Path

import pytest

from morning_paper.config import RENDERER_DIR
from morning_paper.render.renderer import NodeRenderer
from morning_paper.sample import sample_render_document

node_missing = shutil.which("node") is None
deps_missing = not (RENDERER_DIR / "node_modules").exists()

pytestmark = pytest.mark.skipif(
    node_missing or deps_missing,
    reason="Node and renderer deps required (run `make install-node`)",
)


def test_renders_pdf(tmp_path: Path):
    doc = sample_render_document("times-classic")
    out = tmp_path / "issue.pdf"
    result = NodeRenderer().render(doc, out_path=out)
    assert out.exists() and out.stat().st_size > 0
    assert result.page_count is None or result.page_count >= 1
