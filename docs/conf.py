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
    "sphinx_copybutton",
]

# MyST allows us to use Markdown (.md) files alongside reStructuredText
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- HTML output (Furo theme with UChicago branding) ------------------------

html_theme = "furo"
html_title = "Accelerometry Annotation Tool"
html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_favicon = "_static/favicon.svg"

pygments_style = "friendly"
pygments_dark_style = "monokai"

html_theme_options = {
    "light_css_variables": {
        "color-brand-primary": "#800000",
        "color-brand-content": "#800000",
    },
    "dark_css_variables": {
        "color-brand-primary": "#c26e6e",
        "color-brand-content": "#c26e6e",
    },
    "source_repository": "https://github.com/TavoloPerUno/py_visualize_accelerometry",
    "source_branch": "master",
    "source_directory": "docs/",
    "footer_icons": [
        {
            "name": "GitHub",
            "url": "https://github.com/TavoloPerUno/py_visualize_accelerometry",
            "html": (
                '<svg stroke="currentColor" fill="currentColor" stroke-width="0" '
                'viewBox="0 0 16 16"><path fill-rule="evenodd" d="M8 0C3.58 0 0 '
                "3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 "
                "0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94"
                "-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 "
                "1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-"
                "3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 "
                ".67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 "
                "1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 "
                "1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 "
                "0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 "
                '8c0-4.42-3.58-8-8-8z"></path></svg>'
            ),
            "class": "",
        },
    ],
    "announcement": (
        '<a href="https://pypi.org/project/accelerometry-annotator/">Install from PyPI</a>'
        " &mdash; "
        '<a href="https://tavoloperuno-accelerometry-viewer-demo.hf.space/">Try the live demo</a>'
    ),
}

# --- Sitemap ---
html_baseurl = "https://tavoloperuno.github.io/py_visualize_accelerometry/"
sitemap_url_scheme = "{link}"

# --- robots.txt ---
html_extra_path = ["_static/robots.txt", "_static/googlef63886eaa754b15d.html"]

# --- SEO meta tags ---
html_meta = {
    "description": (
        "Accelerometry Annotation Tool — an interactive application for "
        "annotating accelerometer data from physical performance "
        "tests including chair stand, TUG, and 6-minute walk test in the "
        "NSHAP aging-research study."
    ),
    "keywords": (
        "accelerometry, annotation tool, physical performance tests, "
        "accelerometer, chair stand, TUG, timed up and go, "
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
