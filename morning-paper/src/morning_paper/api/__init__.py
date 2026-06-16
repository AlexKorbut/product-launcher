"""FastAPI backend for Morning Paper.

This subpackage is an OPTIONAL extra: it imports fastapi at module level and is
only imported when the server runs. The core `morning_paper` package must never
import this package, so installing morning_paper never requires fastapi.
"""

from __future__ import annotations


def create_app():
    """Lazily build the FastAPI app (keeps fastapi import out of import time)."""
    from .app import create_app as _create_app

    return _create_app()
