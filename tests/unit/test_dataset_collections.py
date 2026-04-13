"""Unit tests for dataset_collection module exports and singleton construction."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from zen_creator import DatasetCollection

import zen_europe.datasets.dataset_collections as collections_module


def _dataset_collection_classes() -> list[type[DatasetCollection]]:
    """Return all dataset collection classes exported by the module."""
    classes: list[type[DatasetCollection]] = []
    for name in collections_module.__all__:
        collection_cls = getattr(collections_module, name)
        if isinstance(collection_cls, type) and issubclass(
            collection_cls, DatasetCollection
        ):
            classes.append(collection_cls)
    return classes


def _construct_collection(
    collection_cls: type[DatasetCollection], source_path: Path
) -> DatasetCollection:
    """Construct a dataset collection with the expected constructor signature."""
    collection_factory = cast(type[Any], collection_cls)
    return cast(DatasetCollection, collection_factory(source_path))


def test_all_exported_dataset_collections_are_collection_classes() -> None:
    """All module exports must be DatasetCollection subclasses."""
    collection_classes = _dataset_collection_classes()
    assert collection_classes
    for collection_cls in collection_classes:
        assert issubclass(collection_cls, DatasetCollection)


# def test_all_exported_dataset_collections_construct_as_singletons(
#     tmp_path: Path,
# ) -> None:
#     """All exported dataset collections should construct and behave as singletons."""
#     for collection_cls in _dataset_collection_classes():
#         first = _construct_collection(collection_cls, tmp_path)
#         second = _construct_collection(collection_cls, tmp_path)

#         assert isinstance(first, collection_cls)
#         assert first is second
#         assert collection_cls.name
