## Summary

Provide a brief summary of the changes proposed in this pull request.

Closes # (if applicable).


## Detailed list of changes

List all changes proposed in the pull request in the format `<type>: <description>` (**mandatory**). This list will be used to update the changelog. Valid types include `fix`, `feat`, `docs`, `chore`, and `breaking`.

The first sentence of the description should be written in the imperative tense (e.g., "Add new feature" or "Clean existing code file"). Subsequent sentences may have any format; however, the description must consist of only one paragraph (no newline characters).

An example list is shown below. Update these sections to match the changes proposed in the pull request.:

- data: describe any changes to the input data made in this pull-request. Include 1-2 additional sentences on the context. Data changes automatically lead to minor version bumps.
- fix: describe bug fixed through the pull-request, including 1-2 additional sentences on the context. Bug fixes automatically lead to patch version bumps.
- feat: describe new features added to the model. Features include any new functionality that is available to ZEN-garden users. New features automatically lead to minor version bumps.
- docs: describe changes to the documentation. This category is for all changes to the documentation or docstrings. Documentation changes do not bump the ZEN-garden version.
- chore: describe maintenance tasks such as updating tests, improving continuous integration workflows, and refactoring code. These tasks do not change the functionality of ZEN-garden from a user perspective and therefore do not lead to a version bump. They are primarily relevant for developers.
- breaking: describe breaking changes. Add a 1–2 sentence description of the breaking change. Breaking changes automatically lead to a major version bump.


## Effect on the generated dataset

Describe how the default dataset changes. If it does not change, state that. If it does, name the elements and attributes that are affected and why the new values are the better ones.


## Checklist

### PR structure
- [ ] The PR has a descriptive title.
- [ ] A detailed list of changes is provided.

### Code quality
- [ ] Newly introduced dependencies are added to `pyproject.toml` and to `zen_europe_env.yml`.
- [ ] Code has been formatted via `black .` in a terminal window.
- [ ] Linter `ruff check .` passes all checks.
- [ ] Type checker `mypy .` passes all checks.

### Tests
- [ ] `pytest tests/unit` passes locally.
- [ ] `pytest tests/end_to_end` passes locally.
- [ ] New datasets, collections, elements, sectors and settings are covered by a test in the matching `tests/unit/test_*.py`.
- [ ] Fixed bugs have a test that fails without the fix.

### Dataset
- [ ] The default dataset is generated without errors (`zen-europe`).
- [ ] Every variant of the models file is generated without errors (`zen-europe --all`), if variants are affected.
- [ ] `SourceInformation` is up to date with complete descriptions of the data processing steps and sources for each attribute. The `sources.md` files have been checked for completeness.
- [ ] Units, node names, technology and carrier names follow the conventions of the model.
- [ ] Time series profiles are taken from the year `settings.time.time_series_year`.
- [ ] Costs are converted to the price year `settings.time.price_year`.
 

### ZEN-garden compatibility
- [ ] The generated dataset is read and solved by the current `main` of ZEN-garden:

  ```bash
  pip install git+https://github.com/ZEN-universe/ZEN-garden.git@main
  zen-europe
  zen_garden --config ./data/created_models/config.yaml --dataset ./data/created_models/zen-europe
  ```

- [ ] The ZEN-garden run is feasible, and the objective value is plausible compared to `main`.

### Structure (see the developer guide, "Adding Elements, Datasets and Settings")
- [ ] Each new source is a `Dataset` of its own, with complete metadata.
- [ ] Values from several sources are combined in a `DatasetCollection`.
- [ ] Element methods only map attributes to datasets, collections or assumptions, each with a source.
- [ ] New classes are imported in the `__init__.py` of their folder, and new elements are listed in their sectors.
- [ ] New options are settings, with a default that reproduces the previous dataset.
- [ ] Downloaded sources are cached.  In `cache.py`, the caches are added to the `CACHE_PROVIDERS` and have an `overwrite_*` flag in `CacheSettings` that controls cache behavior.
- [ ] Raw data files are placed in the matching folder of `data/raw_data`.

### Documentation
- [ ] Docstrings of new and changed classes and methods are up to date.
- [ ] New settings, elements or sectors are documented in `docs/`.
- [ ] The documentation builds (`sphinx-build docs docs/_build`), if `docs/` changed.