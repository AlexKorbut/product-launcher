from __future__ import annotations

from pathlib import Path

from morning_paper.delivery.file import FileDeliverer


def test_file_deliverer_copies_pdf(tmp_path):
    pdf = tmp_path / "src.pdf"
    payload = b"%PDF-1.4 dummy content"
    pdf.write_bytes(payload)

    outbox = tmp_path / "outbox"
    result = FileDeliverer(outbox=outbox).deliver(
        pdf, user_id="me", subject="Morning Paper"
    )

    assert result.ok
    assert result.channel == "file"
    assert result.location is not None
    dest = Path(result.location)
    assert dest.exists()
    assert dest.read_bytes() == payload
