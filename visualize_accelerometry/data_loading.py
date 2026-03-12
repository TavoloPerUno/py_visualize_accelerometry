"""
Data loading and persistence for accelerometry signals and annotations.

Handles HDF5 signal file discovery, time-windowed data loading, annotation
file I/O (Excel-based), and DataFrame normalization.
"""

import glob
import os
from itertools import cycle

import numpy as np
import pandas as pd

from . import config as _config
from .config import (
    ANNOTATION_COLUMNS,
    ANNOTATOR_USERS,
    TIME_FMT,
)


def get_filenames():
    """Discover HDF5 files and assign each to an annotator deterministically.

    Returns
    -------
    list of str
        Sorted list of ``"username--filename"`` strings.  The assignment
        uses a fixed random seed so every server restart produces the
        same mapping, distributing files evenly across annotators.
    """
    # Fixed seed ensures the same user-to-file assignment across restarts.
    # Use a local Generator to avoid polluting global NumPy random state.
    rng = np.random.default_rng(2020)
    users_to_assign = list(ANNOTATOR_USERS)
    rng.shuffle(users_to_assign)
    users_cycle = cycle(users_to_assign)
    lst_files = sorted(
        next(users_cycle) + "--" + os.path.splitext(f)[0]
        for f in os.listdir(_config.READINGS_FOLDER)
        if os.path.splitext(f)[1].lower() == ".h5"
    )
    return lst_files


def get_filedata(fname, anchor_timestamp, windowsize):
    """Load a time window of accelerometry data from an HDF5 file.

    Parameters
    ----------
    fname : str
        Path to the HDF5 file (without ``.h5`` extension).
    anchor_timestamp : str or None
        Center of the time window in ``TIME_FMT``.  If None, the window
        starts at the beginning of the file.
    windowsize : float
        Total window duration in seconds.

    Returns
    -------
    tuple of (str, str or None, str or None, DataFrame)
        ``(anchor_timestamp, file_start, file_end, pdf)`` where
        ``file_start`` and ``file_end`` are only set on the first load
        (when anchor_timestamp was None).
    """
    from datetime import datetime, timedelta

    file_path = fname + ".h5"

    if anchor_timestamp is None:
        # First load: read the first and last rows to determine file bounds
        first_row = pd.read_hdf(file_path, "readings", start=0, stop=1)
        with pd.HDFStore(file_path, mode="r") as store:
            nrows = store.get_storer("readings").nrows
        last_row = pd.read_hdf(file_path, "readings", start=nrows - 1, stop=nrows)
        anchor_timestamp = first_row["timestamp"].dt.strftime(TIME_FMT).values[0]
        file_start = first_row["timestamp"].dt.strftime(TIME_FMT).values[0]
        file_end = last_row["timestamp"].dt.strftime(TIME_FMT).values[0]
    else:
        # Subsequent loads: file bounds already known by the caller
        file_start = None
        file_end = None

    anchor_dt = datetime.strptime(anchor_timestamp, TIME_FMT)
    half_window = timedelta(seconds=int(windowsize / 2))
    start_dt = anchor_dt - half_window
    end_dt = anchor_dt + half_window

    start_str = start_dt.strftime(TIME_FMT)
    end_str = end_dt.strftime(TIME_FMT)

    # HDF5 where-clause pushes filtering to the storage layer for speed
    pdf = pd.read_hdf(
        file_path,
        "readings",
        where=f"(timestamp >= Timestamp('{start_str}')) & (timestamp <= Timestamp('{end_str}'))",
    )

    return anchor_timestamp, file_start, file_end, pdf


def clamp_anchor(anchor_timestamp, file_start, file_end, windowsize):
    """Clamp anchor_timestamp so the window stays within file bounds.

    Parameters
    ----------
    anchor_timestamp : str
        Current anchor in ``TIME_FMT``.
    file_start, file_end : str
        File bounds in ``TIME_FMT``.
    windowsize : float
        Window duration in seconds.

    Returns
    -------
    str
        Clamped anchor in ``TIME_FMT``.
    """
    from datetime import datetime, timedelta

    anchor_dt = datetime.strptime(anchor_timestamp, TIME_FMT)
    start_dt = datetime.strptime(file_start, TIME_FMT)
    end_dt = datetime.strptime(file_end, TIME_FMT)

    # Prevent the window from extending past either end of the file
    if anchor_dt >= end_dt:
        anchor_dt = end_dt - timedelta(seconds=int(windowsize / 2))
    if anchor_dt <= start_dt:
        anchor_dt = start_dt + timedelta(seconds=int(windowsize / 2))

    return anchor_dt.strftime(TIME_FMT)


def get_annotations_from_files(pattern=None):
    """Load all per-user annotation Excel files and concatenate them.

    Parameters
    ----------
    pattern : str, optional
        Glob pattern for annotation files.  Defaults to ``ANNOTATIONS_GLOB``.

    Returns
    -------
    DataFrame
        Combined annotations (unsorted, not yet cleaned).
    """
    if pattern is None:
        pattern = _config.ANNOTATIONS_GLOB
    files = [n for n in glob.glob(pattern) if os.path.isfile(n)]
    if files:
        return pd.concat([pd.read_excel(n, engine="openpyxl") for n in files])
    return pd.DataFrame(columns=ANNOTATION_COLUMNS)


def cleanup_annotations(pdf):
    """Sort and normalize an annotation DataFrame.

    Ensures consistent types for datetime, numeric, and string columns
    so that downstream code (Bokeh serialization, DataFrame filtering)
    doesn't encounter NaN or mixed-type surprises.

    Parameters
    ----------
    pdf : DataFrame
        Raw or partially-processed annotations.

    Returns
    -------
    DataFrame
        Cleaned copy.
    """
    pdf = pdf.sort_values(
        by=["user", "fname", "artifact", "segment", "scoring", "review", "annotated_at"],
        ascending=False,
    )
    if pdf.shape[0] > 0:
        if "notes" not in pdf.columns:
            pdf = pdf.assign(notes="")
        pdf = pdf.assign(
            start_time=pd.to_datetime(pdf["start_time"], errors="coerce"),
            end_time=pd.to_datetime(pdf["end_time"], errors="coerce"),
            notes=pdf["notes"].fillna(""),
        )
        # Fill NaN in numeric columns to prevent Bokeh JSON serialization
        # errors (Bokeh's PayloadEncoder has allow_nan=False)
        for col in ["segment", "scoring", "review", "start_epoch", "end_epoch"]:
            if col in pdf.columns:
                pdf[col] = pdf[col].fillna(0)
    pdf = pdf.assign(notes=pdf["notes"].astype(str))
    return pdf


def save_annotations(pdf_annotations, uname, fname):
    """Persist the current user's annotations for one file to disk.

    Merges the in-memory annotations with any existing data from other
    files in the user's Excel file, then writes the result.

    Parameters
    ----------
    pdf_annotations : DataFrame
        Full in-memory annotation set (all users, all files).
    uname : str
        Current user whose annotations should be saved.
    fname : str
        Current file path (basename is extracted internally).

    Returns
    -------
    DataFrame
        Freshly-reloaded annotations from *all* users' files on disk.
    """
    annotations_file = _config.ANNOTATIONS_GLOB.replace("*", uname)
    pdf_old = pd.DataFrame(columns=ANNOTATION_COLUMNS)
    if os.path.exists(annotations_file):
        pdf_old = pd.read_excel(annotations_file, engine="openpyxl")
        pdf_old = pdf_old.assign(
            annotated_at=pd.to_datetime(pdf_old["annotated_at"], errors="coerce")
        )

    basename = os.path.basename(fname)
    pdf_current = pdf_annotations.loc[
        (pdf_annotations["user"] == uname)
        & (pdf_annotations["fname"] == basename)
    ]

    if pdf_old.shape[0] > 0:
        # Replace only the current user+file slice, keep everything else
        pdf_all = pd.concat(
            [
                pdf_old.loc[
                    ~((pdf_old["user"] == uname) & (pdf_old["fname"] == basename))
                ],
                pdf_current,
            ],
            ignore_index=True,
        ).reset_index(drop=True)
    else:
        pdf_all = pdf_current

    pdf_all = cleanup_annotations(pdf_all)
    pdf_all.to_excel(annotations_file, index=False)

    # Reload from disk so all sessions see a consistent snapshot
    return get_annotations_from_files()
