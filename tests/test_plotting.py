"""Tests for visualize_accelerometry.plotting."""

import numpy as np
import pandas as pd
import pytest

from bokeh.models import ColumnDataSource

from visualize_accelerometry.plotting import _downsample, make_plot, MAX_POINTS


class TestDownsample:
    """Tests for the LTTB downsampling function."""

    def test_passthrough_when_short(self):
        ts = np.arange(100, dtype=np.float64)
        vals = np.random.randn(100)
        ds_ts, ds_vals = _downsample(ts, vals, 200)
        np.testing.assert_array_equal(ds_ts, ts)
        np.testing.assert_array_equal(ds_vals, vals)

    def test_reduces_to_target(self):
        n = 50000
        ts = np.arange(n, dtype=np.float64)
        vals = np.sin(np.linspace(0, 10 * np.pi, n))
        ds_ts, ds_vals = _downsample(ts, vals, 1000)
        assert len(ds_ts) <= 1000 + 10  # allow small tolerance
        assert len(ds_ts) > 0

    def test_preserves_dtype(self):
        ts = np.arange(
            np.datetime64("2023-01-01"),
            np.datetime64("2023-01-01") + np.timedelta64(10000, "ms"),
            np.timedelta64(1, "ms"),
        )
        vals = np.random.randn(len(ts)).astype(np.float64)
        ds_ts, ds_vals = _downsample(ts, vals, 100)
        assert ds_ts.dtype == ts.dtype


class TestMakePlot:
    """Tests for the main plot creation function."""

    def _make_annotation_cds(self):
        empty = dict(start_time=[], end_time=[])
        return {
            "chair_stand": ColumnDataSource(data=dict(**empty)),
            "3m_walk": ColumnDataSource(data=dict(**empty)),
            "6min_walk": ColumnDataSource(data=dict(**empty)),
            "tug": ColumnDataSource(data=dict(**empty)),
            "segment": ColumnDataSource(data=dict(**empty)),
            "scoring": ColumnDataSource(data=dict(**empty)),
            "review": ColumnDataSource(data=dict(**empty)),
        }

    def test_returns_four_elements(self):
        n = 2000
        pdf = pd.DataFrame({
            "timestamp": pd.date_range("2023-01-01", periods=n, freq="12ms"),
            "x": np.random.randn(n),
            "y": np.random.randn(n),
            "z": np.random.randn(n),
        })
        result = make_plot(pdf, self._make_annotation_cds())
        assert len(result) == 4

    def test_empty_data_returns_placeholders(self):
        result = make_plot(None, self._make_annotation_cds())
        assert len(result) == 4

    def test_empty_dataframe_returns_placeholders(self):
        pdf = pd.DataFrame(columns=["timestamp", "x", "y", "z"])
        result = make_plot(pdf, self._make_annotation_cds())
        assert len(result) == 4

    def test_signal_cds_has_expected_keys(self):
        n = 2000
        pdf = pd.DataFrame({
            "timestamp": pd.date_range("2023-01-01", periods=n, freq="12ms"),
            "x": np.random.randn(n),
            "y": np.random.randn(n),
            "z": np.random.randn(n),
        })
        _, _, _, signal_cds = make_plot(pdf, self._make_annotation_cds())
        assert "timestamp" in signal_cds.data
        assert "x" in signal_cds.data
        assert "y" in signal_cds.data
        assert "z" in signal_cds.data
