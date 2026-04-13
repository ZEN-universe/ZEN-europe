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

## Checklist

### PR structure
- [ ] The PR has a descriptive title.
- [ ] A detailed list of changes is provided.


### Code quality
- [ ] Newly introduced dependencies are added to `pyproject.toml`.
- [ ] Code changes have been tested locally and all tests pass.
- [ ] Code has been formatted via ``black .`` in a terminal window.
- [ ] Linter ``ruff check .`` passes all checks.
- [ ] Type Checker  ``mypy .`` passes all checks.

