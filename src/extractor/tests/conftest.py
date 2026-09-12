"""Fixtures do pytest; helpers em ajuda_docs.py (determinístico) e ajuda.py (LLM)."""

from __future__ import annotations

from pathlib import Path

import pytest
from ajuda_docs import PASTA


@pytest.fixture
def pasta_exemplo() -> Path:
    return PASTA
