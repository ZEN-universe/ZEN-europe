"""Shared pytest fixtures for unit tests."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest

from zen_creator.model import Model
from zen_creator.utils.singleton_registry_meta import SingletonRegistryMeta


@pytest.fixture(autouse=True)
def reset_singleton_registries() -> Iterator[None]:
    """Reset singleton registries for test isolation."""
    SingletonRegistryMeta._registries.clear()
    yield
    SingletonRegistryMeta._registries.clear()


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
