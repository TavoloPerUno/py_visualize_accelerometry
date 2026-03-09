import os

# Colors for plot lines (x, y, z axes)
LST_COLORS = ["red", "blue", "green"]

# Annotation artifact types and their display colors
ARTIFACT_COLORS = {
    "chair_stand": "cyan",
    "3m_walk": "magenta",
    "6min_walk": "green",
    "tug": "yellow",
}

# Paths
DATA_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
READINGS_FOLDER = os.path.join(DATA_FOLDER, "readings")
OUTPUT_FOLDER = os.path.join(DATA_FOLDER, "output")
ANNOTATIONS_GLOB = os.path.join(OUTPUT_FOLDER, "annotations_*.xlsx")

# Known users (used for file assignment; login users come from OAuth)
KNOWN_USERS = sorted([
    "ideyah", "evelyn", "junny", "amritap1", "ldepablo1", "ar277",
    "megan", "fran", "alan", "anita", "liberto",
])

# Default time window in seconds
DEFAULT_WINDOW_SIZE = 3600

# Timestamp format used throughout the app
TIME_FMT = "%b %d %Y %I:%M %p"

# Annotation columns
ANNOTATION_COLUMNS = [
    "fname", "artifact", "segment", "scoring", "review",
    "start_epoch", "end_epoch", "start_time", "end_time",
    "annotated_at", "user", "notes",
]

DISPLAYED_ANNOTATION_COLUMNS = [
    "artifact", "segment", "scoring", "review",
    "start_time", "end_time", "annotated_at", "user", "notes",
]
