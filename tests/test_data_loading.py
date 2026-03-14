"""Tests for visualize_accelerometry.data_loading."""

import os

import numpy as np
import pandas as pd
import pytest

from visualize_accelerometry.config import ANNOTATION_COLUMNS, TIME_FMT
from visualize_accelerometry.data_loading import (
    clamp_anchor,
    cleanup_annotations,
    get_annotations_from_files,
    get_filedata,
    get_filenames,
    save_annotations,
)


class TestGetFilenames:
    """Tests for file discovery and user assignment."""

    def test_discovers_h5_files(self, patch_config, sample_h5):
        fnames = get_filenames()
        assert len(fnames) == 1
        assert "900001-20230315093000" in fnames[0]

    def test_deterministic_assignment(self, patch_config, sample_h5, second_h5):
        """Same seed produces same assignment across calls."""
        first = get_filenames()
        second = get_filenames()
        assert first == second

    def test_assigns_all_files(self, patch_config, sample_h5, second_h5):
        fnames = get_filenames()
        assert len(fnames) == 2
        basenames = [f.split("--")[1] for f in fnames]
        assert "900001-20230315093000" in basenames
        assert "900002-20230316140000" in basenames

    def test_format_is_user_dash_dash_filename(self, patch_config, sample_h5):
        from visualize_accelerometry.config import ANNOTATOR_USERS
        fnames = get_filenames()
        for f in fnames:
            parts = f.split("--")
            assert len(parts) == 2
            assert parts[0] in ANNOTATOR_USERS

    def test_ignores_non_h5_files(self, patch_config, tmp_data_dir):
        readings = tmp_data_dir / "readings"
        (readings / "not_a_data_file.csv").write_text("x,y,z")
        fnames = get_filenames()
        assert len(fnames) == 0

    def test_no_global_rng_pollution(self, patch_config, sample_h5):
        """Ensure get_filenames doesn't pollute global numpy random state."""
        np.random.seed(123)
        before = np.random.random()
        np.random.seed(123)
        get_filenames()
        after = np.random.random()
        assert before == after


class TestGetFiledata:
    """Tests for HDF5 time-window loading."""

    def test_first_load_returns_bounds(self, sample_h5):
        fname = str(sample_h5).replace(".h5", "")
        anchor, start, end, pdf = get_filedata(fname, None, 3600)
        assert anchor is not None
        assert start is not None
        assert end is not None
        assert len(pdf) > 0

    def test_subsequent_load_no_bounds(self, sample_h5):
        fname = str(sample_h5).replace(".h5", "")
        anchor, start, end, pdf = get_filedata(fname, None, 3600)
        anchor2, start2, end2, pdf2 = get_filedata(fname, anchor, 3600)
        assert start2 is None
        assert end2 is None

    def test_returns_expected_columns(self, sample_h5):
        fname = str(sample_h5).replace(".h5", "")
        _, _, _, pdf = get_filedata(fname, None, 3600)
        assert "timestamp" in pdf.columns
        assert "x" in pdf.columns
        assert "y" in pdf.columns
        assert "z" in pdf.columns

    def test_windowed_query(self, sample_h5):
        """Small window should return fewer rows than the full file."""
        fname = str(sample_h5).replace(".h5", "")
        _, _, _, pdf_full = get_filedata(fname, None, 3600)
        anchor = pdf_full["timestamp"].iloc[len(pdf_full) // 2].strftime(TIME_FMT)
        _, _, _, pdf_small = get_filedata(fname, anchor, 1)
        assert len(pdf_small) <= len(pdf_full)


class TestClampAnchor:
    """Tests for anchor clamping logic."""

    def test_anchor_within_bounds_unchanged(self):
        start = "Mar 15 2023 09:00 AM"
        end = "Mar 15 2023 10:00 AM"
        anchor = "Mar 15 2023 09:30 AM"
        result = clamp_anchor(anchor, start, end, 600)
        assert result == anchor

    def test_anchor_past_end_clamped(self):
        start = "Mar 15 2023 09:00 AM"
        end = "Mar 15 2023 10:00 AM"
        anchor = "Mar 15 2023 10:30 AM"
        result = clamp_anchor(anchor, start, end, 600)
        from datetime import datetime
        result_dt = datetime.strptime(result, TIME_FMT)
        end_dt = datetime.strptime(end, TIME_FMT)
        assert result_dt < end_dt

    def test_anchor_before_start_clamped(self):
        start = "Mar 15 2023 09:00 AM"
        end = "Mar 15 2023 10:00 AM"
        anchor = "Mar 15 2023 08:00 AM"
        result = clamp_anchor(anchor, start, end, 600)
        from datetime import datetime
        result_dt = datetime.strptime(result, TIME_FMT)
        start_dt = datetime.strptime(start, TIME_FMT)
        assert result_dt > start_dt


class TestAnnotations:
    """Tests for annotation I/O and cleanup."""

    def test_load_annotations(self, patch_config, sample_annotations):
        pdf = get_annotations_from_files()
        assert len(pdf) == 2
        assert set(pdf["artifact"]) == {"chair_stand", "tug"}

    def test_load_empty_returns_empty_df(self, patch_config):
        pdf = get_annotations_from_files()
        assert len(pdf) == 0
        assert list(pdf.columns) == ANNOTATION_COLUMNS

    def test_cleanup_sorts_and_fills(self):
        pdf = pd.DataFrame({
            "fname": ["f1", "f2"],
            "artifact": ["tug", "chair_stand"],
            "segment": [1, np.nan],
            "scoring": [np.nan, 1],
            "review": [0, np.nan],
            "start_epoch": [100, np.nan],
            "end_epoch": [200, np.nan],
            "start_time": pd.to_datetime(["2023-01-01", None]),
            "end_time": pd.to_datetime(["2023-01-02", None]),
            "annotated_at": pd.to_datetime(["2023-01-01", "2023-01-01"]),
            "user": ["a", "b"],
            "notes": [None, "test"],
        })
        result = cleanup_annotations(pdf)
        assert result["segment"].isna().sum() == 0
        assert result["scoring"].isna().sum() == 0
        assert result["review"].isna().sum() == 0
        assert pd.api.types.is_string_dtype(result["notes"])

    def test_cleanup_adds_notes_column(self):
        pdf = pd.DataFrame({
            "fname": ["f1"],
            "artifact": ["tug"],
            "segment": [0], "scoring": [0], "review": [0],
            "start_epoch": [100], "end_epoch": [200],
            "start_time": pd.to_datetime(["2023-01-01"]),
            "end_time": pd.to_datetime(["2023-01-02"]),
            "annotated_at": pd.to_datetime(["2023-01-01"]),
            "user": ["a"],
        })
        result = cleanup_annotations(pdf)
        assert "notes" in result.columns

    def test_save_and_reload(self, patch_config, sample_annotations):
        pdf = get_annotations_from_files()
        pdf = cleanup_annotations(pdf)

        # Add a new annotation
        new_row = pd.DataFrame({
            "fname": ["900001-20230315093000"],
            "artifact": ["3m_walk"],
            "segment": [0], "scoring": [0], "review": [0],
            "start_epoch": [1678872700.0], "end_epoch": [1678872720.0],
            "start_time": pd.to_datetime(["2023-03-15 09:31:40"]),
            "end_time": pd.to_datetime(["2023-03-15 09:32:00"]),
            "annotated_at": pd.to_datetime(["2023-03-17 11:00:00"]),
            "user": ["test_user"],
            "notes": [""],
        })
        pdf = pd.concat([pdf, new_row], ignore_index=True)

        result = save_annotations(
            pdf, "test_user", "900001-20230315093000",
        )
        assert len(result) == 3
        assert "3m_walk" in result["artifact"].values

    def test_save_preserves_other_files(self, patch_config, sample_annotations):
        """Saving annotations for one file shouldn't delete annotations for other files."""
        pdf = get_annotations_from_files()
        pdf = cleanup_annotations(pdf)

        # Save with only one file's annotations modified
        result = save_annotations(
            pdf, "test_user", "900001-20230315093000",
        )
        assert len(result) == 2
