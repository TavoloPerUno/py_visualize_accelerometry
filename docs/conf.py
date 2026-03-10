"""Sphinx configuration for Accelerometry Annotation Tool documentation."""

import os
import sys

# Add project root to sys.path so autodoc can import the package
sys.path.insert(0, os.path.abspath(".."))

project = "Accelerometry Annotation Tool"
copyright = "2021, NSHAP Lab — University of Chicago"
author = "NSHAP Lab"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "myst_parser",
]

# MyST allows us to use Markdown (.md) files alongside reStructuredText
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

# Napoleon settings for numpy-style docstrings
napoleon_google_docstring = False
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True

# Mock heavy dependencies so autodoc works in CI without installing them
autodoc_mock_imports = [
    "panel", "bokeh", "pandas", "numpy", "tables", "openpyxl", "lttbc",
]
