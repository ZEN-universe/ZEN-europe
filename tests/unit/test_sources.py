"""Unit tests for the sources written to sources.md."""

from __future__ import annotations

from zen_creator import Model, SourceInformation

from zen_europe.elements.carriers.clinker import Clinker


def test_clinker_demand_cites_only_the_datasets_read(model: Model) -> None:
    """ClinkerData holds four datasets, the clinker demand reads two of them."""
    clinker = Clinker(model=model)
    clinker._build_attribute("demand")

    (source,) = clinker.demand.sources
    assert isinstance(source, SourceInformation)
    assert isinstance(source.cited_metadata, dict)
    assert set(source.cited_metadata) == {"aidres", "british_geological_survey"}
