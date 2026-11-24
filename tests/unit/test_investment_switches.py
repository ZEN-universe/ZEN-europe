"""Source scan: every setter of the existing capacity or the maximum diffusion rate
honours its investment switch.

The first statement after the docstring must branch on the switch, and the branch
taken when the switch is off must return the attribute's default (no existing
capacity, unbounded diffusion rate), or set the existing capacity to
``default_value=0``. Both ``if not <switch>: return ...`` and
``if <switch>: ... else: ...`` are accepted.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import zen_europe

ELEMENTS_PATH = Path(zen_europe.__file__).parent / "elements"
# setter name -> investment switch it has to honour
SWITCHES = {
    "_set_capacity_existing": "use_existing_capacities",
    "_set_capacity_existing_energy": "use_existing_capacities",
    "_set_max_diffusion_rate": "use_diffusion_rates",
}


def _setters() -> list[tuple[str, ast.FunctionDef]]:
    """All setters of SWITCHES in the element modules, with their location."""
    setters = []
    for path in sorted(ELEMENTS_PATH.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.FunctionDef) and node.name in SWITCHES:
                location = f"{path.relative_to(ELEMENTS_PATH)}:{node.lineno}"
                setters.append((location, node))
    return setters


def _is_negated(test: ast.expr) -> bool:
    """Whether the condition is true when the switch is off, i.e. `not <switch>`,
    `not (...)` or `not <switch> or not <other>`."""
    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        return True
    return isinstance(test, ast.BoolOp) and all(_is_negated(v) for v in test.values)


def _returns_off_value(branch: list[ast.stmt], setter: str) -> bool:
    """Whether the branch returns the attribute's default (no existing capacity,
    unbounded diffusion rate) or, for the existing capacity, sets it to zero."""
    source = ast.unparse(ast.Module(body=branch, type_ignores=[]))
    if f"return self.{setter.removeprefix('_set_')}" in source:
        return True
    return setter != "_set_max_diffusion_rate" and "default_value=0" in source


SETTERS = _setters()


def test_setters_found() -> None:
    """The scan finds the setters, so that the test below does not pass vacuously."""
    assert len(SETTERS) > 100


@pytest.mark.parametrize(
    "location, setter", SETTERS, ids=[location for location, _ in SETTERS]
)
def test_setter_honours_switch(location: str, setter: ast.FunctionDef) -> None:
    """The setter branches on its switch first and returns the off value."""
    switch = SWITCHES[setter.name]
    body = setter.body
    if isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        body = body[1:]  # skip the docstring
    guard = body[0]
    assert isinstance(guard, ast.If) and switch in ast.unparse(guard.test), (
        f"{location}: {setter.name} must start with "
        f"`if not self.settings.investment.{switch}:`"
    )
    # the else branch, or the code after an if branch that returns
    off_branch = guard.body if _is_negated(guard.test) else guard.orelse or body[1:]
    assert _returns_off_value(off_branch, setter.name), (
        f"{location}: {setter.name} must return "
        + (
            "self.max_diffusion_rate"
            if setter.name == "_set_max_diffusion_rate"
            else "a capacity with default_value=0"
        )
        + f" if {switch} is False"
    )
