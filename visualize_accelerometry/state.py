import os

import pandas as pd
from bokeh.models import ColumnDataSource
import bokeh.plotting as bp

from .config import (
    ANNOTATION_COLUMNS,
    ANNOTATIONS_GLOB,
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
    """Per-session application state. Each user session gets its own instance."""

    def __init__(self, username):
        self.username = username
        self.lst_fnames = get_filenames()
        self.fname = os.path.join(READINGS_FOLDER, self.lst_fnames[0].split("--")[1])
        self.anchor_timestamp = None
        self.file_start_timestamp = None
        self.file_end_timestamp = None
        self.windowsize = DEFAULT_WINDOW_SIZE

        # DataFrames
        self.pdf_signal_to_display = None
        self.pdf_annotations = get_annotations_from_files()
        self.pdf_annotations = cleanup_annotations(self.pdf_annotations)
        self.pdf_displayed_annotations = self.pdf_annotations.copy()

        # Bokeh data sources
        self.colsource = ColumnDataSource(data=dict(timestamp=[], x=[], y=[], z=[]))
        self.selected_data = ColumnDataSource(data=dict(start_time=[], end_time=[]))
        self.selected_annotations = ColumnDataSource(
            self.pdf_annotations[DISPLAYED_ANNOTATION_COLUMNS]
        )

        empty_annot = dict(start_epoch=[], end_epoch=[], start_time=[], end_time=[])
        self.annotation_sources = {
            "chair_stand": ColumnDataSource(data=dict(**empty_annot)),
            "3m_walk": ColumnDataSource(data=dict(**empty_annot)),
            "6min_walk": ColumnDataSource(data=dict(**empty_annot)),
            "tug": ColumnDataSource(data=dict(**empty_annot)),
            "segment": ColumnDataSource(data=dict(**empty_annot, artifact=[])),
            "scoring": ColumnDataSource(data=dict(**empty_annot, artifact=[])),
            "review": ColumnDataSource(data=dict(**empty_annot, artifact=[])),
        }

    def load_file_data(self):
        """Load signal data for the current file/anchor/window."""
        from .data_loading import clamp_anchor, get_filedata

        anchor, file_start, file_end, pdf = get_filedata(
            self.fname, self.anchor_timestamp, self.windowsize
        )
        self.anchor_timestamp = anchor
        if file_start is not None:
            self.file_start_timestamp = file_start
        if file_end is not None:
            self.file_end_timestamp = file_end

        # Clamp anchor within bounds
        if self.file_start_timestamp and self.file_end_timestamp:
            self.anchor_timestamp = clamp_anchor(
                self.anchor_timestamp,
                self.file_start_timestamp,
                self.file_end_timestamp,
                self.windowsize,
            )

        self.pdf_signal_to_display = pdf
        dates = pdf["timestamp"].values
        source = bp.ColumnDataSource(pdf)
        return dates, source

    def refresh_annotations(self):
        """Reload annotations from disk."""
        self.pdf_annotations = get_annotations_from_files()
        self.pdf_annotations = cleanup_annotations(self.pdf_annotations)

    def get_displayed_annotations(self):
        """Filter annotations for current user + file."""
        self.pdf_displayed_annotations = self.pdf_annotations.loc[
            (self.pdf_annotations["user"] == self.username)
            & (self.pdf_annotations["fname"] == os.path.basename(self.fname))
        ]
        return self.pdf_displayed_annotations

    def update_annotation_sources(self):
        """Sync all annotation ColumnDataSources from pdf_annotations."""
        self.pdf_annotations = cleanup_annotations(self.pdf_annotations)
        displayed = self.get_displayed_annotations()

        artifact_keys = ["chair_stand", "3m_walk", "6min_walk", "tug"]
        for key in artifact_keys:
            subset = displayed.loc[displayed["artifact"] == key][
                ["start_epoch", "end_epoch", "start_time", "end_time"]
            ]
            self.annotation_sources[key].data.update(bp.ColumnDataSource(subset).data)

        flag_keys = ["segment", "scoring", "review"]
        for key in flag_keys:
            subset = displayed.loc[displayed[key] == 1][
                ["start_epoch", "end_epoch", "start_time", "end_time", "artifact"]
            ]
            self.annotation_sources[key].data.update(bp.ColumnDataSource(subset).data)
