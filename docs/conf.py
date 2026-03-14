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
    "sphinx_sitemap",
    "sphinxext.opengraph",
    "sphinxcontrib.mermaid",
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

# --- Sitemap ---
html_baseurl = "https://tavoloperuno.github.io/py_visualize_accelerometry/"
sitemap_url_scheme = "{link}"

# --- robots.txt ---
html_extra_path = ["_static/robots.txt", "_static/googlef63886eaa754b15d.html"]

# --- SEO meta tags ---
html_meta = {
    "description": (
        "Accelerometry Annotation Tool — an interactive application for "
        "annotating wrist-worn accelerometer data from physical performance "
        "tests including chair stand, TUG, and 6-minute walk test in the "
        "NSHAP aging-research study."
    ),
    "keywords": (
        "accelerometry, annotation tool, physical performance tests, "
        "wrist-worn accelerometer, chair stand, TUG, timed up and go, "
        "6-minute walk test, NSHAP, aging research, actigraphy"
    ),
}

# --- Open Graph (social sharing) ---
ogp_site_url = "https://tavoloperuno.github.io/py_visualize_accelerometry/"
ogp_site_name = "Accelerometry Annotation Tool"
ogp_description_length = 200
ogp_type = "website"

# Napoleon settings for numpy-style docstrings
napoleon_google_docstring = False
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True

# Mock heavy dependencies so autodoc works in CI without installing them
autodoc_mock_imports = [
    "panel", "bokeh", "pandas", "numpy", "tables", "openpyxl", "lttbc",
]
