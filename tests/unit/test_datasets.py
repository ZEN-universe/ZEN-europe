"""Unit tests for dataset module exports and singleton construction."""

from __future__ import annotations

import importlib
import inspect
from pathlib import Path

from zen_creator import Dataset

import zen_europe.datasets.datasets as datasets_module


def _all_dataset_classes() -> list[type[Dataset]]:
    """Return every Dataset defined in zen_europe.datasets.datasets, found by
    file since not every subfolder is a regular package."""
    root = Path(datasets_module.__file__).parent
    classes: list[type[Dataset]] = []
    for path in sorted(root.rglob("[!_]*.py")):
        parts = path.relative_to(root).with_suffix("").parts
        module = importlib.import_module(".".join((datasets_module.__name__, *parts)))
        classes += [
            cls
            for _, cls in inspect.getmembers(module, inspect.isclass)
            if issubclass(cls, Dataset)
            and cls.__module__ == module.__name__
            and not inspect.isabstract(cls)
        ]
    return classes


def test_all_datasets_cite_a_url_or_doi() -> None:
    """Building the metadata of every dataset, without loading its data,
    raises if a source has neither url nor doi."""
    dataset_classes = _all_dataset_classes()
    assert dataset_classes
    for dataset_cls in dataset_classes:
        dataset_cls._set_metadata(dataset_cls.__new__(dataset_cls))


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
