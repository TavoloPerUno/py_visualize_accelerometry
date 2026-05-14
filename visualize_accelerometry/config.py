"""
Application-wide configuration constants.

Centralizes paths, color palettes, user lists, and annotation schema
so that changes propagate consistently across all modules.
"""

import os

# ---------------------------------------------------------------------------
# UChicago brand color palette
# ---------------------------------------------------------------------------
UCHICAGO_MAROON = "#800000"
UCHICAGO_GRAY = "#58595b"
UCHICAGO_TEAL = "#7EBEC5"

# Signal line colors for the x, y, z accelerometry axes
LST_COLORS = [UCHICAGO_MAROON, UCHICAGO_TEAL, UCHICAGO_GRAY]

# Fill colors for annotation overlay quads (one per activity type)
ARTIFACT_COLORS = {
    "chair_stand": "cyan",
    "3m_walk": "magenta",
    "6min_walk": "green",
    "tug": "yellow",
}

# Visual treatment for *suggested* (algorithm-detected, not yet confirmed)
# walking segments.  Distinct from ARTIFACT_COLORS so annotators don't
# mistake suggestions for human-made labels.  Rendered with a dashed
# border on top of a translucent fill — see plotting.make_plot.
WALKING_SUGGESTION_COLOR = "#ff8c00"

# ---------------------------------------------------------------------------
# Filesystem paths
# ---------------------------------------------------------------------------
DATA_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
READINGS_FOLDER = os.path.join(DATA_FOLDER, "readings")
OUTPUT_FOLDER = os.path.join(DATA_FOLDER, "output")
# Glob pattern for per-user annotation Excel files (the * is replaced by username)
ANNOTATIONS_GLOB = os.path.join(OUTPUT_FOLDER, "annotations_*.xlsx")
# Path to the JSON credentials file used by the admin panel to add/remove users.
# Overridden by demo/config_overrides.py for demo deployments.
CREDENTIALS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "credentials.json",
)

# ---------------------------------------------------------------------------
# User lists
# These are module-level mutable lists so the admin panel can add/remove
# users at runtime without a server restart.  Because they are shared across
# sessions, admin changes take effect for all sessions immediately.
# ---------------------------------------------------------------------------
ADMIN_USERS = ["megan", "kristen", "manu"]

ANNOTATOR_USERS = sorted([
    "ideyah", "evelyn", "junny", "amritap1", "ldepablo1", "ar277",
    "megan", "kristen", "fran", "alan", "anita", "liberto",
])

KNOWN_USERS = sorted(set(ADMIN_USERS + ANNOTATOR_USERS))

# ---------------------------------------------------------------------------
# Defaults and formats
# ---------------------------------------------------------------------------
DEFAULT_WINDOW_SIZE = 3600  # seconds of signal data shown at once

# Timestamp format used for anchor time display and HDF5 queries.
# Must match the format produced by pandas dt.strftime.
TIME_FMT = "%b %d %Y %I:%M %p"

# ---------------------------------------------------------------------------
# Annotation DataFrame schema
# ---------------------------------------------------------------------------
ANNOTATION_COLUMNS = [
    "fname", "artifact", "segment", "scoring", "review",
    "start_epoch", "end_epoch", "start_time", "end_time",
    "annotated_at", "user", "notes",
]

DISPLAYED_ANNOTATION_COLUMNS = [
    "artifact", "segment", "scoring", "review",
    "start_time", "end_time", "annotated_at", "user", "notes",
]

# Walking-detection suggestions — single shared xlsx for all users and
# files.  Walking detection is deterministic per file, so there's no
# per-user variation in the algorithm output; dismissals are also shared.
WALKING_SUGGESTIONS_FILE = os.path.join(OUTPUT_FOLDER, "walking_suggestions.xlsx")
WALKING_SUGGESTION_COLUMNS = [
    "fname", "start_time", "end_time", "start_epoch", "end_epoch",
    "duration_s", "mean_step_freq_hz", "detected_at", "deleted",
]
