"""Shared pytest fixtures for unit tests."""

from __future__ import annotations

from typing import Iterator

import pytest
from pathlib import Path
from zen_creator import Model, Dataset, DatasetCollection


@pytest.fixture(autouse=True)
def reset_singleton_registries() -> Iterator[None]:
    """Reset dataset registries for test isolation."""
    Dataset._registries.clear()
    DatasetCollection._registries.clear()
    yield
    Dataset._registries.clear()
    DatasetCollection._registries.clear()
    
@pytest.fixture
def model(tmp_path: Path, request: pytest.FixtureRequest) -> Model:
    """Create a minimal model object that is sufficient for element tests.

    The element ``write()`` path resolution requires ``output_folder`` and
    ``name`` to be defined, while templates using datasets require
    ``source_path``.
    """
    model = Model()
    model.name = f"{request.module.__name__.split('.')[-1]}_model"
    model.output_folder = tmp_path / "outputs"
    model.source_path = tmp_path
    return model

