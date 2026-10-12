"""Generate the documentation pages of the sectors, technologies and carriers."""

import logging
import shutil
from collections.abc import Sequence
from pathlib import Path

from zen_creator import Model, model_structure
from zen_creator.utils.config import Config
from zen_creator.utils.settings import Settings

from zen_europe.model_creator import DATA_PATH, DEFAULT_CONFIG_PATH

TECHNOLOGY_TYPES = {
    "conversion_technology": "Conversion technologies",
    "retrofitting_technology": "Retrofitting technologies",
    "storage_technology": "Storage technologies",
    "transport_technology": "Transport technologies",
}

# mermaid node shapes per element type
NODE_SHAPES = {
    "carrier": "stadium",
    "conversion_technology": "rect",
    "retrofitting_technology": "notch-rect",
    "storage_technology": "cyl",
    "transport_technology": "lean-r",
}

LEGEND = (
    "Rounded nodes are carriers, boxes are conversion technologies, boxes with a "
    "cut corner are retrofitting technologies, cylinders are storage technologies "
    "and parallelograms are transport technologies. A retrofitting technology "
    "shares a box with the technology it retrofits."
)


def default_structure() -> dict:
    """Return the structure of the model with the default configuration."""
    config = Config.load_from_yaml(DEFAULT_CONFIG_PATH)
    config.source_path = str(DATA_PATH / "raw_data")
    model = Model.from_config(
        config, settings=Settings.load_from_yaml(DEFAULT_CONFIG_PATH)
    )
    return model_structure(model)


def sort_names(names) -> list[str]:
    return sorted(names, key=str.lower)


def heading(text: str, char: str, overline: bool = False) -> str:
    line = char * len(text)
    return f"{line}\n{text}\n{line}\n" if overline else f"{text}\n{line}\n"


def links(names: list[str], prefix: str, known=None) -> str:
    """Return references to the given elements, or "none"."""
    if not names:
        return "none"
    return ", ".join(
        f":ref:`{name} <{prefix}-{name}>`" if known is None or name in known else name
        for name in sort_names(names)
    )


def flow_diagram(
    tech_names: list[str],
    structure: dict,
    carriers: Sequence[str] = (),
    own_elements: list[str] | None = None,
    highlight: Sequence[str] = (),
) -> list[str]:
    """Return the body of a mermaid flowchart of the carrier flows of technologies.

    Args:
        tech_names: The technologies to draw, with their carriers.
        structure: The model structure.
        carriers: Further carriers to draw.
        own_elements: Carriers and technologies that are not in this list are
            drawn dashed. Nothing is drawn dashed if it is None.
        highlight: Carriers that are drawn with a thick border.
    """
    technologies = structure["technologies"]
    nodes = {carrier: "carrier" for carrier in carriers}
    retrofits: dict[str, list[str]] = {}
    edges = []
    for tech_name in tech_names:
        tech = technologies[tech_name]
        nodes[tech_name] = tech["type"]
        if "input_carrier" in tech:
            for carrier in tech["input_carrier"]:
                nodes.setdefault(carrier, "carrier")
                edges.append(f"c_{carrier} --> t_{tech_name}")
            for carrier in tech["output_carrier"]:
                nodes.setdefault(carrier, "carrier")
                edges.append(f"t_{tech_name} --> c_{carrier}")
        else:
            for carrier in tech["reference_carrier"]:
                nodes.setdefault(carrier, "carrier")
                edges.append(f"c_{carrier} <--> t_{tech_name}")
        base = tech.get("base_technology")
        if base in technologies:
            retrofits.setdefault(base, []).append(tech_name)

    lines = [
        "flowchart LR",
        "  classDef external stroke-dasharray: 4 4,fill:transparent",
        "  classDef highlight stroke-width:3px",
    ]
    nested = {name for names in retrofits.values() for name in names}
    for node, node_type in nodes.items():
        if node not in nested and node not in retrofits:
            lines += node_lines(node, node_type, own_elements, highlight)
    # a technology and its retrofits share a box
    for base, names in retrofits.items():
        lines.append(f'  subgraph g_{base} [" "]')
        lines += node_lines(base, technologies[base]["type"], own_elements, highlight)
        for name in names:
            lines += node_lines(name, nodes[name], own_elements, highlight)
        lines.append("  end")
        if own_elements is not None and base not in own_elements:
            lines.append(f"  style g_{base} stroke-dasharray: 4 4")
    return lines + [f"  {edge}" for edge in edges]


def node_lines(
    node: str, node_type: str, own_elements: list[str] | None, highlight: Sequence[str]
) -> list[str]:
    """Return the mermaid lines that declare and style a node."""
    node_id = f"c_{node}" if node_type == "carrier" else f"t_{node}"
    lines = [f'  {node_id}@{{ shape: {NODE_SHAPES[node_type]}, label: "{node}" }}']
    if own_elements is not None and node not in own_elements:
        lines.append(f"  class {node_id} external")
    if node in highlight:
        lines.append(f"  class {node_id} highlight")
    return lines


def mermaid(body: list[str], zoom: bool = False, indent: str = "") -> list[str]:
    """Return a mermaid directive with the given diagram body."""
    lines = [f"{indent}.. mermaid::"]
    if zoom:
        lines.append(f"{indent}   :zoom:")
    return lines + [""] + [f"{indent}   {line}" for line in body] + [""]


def carrier_flow_diagram(structure: dict) -> list[str]:
    """Return the body of a mermaid flowchart of the carriers converted into each
    other."""
    lines = ["flowchart LR"]
    for name in sort_names(structure["carriers"]):
        lines += node_lines(name, "carrier", None, ())
    lines += [
        f"  c_{source} --> c_{target}" for source, target in structure["carrier_flows"]
    ]
    return lines


def render_index(structure: dict) -> str:
    technologies = structure["technologies"]
    lines = [
        ".. _model_structure.index:",
        "",
        heading("Sectors, Technologies and Carriers", "#", overline=True),
        "These pages are generated from the code at every documentation build. "
        "They show the model of the default configuration "
        "(``data/zen_europe_config.yaml``).",
        "",
        ".. list-table::",
        "   :header-rows: 1",
        "   :widths: 50 20",
        "",
        "   * - Element type",
        "     - Number",
        "   * - Sectors",
        f"     - {len(structure['sectors'])}",
        "   * - :ref:`Carriers <model_structure.carriers>`",
        f"     - {len(structure['carriers'])}",
    ]
    for technology_type, title in TECHNOLOGY_TYPES.items():
        count = sum(t["type"] == technology_type for t in technologies.values())
        lines += [
            f"   * - :ref:`{title} <model_structure.{technology_type}>`",
            f"     - {count}",
        ]
    lines += [
        "",
        "An arrow from carrier A to carrier B means that at least one technology "
        "converts A into B. Scroll to zoom, drag to pan, or open the diagram in "
        "full screen.",
        "",
        ".. container:: natural-size",
        "",
        *mermaid(carrier_flow_diagram(structure), zoom=True, indent="   "),
        ".. toctree::",
        "   :maxdepth: 1",
        "   :caption: Sectors",
        "",
        *(f"   sectors/{name}" for name in structure["sectors"]),
        "",
        ".. toctree::",
        "   :maxdepth: 1",
        "   :caption: Elements",
        "",
        "   technologies",
        "   carriers",
        "",
    ]
    return "\n".join(lines)


def render_sector(name: str, structure: dict) -> str:
    sector = structure["sectors"][name]
    technologies = structure["technologies"]
    carriers = structure["carriers"]
    sector_technologies = sort_names(e for e in sector["elements"] if e in technologies)
    sector_carriers = [e for e in sector["elements"] if e in carriers]
    diagram = flow_diagram(
        sector_technologies,
        structure,
        carriers=sector_carriers,
        own_elements=sector["elements"],
    )

    lines = [
        f".. _sector-{name}:",
        "",
        heading(name, "#", overline=True),
        sector["description"],
        "",
        f":Requires: {links(sector['required_sectors'], 'sector')}",
        f":Carriers: {links(sector_carriers, 'carrier')}",
        "",
        heading("Carrier flows", "="),
        f"{LEGEND} Dashed elements belong to another sector. Scroll to zoom, drag "
        "to pan, or open the diagram in full screen.",
        "",
        *mermaid(diagram, zoom=True),
        heading("Technologies", "="),
        "Technologies that are also declared by another sector are only part of "
        "the model when all of their sectors are included.",
        "",
        ".. list-table::",
        "   :header-rows: 1",
        "   :widths: 22 18 20 20 20",
        "",
        "   * - Technology",
        "     - Type",
        "     - Input",
        "     - Output",
        "     - Also in",
    ]
    for tech_name in sector_technologies:
        tech = technologies[tech_name]
        if "input_carrier" in tech:
            inputs, outputs = tech["input_carrier"], tech["output_carrier"]
        else:
            inputs = outputs = tech["reference_carrier"]
        others = [s for s in tech["sectors"] if s != name]
        lines += [
            f"   * - :ref:`{tech_name} <tech-{tech_name}>`",
            f"     - {TECHNOLOGY_TYPES[tech['type']].split()[0]}",
            f"     - {links(inputs, 'carrier', carriers)}",
            f"     - {links(outputs, 'carrier', carriers)}",
            f"     - {links(others, 'sector') if others else ''}",
        ]
    return "\n".join(lines) + "\n"


def render_technologies(structure: dict) -> str:
    technologies = structure["technologies"]
    carriers = structure["carriers"]
    lines = [
        ".. _model_structure.technologies:",
        "",
        heading("Technologies", "#", overline=True),
        f"{LEGEND} The reference carrier, in which the capacity of a technology is "
        "measured, has a thick border.",
        "",
    ]
    for technology_type, title in TECHNOLOGY_TYPES.items():
        lines += [f".. _model_structure.{technology_type}:", "", heading(title, "=")]
        for name in sort_names(technologies):
            tech = technologies[name]
            if tech["type"] != technology_type:
                continue
            diagram = flow_diagram(
                [name], structure, highlight=tech["reference_carrier"]
            )
            lines += [
                f".. _tech-{name}:",
                "",
                heading(name, "-"),
                ".. container:: natural-size",
                "",
                *mermaid(diagram, indent="   "),
                f":Sectors: {links(tech['sectors'], 'sector')}",
                ":Reference carrier: "
                f"{links(tech['reference_carrier'], 'carrier', carriers)}",
            ]
            if "input_carrier" in tech:
                lines += [
                    ":Input carriers: "
                    f"{links(tech['input_carrier'], 'carrier', carriers)}",
                    ":Output carriers: "
                    f"{links(tech['output_carrier'], 'carrier', carriers)}",
                ]
            if "base_technology" in tech:
                lines += [
                    ":Retrofit reference carrier: "
                    f"{links(tech['retrofit_reference_carrier'], 'carrier', carriers)}",
                    ":Base technology: "
                    f"{links([tech['base_technology']], 'tech', technologies)}",
                ]
            lines.append("")
    return "\n".join(lines)


def render_carriers(structure: dict) -> str:
    lines = [
        ".. _model_structure.carriers:",
        "",
        heading("Carriers", "#", overline=True),
    ]
    for name in sort_names(structure["carriers"]):
        carrier = structure["carriers"][name]
        lines += [
            f".. _carrier-{name}:",
            "",
            heading(name, "="),
            f":Sectors: {links(carrier['sectors'], 'sector')}",
            f":Produced by: {links(carrier['produced_by'], 'tech')}",
            f":Consumed by: {links(carrier['consumed_by'], 'tech')}",
        ]
        if carrier["stored_by"]:
            lines.append(f":Stored by: {links(carrier['stored_by'], 'tech')}")
        if carrier["transported_by"]:
            lines.append(f":Transported by: {links(carrier['transported_by'], 'tech')}")
        lines.append("")
    return "\n".join(lines)


def write_model_structure_docs(app) -> None:
    """Write the pages to files/generated/model_structure in the docs folder."""
    out = Path(app.confdir) / "files" / "generated" / "model_structure"
    shutil.rmtree(out, ignore_errors=True)
    (out / "sectors").mkdir(parents=True)

    logging.getLogger("zen_creator").setLevel(logging.WARNING)
    structure = default_structure()
    (out / "index.rst").write_text(render_index(structure), encoding="utf-8")
    (out / "technologies.rst").write_text(
        render_technologies(structure), encoding="utf-8"
    )
    (out / "carriers.rst").write_text(render_carriers(structure), encoding="utf-8")
    for name in structure["sectors"]:
        (out / "sectors" / f"{name}.rst").write_text(
            render_sector(name, structure), encoding="utf-8"
        )
