"""
Per-session application state.

Each browser session (user) gets its own ``AppState`` instance that
tracks the current file, time window, signal data, and annotations.
Persistent ``ColumnDataSource`` objects are shared with Bokeh figures
so that updating ``.data`` triggers a re-render without rebuilding
the entire plot.
"""

import os

import pandas as pd
from bokeh.models import ColumnDataSource

from .config import (
    DEFAULT_WINDOW_SIZE,
    DISPLAYED_ANNOTATION_COLUMNS,
    READINGS_FOLDER,
    TIME_FMT,
)
from .data_loading import (
    cleanup_annotations,
    get_annotations_from_files,
    get_filenames,
)


class AppState:
    """Per-session application state.

    Parameters
    ----------
    username : str
        Authenticated username for this session.

    Attributes
    ----------
    signal_cds : ColumnDataSource or None
        The downsampled signal CDS currently rendered in the plot.
        Set externally by ``app.py`` / ``CallbackManager._refresh_plot``
        after each plot (re)build.
    selection_bounds : tuple or None
        ``(start_timestamp, end_timestamp)`` set by the box-select
        callback, or None when nothing is selected.
    """

    def __init__(self, username):
        self.username = username
        self.lst_fnames = get_filenames()
        self.fname = os.path.join(READINGS_FOLDER, self.lst_fnames[0].split("--")[1])
        self.anchor_timestamp = None
        self.file_start_timestamp = None
        self.file_end_timestamp = None
        self.windowsize = DEFAULT_WINDOW_SIZE

        # Signal data for the current time window
        self.pdf_signal_to_display = None

        # Annotations: full in-memory set and current-user subset
        self.pdf_annotations = get_annotations_from_files()
        self.pdf_annotations = cleanup_annotations(self.pdf_annotations)
        self.pdf_displayed_annotations = self.pdf_annotations.copy()

        # Persistent ColumnDataSources for annotation overlay quads.
        # Updating .data triggers Bokeh to re-render without a plot rebuild.
        empty = dict(start_time=[], end_time=[])
        self.annotation_cds = {
            "chair_stand": ColumnDataSource(data=dict(**empty)),
            "3m_walk": ColumnDataSource(data=dict(**empty)),
            "6min_walk": ColumnDataSource(data=dict(**empty)),
            "tug": ColumnDataSource(data=dict(**empty)),
            "segment": ColumnDataSource(data=dict(**empty)),
            "scoring": ColumnDataSource(data=dict(**empty)),
            "review": ColumnDataSource(data=dict(**empty)),
        }

        # CDS for the "selected bounds" and "selected annotations" tables
        self.selected_data = ColumnDataSource(data=dict(start_time=[], end_time=[]))
        self.selected_annotations = ColumnDataSource(
            pd.DataFrame(columns=DISPLAYED_ANNOTATION_COLUMNS)
        )

        # Set by box-select callback in app.py (via selected.on_change)
        self.selection_bounds = None
        # Set after plot creation by app.py / _refresh_plot
        self.signal_cds = None

    def load_file_data(self):
        """Load signal data for the current file, anchor, and window size.

        Returns
        -------
        DataFrame or None
            Signal data with ``timestamp``, ``x``, ``y``, ``z`` columns,
            or None if the file is empty / unreadable.
        """
        from .data_loading import clamp_anchor, get_filedata

        anchor, file_start, file_end, pdf = get_filedata(
            self.fname, self.anchor_timestamp, self.windowsize
        )
        self.anchor_timestamp = anchor
        if file_start is not None:
            self.file_start_timestamp = file_start
        if file_end is not None:
            self.file_end_timestamp = file_end

        # Keep the anchor inside the file so next/prev don't run off the edge
        if self.file_start_timestamp and self.file_end_timestamp:
            self.anchor_timestamp = clamp_anchor(
                self.anchor_timestamp,
                self.file_start_timestamp,
                self.file_end_timestamp,
                self.windowsize,
            )

        self.pdf_signal_to_display = pdf
        return pdf

    def refresh_annotations(self):
        """Reload annotations from disk (all users, all files)."""
        self.pdf_annotations = get_annotations_from_files()
        self.pdf_annotations = cleanup_annotations(self.pdf_annotations)

    def get_displayed_annotations(self):
        """Filter annotations for the current user and file.

        Returns
        -------
        DataFrame
            Subset of ``pdf_annotations`` matching the current
            ``username`` and ``fname``.
        """
        self.pdf_displayed_annotations = self.pdf_annotations.loc[
            (self.pdf_annotations["user"] == self.username)
            & (self.pdf_annotations["fname"] == os.path.basename(self.fname))
        ]
        return self.pdf_displayed_annotations

    def update_annotation_sources(self):
        """Sync all annotation ColumnDataSources from ``pdf_annotations``.

        Filters out rows with NaT timestamps (e.g. review-only flags that
        have no time range) to prevent Bokeh NaN serialization errors.
        """
        self.pdf_annotations = cleanup_annotations(self.pdf_annotations)
        displayed = self.get_displayed_annotations()
        # Exclude review-only rows that have no time range
        has_time = displayed["start_time"].notna() & displayed["end_time"].notna()

        for key in ["chair_stand", "3m_walk", "6min_walk", "tug"]:
            subset = displayed.loc[has_time & (displayed["artifact"] == key)]
            self.annotation_cds[key].data = {
                "start_time": subset["start_time"].tolist(),
                "end_time": subset["end_time"].tolist(),
            }

        for key in ["segment", "scoring", "review"]:
            subset = displayed.loc[has_time & (displayed[key] == 1)]
            self.annotation_cds[key].data = {
                "start_time": subset["start_time"].tolist(),
                "end_time": subset["end_time"].tolist(),
            }
