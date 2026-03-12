"""Tests for visualize_accelerometry.state."""

import os

import pandas as pd
import pytest

from visualize_accelerometry.state import AppState


class TestAppStateInit:
    """Tests for AppState initialization."""

    def test_creates_with_username(self, patch_config, sample_h5):
        state = AppState("test_user")
        assert state.username == "test_user"

    def test_discovers_files(self, patch_config, sample_h5):
        state = AppState("test_user")
        assert len(state.lst_fnames) == 1

    def test_sets_initial_fname(self, patch_config, sample_h5):
        state = AppState("test_user")
        assert "900001-20230315093000" in state.fname

    def test_default_windowsize(self, patch_config, sample_h5):
        state = AppState("test_user")
        assert state.windowsize == 3600

    def test_annotation_cds_keys(self, patch_config, sample_h5):
        state = AppState("test_user")
        expected = {"chair_stand", "3m_walk", "6min_walk", "tug",
                    "segment", "scoring", "review"}
        assert set(state.annotation_cds.keys()) == expected

    def test_initial_selection_bounds_none(self, patch_config, sample_h5):
        state = AppState("test_user")
        assert state.selection_bounds is None


class TestAppStateLoadFile:
    """Tests for loading signal data."""

    def test_load_file_data(self, patch_config, sample_h5):
        state = AppState("test_user")
        pdf = state.load_file_data()
        assert pdf is not None
        assert len(pdf) > 0
        assert "timestamp" in pdf.columns

    def test_sets_anchor_and_bounds(self, patch_config, sample_h5):
        state = AppState("test_user")
        state.load_file_data()
        assert state.anchor_timestamp is not None
        assert state.file_start_timestamp is not None
        assert state.file_end_timestamp is not None

    def test_stores_signal_data(self, patch_config, sample_h5):
        state = AppState("test_user")
        pdf = state.load_file_data()
        assert state.pdf_signal_to_display is pdf


class TestAppStateAnnotations:
    """Tests for annotation management in AppState."""

    def test_loads_annotations(self, patch_config, sample_h5, sample_annotations):
        state = AppState("test_user")
        assert len(state.pdf_annotations) == 2

    def test_refresh_annotations(self, patch_config, sample_h5, sample_annotations):
        state = AppState("test_user")
        state.refresh_annotations()
        assert len(state.pdf_annotations) == 2

    def test_get_displayed_annotations_filters(
        self, patch_config, sample_h5, sample_annotations,
    ):
        state = AppState("test_user")
        displayed = state.get_displayed_annotations()
        assert all(displayed["user"] == "test_user")
        assert all(
            displayed["fname"] == os.path.basename(state.fname)
        )

    def test_update_annotation_sources(
        self, patch_config, sample_h5, sample_annotations,
    ):
        state = AppState("test_user")
        state.update_annotation_sources()
        # chair_stand annotation should appear in the CDS
        cs_data = state.annotation_cds["chair_stand"].data
        assert len(cs_data["start_time"]) == 1
