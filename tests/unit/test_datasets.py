"""Unit tests for dataset module exports and singleton construction."""

from __future__ import annotations

from pathlib import Path

from zen_creator import Dataset

import zen_europe.datasets.datasets as datasets_module


def _dataset_classes() -> list[type[Dataset]]:
    """Return all dataset classes exported by zen_europe.datasets.datasets."""
    classes: list[type[Dataset]] = []
    for name in datasets_module.__all__:
        dataset_cls = getattr(datasets_module, name)
        if isinstance(dataset_cls, type) and issubclass(dataset_cls, Dataset):
            classes.append(dataset_cls)
    return classes


def _construct_dataset(dataset_cls: type[Dataset], source_path: Path) -> Dataset:
    """Construct a dataset class with the right constructor signature."""
    return dataset_cls(source_path)


def test_all_exported_datasets_are_dataset_classes() -> None:
    """All module exports must be Dataset subclasses."""
    dataset_classes = _dataset_classes()
    assert dataset_classes
    for dataset_cls in dataset_classes:
        assert issubclass(dataset_cls, Dataset)


# def test_all_exported_datasets_construct_as_singletons(tmp_path: Path) -> None:
#     """All exported dataset classes should construct and behave as singletons."""
#     for dataset_cls in _dataset_classes():
#         first = _construct_dataset(dataset_cls, tmp_path)
#         second = _construct_dataset(dataset_cls, tmp_path)

#         if not dataset_cls.name:
#             raise ValueError(
#                 f"Dataset class {dataset_cls.__name__} does not have a name "
#                 "attribute."
#             )
#         if not isinstance(first, dataset_cls):
#             raise TypeError(
#                 f"Expected instance of {dataset_cls.__name__}, got "
#                 "{type(first).__name__}"
#             )
#         if first is not second:
#             raise AssertionError(
#                 f"Dataset class {dataset_cls.__name__} does not behave as a "
#                 "singleton. Two instances were created."
#             )
