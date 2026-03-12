"""Shared test fixtures.

Creates temporary HDF5 files and annotation Excel files that mirror the
production data layout, so tests run without needing real data.
"""

import os
import json

import numpy as np
import pandas as pd
import pytest


@pytest.fixture()
def tmp_data_dir(tmp_path):
    """Create a temporary data directory with readings/ and output/ subdirs."""
    readings = tmp_path / "readings"
    output = tmp_path / "output"
    readings.mkdir()
    output.mkdir()
    return tmp_path


@pytest.fixture()
def sample_h5(tmp_data_dir):
    """Write a small HDF5 file with 1000 rows of accelerometry data."""
    readings_dir = tmp_data_dir / "readings"
    rng = np.random.default_rng(42)
    n = 1000
    timestamps = pd.date_range("2023-03-15 09:30:00", periods=n, freq="12ms")
    df = pd.DataFrame({
        "timestamp": timestamps,
        "x": rng.normal(0, 0.3, n),
        "y": rng.normal(0, 0.2, n),
        "z": rng.normal(1.0, 0.1, n),
        "light": rng.uniform(100, 800, n),
        "button": np.zeros(n),
        "temperature": rng.normal(25, 0.5, n),
    })
    filepath = readings_dir / "900001-20230315093000.h5"
    df.to_hdf(
        str(filepath), key="readings", format="table",
        data_columns=["timestamp"],
    )
    return filepath


@pytest.fixture()
def second_h5(tmp_data_dir):
    """Write a second HDF5 file for multi-file tests."""
    readings_dir = tmp_data_dir / "readings"
    rng = np.random.default_rng(99)
    n = 500
    timestamps = pd.date_range("2023-03-16 14:00:00", periods=n, freq="12ms")
    df = pd.DataFrame({
        "timestamp": timestamps,
        "x": rng.normal(0, 0.3, n),
        "y": rng.normal(0, 0.2, n),
        "z": rng.normal(1.0, 0.1, n),
        "light": rng.uniform(100, 800, n),
        "button": np.zeros(n),
        "temperature": rng.normal(25, 0.5, n),
    })
    filepath = readings_dir / "900002-20230316140000.h5"
    df.to_hdf(
        str(filepath), key="readings", format="table",
        data_columns=["timestamp"],
    )
    return filepath


@pytest.fixture()
def sample_annotations(tmp_data_dir):
    """Write a sample annotation Excel file."""
    output_dir = tmp_data_dir / "output"
    df = pd.DataFrame({
        "fname": ["900001-20230315093000", "900001-20230315093000"],
        "artifact": ["chair_stand", "tug"],
        "segment": [1, 0],
        "scoring": [1, 1],
        "review": [0, 0],
        "start_epoch": [1678872600.0, 1678872660.0],
        "end_epoch": [1678872625.0, 1678872675.0],
        "start_time": pd.to_datetime(["2023-03-15 09:30:00", "2023-03-15 09:31:00"]),
        "end_time": pd.to_datetime(["2023-03-15 09:30:25", "2023-03-15 09:31:15"]),
        "annotated_at": pd.to_datetime(["2023-03-17 10:00:00", "2023-03-17 10:01:00"]),
        "user": ["test_user", "test_user"],
        "notes": ["", "boundary unclear"],
    })
    filepath = output_dir / "annotations_test_user.xlsx"
    df.to_excel(str(filepath), index=False)
    return filepath


@pytest.fixture()
def patch_config(tmp_data_dir, monkeypatch):
    """Patch config module to point at temporary data directories."""
    from visualize_accelerometry import config
    monkeypatch.setattr(config, "DATA_FOLDER", str(tmp_data_dir))
    monkeypatch.setattr(config, "READINGS_FOLDER", str(tmp_data_dir / "readings"))
    monkeypatch.setattr(config, "OUTPUT_FOLDER", str(tmp_data_dir / "output"))
    monkeypatch.setattr(
        config, "ANNOTATIONS_GLOB",
        str(tmp_data_dir / "output" / "annotations_*.xlsx"),
    )
    creds_path = tmp_data_dir / "credentials.json"
    creds_path.write_text(json.dumps({"test_admin": "pass", "test_user": "pass"}))
    monkeypatch.setattr(config, "CREDENTIALS_FILE", str(creds_path))
    # Use slice assignment so that any module holding a direct reference
    # to these lists (via `from .config import ANNOTATOR_USERS`) sees
    # the patched values too.
    original_admin = config.ADMIN_USERS[:]
    original_annotator = config.ANNOTATOR_USERS[:]
    original_known = config.KNOWN_USERS[:]
    config.ADMIN_USERS[:] = ["test_admin"]
    config.ANNOTATOR_USERS[:] = sorted(["test_admin", "test_user"])
    config.KNOWN_USERS[:] = sorted(["test_admin", "test_user"])

    yield

    # Restore originals
    config.ADMIN_USERS[:] = original_admin
    config.ANNOTATOR_USERS[:] = original_annotator
    config.KNOWN_USERS[:] = original_known
