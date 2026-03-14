# Data Format Reference

## HDF5 input format

The application reads accelerometry data from HDF5 files (`.h5`). Each file must contain a `readings` table with the following columns:

| Column | Type | Description |
|--------|------|-------------|
| `timestamp` | datetime64 | Measurement timestamp |
| `x` | float | Acceleration along the x-axis |
| `y` | float | Acceleration along the y-axis |
| `z` | float | Acceleration along the z-axis |

The `readings` table is stored as a PyTables (HDF5) table, which allows efficient time-range queries without loading the entire file into memory.

## File placement

Place HDF5 files in:

```
visualize_accelerometry/data/readings/
```

Any file with an `.h5` extension in this directory will be discovered by the application.

## File naming

There are no strict naming requirements — any `.h5` extension works. However, the application displays filenames in the file picker dropdown, so descriptive names are recommended. A common convention is:

```
participant_id-date.h5
```

## File assignment

Files are distributed across annotators using a **deterministic shuffle with a fixed seed**. This ensures that:

- Each annotator sees a consistent set of files across sessions
- The workload is evenly distributed
- Two annotators never see the same assignment order (reducing redundant work)

The assignment is computed at startup based on the list of available files and registered users. Admins can see all files and can impersonate other users to view their assignments.

## Annotation output format

Annotations are saved as Excel files (`.xlsx`) in:

```
visualize_accelerometry/data/output/
```

Each user's annotations are stored in a separate file named `annotations_{username}.xlsx`. Clicking **Export** in the toolbar writes the current user's complete annotation set to this file.

### Column schema

The annotation DataFrame uses the following columns, defined in `config.py` as `ANNOTATION_COLUMNS`:

| Column | Type | Description |
|--------|------|-------------|
| `fname` | string | Source HDF5 filename that was annotated |
| `artifact` | string | Activity type: `"chairstand"`, `"tug"`, `"3mw"`, or `"6mw"` |
| `segment` | bool | `True` if this annotation marks an individual repetition segment |
| `scoring` | bool | `True` if this segment was selected for frailty assessment scoring |
| `review` | bool | `True` if this annotation is flagged for peer review |
| `start_epoch` | float | Start time as Unix epoch (seconds since 1970-01-01) |
| `end_epoch` | float | End time as Unix epoch (seconds since 1970-01-01) |
| `start_time` | string | Human-readable start time (e.g., `"Nov 08 2021 11:39 AM"`) |
| `end_time` | string | Human-readable end time |
| `annotated_at` | string | Timestamp when the annotation was created or last modified |
| `user` | string | Username of the annotator who created the annotation |
| `notes` | string | Free-text notes (e.g., `"uncertain boundary"`, `"possible artifact"`) |

The subset of columns displayed in the in-app data table is defined by `DISPLAYED_ANNOTATION_COLUMNS` and omits `fname`, `start_epoch`, and `end_epoch`.

## Converting from CSV to HDF5

If your accelerometry data is in CSV format, you can convert it to the required HDF5 format using pandas:

```python
import pandas as pd

# Read the CSV file
df = pd.read_csv("recording.csv", parse_dates=["timestamp"])

# Ensure the expected columns exist
assert set(["timestamp", "x", "y", "z"]).issubset(df.columns)

# Write to HDF5 in PyTables format
df.to_hdf(
    "recording.h5",
    key="readings",
    format="table",      # use 'table' format for queryable storage
    data_columns=True,   # index all columns for fast time-range queries
)
```

The `format="table"` argument is important — it creates a PyTables table that supports efficient row-level queries, which the application uses to load only the visible time window rather than the entire file.
