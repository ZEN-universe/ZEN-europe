# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import shutil
import sys
from importlib.metadata import version as get_version
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from model_structure_docs import write_model_structure_docs  # noqa: E402

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "ZEN-europe"
copyright = "2026, Reliability and Risk Engineering lab, ETH Zurich"
author = "Jacob Mannhardt, Christoph Funke"
release = get_version("zen_europe")
language = "en"

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.mathjax",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    #              "sphinx.ext.autosectionlabel",
    "sphinx_reredirects",
    "nbsphinx",
    "nbsphinx_link",
    "myst_parser",
    "sphinx.ext.imgconverter",  # for SVG conversion
    "sphinxcontrib.mermaid",  # for class diagrams
]
# generate anchors for Markdown headings (h1-h3), for links like
# `[Diffusion](#diffusion)`
myst_heading_anchors = 3

# allow errors in the notebooks
nbsphinx_allow_errors = True

# Generate .rst files when encountering an autosummary directive
autosummary_generate = True
autosummary_generate_overwrite = False

# configure docstring options
# todo_include_todos = True  # <- REQUIRED
napoleon_attr_annotations = True
napoleon_use_ivar = False

# Specify the special members to include in the documentation
autodoc_default_options = {
    "members": True,
    "special-members": "__init__",
}

numfig = True

# Prevent Spynx from showing nested defaults and typehints.
autodoc_typehints_format = "short"

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
# exclude all jupyter notebooks
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "**.ipynb_checkpoints"]


mermaid_light_theme = "neutral"
mermaid_init_config = {
    "startOnLoad": False,
    # counter-based diagram ids, time-based ids collide on pages with many diagrams
    "deterministicIds": True,
    "classDiagram": {"curve": "basis"},
    "flowchart": {"useMaxWidth": False},
}

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
# html_theme = 'sphinx_book_theme'
html_theme = "furo"

# Theme-specific options to customize the look of a theme
# For a list of options available for each theme, see the documentation.
## sphinx_book_theme options
# html_theme_options = {
#     "repository_url": "https://github.com/ZEN-universe/ZEN-garden",
#     "use_repository_button": True,
#     "show_navbar_depth": 1,
#     "show_toc_level": 2,
# }
# GitHub mark for the footer icon linking to the repository
GITHUB_ICON = (
    '<svg stroke="currentColor" fill="currentColor" stroke-width="0" '
    'viewBox="0 0 16 16"><path fill-rule="evenodd" d="'
    "M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 "
    "0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13"
    "-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66"
    ".07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15"
    "-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 "
    "1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 "
    "1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.76.54 1.52 0 1.11-.01 "
    "2.01-.01 2.29 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z"
    '"></path></svg>'
)

html_theme_options = {
    "light_css_variables": {
        "color-brand-primary": "#215CAF",
        "color-brand-content": "#007894",
    },
    "source_repository": "https://github.com/ZEN-universe/ZEN-europe",
    "source_branch": "main",
    "source_directory": "docs/",
    "top_of_page_buttons": ["view"],
    "footer_icons": [
        {
            "name": "GitHub",
            "url": "https://github.com/ZEN-universe/ZEN-europe",
            "html": GITHUB_ICON,
            "class": "",
        },
    ],
}


# The name for this set of Sphinx documents.
html_title = "ZEN-europe"
html_short_title = "ZEN-europe"

# The name of an image file (relative to this directory)
html_logo = "files/figures/general/zen_garden_logo_text.png"

# html_favicon = "images/zen_garden_logo.svg"
html_favicon = "files/figures/general/zen_garden_logo_text.png"
# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]
html_css_files = ["model_structure.css"]


## ----------------------------------------------------------------------------
# copy changelog to allow it to appear in the documentation.
# GitHub expects the changelog in the root directory
# Sphinx requires the changelog to be in the docs folder
def copy_changelog(app):
    src = Path(app.confdir).parent / "CHANGELOG.md"
    dst = Path(app.confdir) / "files" / "generated" / "changelog.md"
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.exists():
        shutil.copy(src, dst)
    elif not dst.exists():
        dst.write_text("# Changelog\n\nNo changelog found in repository root.\n")


def setup(app):
    app.connect("builder-inited", copy_changelog)
    app.connect("builder-inited", write_model_structure_docs)
    # inline, since browsers block module scripts from files opened locally
    zoom_js = Path(app.confdir) / "mermaid_zoom.js"
    app.add_js_file(None, body=zoom_js.read_text(encoding="utf-8"), type="module")
