"""Fixtures do pytest; helpers em ajuda.py."""

from __future__ import annotations

from pathlib import Path

import pytest
from ajuda import FakeCliente
from ajuda_docs import PASTA


@pytest.fixture
def pasta_exemplo() -> Path:
    return PASTA


@pytest.fixture
def fake() -> FakeCliente:
    return FakeCliente()
