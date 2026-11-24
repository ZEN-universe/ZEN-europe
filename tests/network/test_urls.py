"""Reachability of the URLs the datasets cite or download from.

Needs internet access and is deselected by default. Run with
``pytest tests/network -m network -n 8``.

The URLs are collected from each dataset's metadata (``url`` and ``doi``) and
from URL constants in the dataset classes and modules (download sources). URLs
built at runtime (f-strings) are not covered.
"""

from __future__ import annotations

import importlib
import inspect
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import pytest
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from zen_creator import Dataset

import zen_europe.datasets.datasets as datasets_package

pytestmark = pytest.mark.network

TIMEOUT = 10
# some publishers reject the default python-requests user agent outright
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}
# answered by bot protection (Elsevier, MDPI, IEA, Zenodo, ...): inconclusive
BLOCKED = {401, 403, 429}


def _dataset_modules() -> list[ModuleType]:
    """Import every module below zen_europe.datasets.datasets."""
    root = Path(datasets_package.__file__).parent
    return [
        importlib.import_module(
            ".".join(
                (datasets_package.__name__, *f.relative_to(root).with_suffix("").parts)
            )
        )
        for f in sorted(root.rglob("[!_]*.py"))
    ]


def _dataset_classes() -> list[type[Dataset]]:
    """All concrete Dataset subclasses defined in zen_europe."""
    found, stack = set(), [Dataset]
    while stack:
        for sub in stack.pop().__subclasses__():
            stack.append(sub)
            if sub.__module__.startswith("zen_europe") and not inspect.isabstract(sub):
                found.add(sub)
    return sorted(found, key=lambda c: c.__name__)


def _urls_in(value: object) -> Iterator[str]:
    """Complete URLs in a constant, searching tuples, lists and dicts."""
    if isinstance(value, str):
        if value.startswith(("http://", "https://")) and "{" not in value:
            yield value
    elif isinstance(value, (tuple, list)):
        for item in value:
            yield from _urls_in(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _urls_in(item)


def _collect_urls() -> dict[str, str]:
    """Map each URL to the first place it is defined in."""
    urls: dict[str, str] = {}
    for module in _dataset_modules():
        for url in _urls_in(list(vars(module).values())):
            urls.setdefault(url, module.__name__.rsplit(".", 1)[-1])
    for cls in _dataset_classes():
        # metadata is built without loading the data
        metadata = cls._set_metadata(object.__new__(cls))
        doi = metadata.doi
        if doi and not doi.startswith("http"):
            doi = f"https://doi.org/{doi}"
        candidates = [metadata.url, doi, *_urls_in(list(vars(cls).values()))]
        for url in filter(None, candidates):
            urls.setdefault(url, cls.__name__)
    return urls


URLS = _collect_urls()


@pytest.fixture(scope="module")
def session() -> Iterator[requests.Session]:
    """Session that retries transient failures with backoff."""
    retry = Retry(
        total=1,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["HEAD", "GET"],
        raise_on_status=False,
    )
    with requests.Session() as s:
        s.headers.update(HEADERS)
        s.mount("https://", HTTPAdapter(max_retries=retry))
        s.mount("http://", HTTPAdapter(max_retries=retry))
        yield s


@pytest.mark.parametrize("url", sorted(URLS))
def test_url_is_reachable(url: str, session: requests.Session) -> None:
    """The URL answers without a client or server error."""
    try:
        status = session.head(url, allow_redirects=True, timeout=TIMEOUT).status_code
        if status >= 400:
            # some servers reject HEAD; stream so large downloads are not fetched
            with session.get(
                url, allow_redirects=True, timeout=TIMEOUT, stream=True
            ) as r:
                status = r.status_code
    except requests.RequestException as error:
        pytest.fail(f"{url} (used in {URLS[url]}): {type(error).__name__}")
    if status in BLOCKED:
        pytest.skip(f"{status} (bot protection?) from {URLS[url]}")
    if status >= 400:
        pytest.fail(f"{url} (used in {URLS[url]}): HTTP {status}")
