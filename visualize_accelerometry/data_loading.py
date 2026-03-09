import glob
import os
from itertools import cycle

import numpy as np
import pandas as pd

from .config import (
    ANNOTATION_COLUMNS,
    ANNOTATIONS_GLOB,
    KNOWN_USERS,
    READINGS_FOLDER,
    TIME_FMT,
)


def get_filenames():
    """Discover HDF5 files and assign them to users deterministically."""
    np.random.seed(2020)
    users_to_assign = list(KNOWN_USERS)
    np.random.shuffle(users_to_assign)
    users_cycle = cycle(users_to_assign)
    lst_files = sorted(
        next(users_cycle) + "--" + os.path.splitext(f)[0]
        for f in os.listdir(READINGS_FOLDER)
        if os.path.splitext(f)[1].lower() == ".h5"
    )
    return lst_files


def get_filedata(fname, anchor_timestamp, windowsize):
    """Load a time window of accelerometry data from an HDF5 file.

    Returns (anchor_timestamp, file_start, file_end, dataframe).
    If anchor_timestamp is None, initializes from the file's first record.
    """
    from datetime import datetime, timedelta

    file_path = fname + ".h5"

    if anchor_timestamp is None:
        first_row = pd.read_hdf(file_path, "readings", start=0, stop=1)
        last_row = pd.read_hdf(file_path, "readings", start=-1)
        anchor_timestamp = first_row["timestamp"].dt.strftime(TIME_FMT).values[0]
        file_start = first_row["timestamp"].dt.strftime(TIME_FMT).values[0]
        file_end = last_row["timestamp"].dt.strftime(TIME_FMT).values[0]
    else:
        file_start = None
        file_end = None

    # Clamp anchor within file bounds
    anchor_dt = datetime.strptime(anchor_timestamp, TIME_FMT)

    half_window = timedelta(seconds=int(windowsize / 2))
    start_dt = anchor_dt - half_window
    end_dt = anchor_dt + half_window

    start_str = start_dt.strftime(TIME_FMT)
    end_str = end_dt.strftime(TIME_FMT)

    pdf = pd.read_hdf(
        file_path,
        "readings",
        where=f"(timestamp >= Timestamp('{start_str}')) & (timestamp <= Timestamp('{end_str}'))",
    )

    return anchor_timestamp, file_start, file_end, pdf


def clamp_anchor(anchor_timestamp, file_start, file_end, windowsize):
    """Ensure anchor_timestamp stays within file bounds."""
    from datetime import datetime, timedelta

    anchor_dt = datetime.strptime(anchor_timestamp, TIME_FMT)
    start_dt = datetime.strptime(file_start, TIME_FMT)
    end_dt = datetime.strptime(file_end, TIME_FMT)

    if anchor_dt >= end_dt:
        anchor_dt = end_dt - timedelta(seconds=int(windowsize / 2))
    if anchor_dt <= start_dt:
        anchor_dt = start_dt + timedelta(seconds=int(windowsize / 2))

    return anchor_dt.strftime(TIME_FMT)


def get_annotations_from_files(pattern=None):
    """Load all annotation Excel files and concatenate them."""
    if pattern is None:
        pattern = ANNOTATIONS_GLOB
    files = [n for n in glob.glob(pattern) if os.path.isfile(n)]
    if files:
        return pd.concat([pd.read_excel(n, engine="openpyxl") for n in files])
    return pd.DataFrame(columns=ANNOTATION_COLUMNS)


def cleanup_annotations(pdf):
    """Sort and normalize annotation DataFrame."""
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
    pdf = pdf.assign(notes=pdf["notes"].astype(str))
    return pdf


def save_annotations(pdf_annotations, uname, fname):
    """Save user's annotations for the current file, merging with existing data."""
    annotations_file = ANNOTATIONS_GLOB.replace("*", uname)
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
    return get_annotations_from_files()
