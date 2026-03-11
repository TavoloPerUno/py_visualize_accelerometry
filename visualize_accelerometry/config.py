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
