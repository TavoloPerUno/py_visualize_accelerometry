#!/usr/bin/env python3
"""Generate demo accelerometry HDF5 files with example annotations.

Downloads real tri-axial accelerometer data from the Accelerometer & Gyro
Mobile Phone Dataset (UCI ML Repository, CC BY 4.0) and composes realistic
10-minute recordings that exercise every feature of the annotation UI.

Also generates pre-populated annotation Excel files so the demo ships with
example labels, flags, and notes.

Falls back to synthetic sine-wave data if the download fails or --synthetic
is passed.

Usage:
    python demo/generate_data.py              # real data (downloads from UCI)
    python demo/generate_data.py --synthetic  # synthetic fallback
    python demo/generate_data.py /tmp/out     # custom output directory

Dataset citation:
    Alharbi, F. (2022). Accelerometer Gyro Mobile Phone Dataset.
    UCI Machine Learning Repository.
    https://archive.ics.uci.edu/dataset/755/accelerometer+gyro+mobile+phone+dataset
    License: CC BY 4.0
"""

import io
import json
import os
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TARGET_HZ = 85
DURATION_S = 600  # 10 minutes per file — keeps HDF5 under 10 MB
N_ROWS = TARGET_HZ * DURATION_S

# UCI dataset details (2 MB zip, single CSV inside)
DATASET_URL = (
    "https://archive.ics.uci.edu/static/public/755/"
    "accelerometer+gyro+mobile+phone+dataset.zip"
)
DATASET_CSV = "accelerometer_gyro_mobile_phone_dataset.csv"

# Activity labels in the source dataset (integer-coded: 1=walking, 0=standing)
SRC_WALKING = 1
SRC_STANDING = 0

# Demo file naming: <subject_id>-<YYYYMMDDHHmmss>.h5
FILE_SPECS = [
    {
        "filename": "900001-20230315093000.h5",
        "start": pd.Timestamp("2023-03-15 09:30:00"),
        # (source_activity, duration_seconds)  — must sum to 600 s
        "sequence": [
            (SRC_STANDING,  45),   # 0:00 – 0:45   sitting (attenuated standing)
            (SRC_STANDING,  20),   # 0:45 – 1:05   standing
            (SRC_WALKING,   25),   # 1:05 – 1:30   ← chair_stand annotation
            (SRC_STANDING,  30),   # 1:30 – 2:00   sitting
            (SRC_WALKING,   15),   # 2:00 – 2:15   ← tug annotation
            (SRC_STANDING,  30),   # 2:15 – 2:45   sitting
            (SRC_WALKING,   20),   # 2:45 – 3:05   ← 3m_walk annotation
            (SRC_STANDING,  30),   # 3:05 – 3:35   sitting
            (SRC_WALKING,   90),   # 3:35 – 5:05   ← 6min_walk annotation
            (SRC_STANDING,  45),   # 5:05 – 5:50   sitting
            (SRC_WALKING,   60),   # 5:50 – 6:50
            (SRC_STANDING,  30),   # 6:50 – 7:20   sitting
            (SRC_STANDING,  20),   # 7:20 – 7:40   standing
            (SRC_WALKING,   70),   # 7:40 – 8:50
            (SRC_STANDING,  70),   # 8:50 – 10:00  sitting
        ],
    },
    {
        "filename": "900002-20230316140000.h5",
        "start": pd.Timestamp("2023-03-16 14:00:00"),
        "sequence": [
            (SRC_STANDING,  30),   # 0:00 – 0:30   sitting
            (SRC_STANDING,  25),   # 0:30 – 0:55   standing
            (SRC_WALKING,   20),   # 0:55 – 1:15   ← 3m_walk annotation
            (SRC_STANDING,  25),   # 1:15 – 1:40   sitting
            (SRC_WALKING,   30),   # 1:40 – 2:10   ← chair_stand annotation
            (SRC_STANDING,  25),   # 2:10 – 2:35   sitting
            (SRC_WALKING,   15),   # 2:35 – 2:50   ← tug annotation
            (SRC_STANDING,  30),   # 2:50 – 3:20   sitting
            (SRC_WALKING,  120),   # 3:20 – 5:20   ← 6min_walk annotation
            (SRC_STANDING,  40),   # 5:20 – 6:00   sitting
            (SRC_WALKING,   45),   # 6:00 – 6:45
            (SRC_STANDING,  35),   # 6:45 – 7:20   sitting
            (SRC_STANDING,  25),   # 7:20 – 7:45   standing
            (SRC_WALKING,   50),   # 7:45 – 8:35
            (SRC_STANDING,  85),   # 8:35 – 10:00  sitting
        ],
    },
]

# Annotation definitions
# offset_s / end_s are seconds from file start, matching the sequences above
ANNOTATION_DEFS = [
    # --- demo_admin: complete annotations on file 1 ---
    {
        "fname": "900001-20230315093000",
        "artifact": "chair_stand", "start_s": 65, "end_s": 90,
        "segment": 1, "scoring": 1, "review": 0,
        "user": "demo_admin", "notes": "",
    },
    {
        "fname": "900001-20230315093000",
        "artifact": "tug", "start_s": 120, "end_s": 135,
        "segment": 0, "scoring": 1, "review": 0,
        "user": "demo_admin", "notes": "",
    },
    {
        "fname": "900001-20230315093000",
        "artifact": "3m_walk", "start_s": 165, "end_s": 185,
        "segment": 0, "scoring": 1, "review": 0,
        "user": "demo_admin", "notes": "",
    },
    {
        "fname": "900001-20230315093000",
        "artifact": "6min_walk", "start_s": 215, "end_s": 305,
        "segment": 0, "scoring": 0, "review": 0,
        "user": "demo_admin", "notes": "",
    },
    # --- demo_admin: partial annotations on file 2 (flags + notes) ---
    {
        "fname": "900002-20230316140000",
        "artifact": "3m_walk", "start_s": 55, "end_s": 75,
        "segment": 0, "scoring": 1, "review": 0,
        "user": "demo_admin", "notes": "",
    },
    {
        "fname": "900002-20230316140000",
        "artifact": "chair_stand", "start_s": 100, "end_s": 130,
        "segment": 0, "scoring": 0, "review": 1,
        "user": "demo_admin",
        "notes": "uncertain boundary \u2014 participant paused mid-test",
    },
    {
        "fname": "900002-20230316140000",
        "artifact": "tug", "start_s": 155, "end_s": 170,
        "segment": 0, "scoring": 1, "review": 0,
        "user": "demo_admin", "notes": "",
    },
    # --- demo_user: fewer annotations, inter-annotator variability ---
    {
        "fname": "900001-20230315093000",
        "artifact": "chair_stand", "start_s": 67, "end_s": 88,
        "segment": 0, "scoring": 0, "review": 0,
        "user": "demo_user", "notes": "",
    },
    {
        "fname": "900001-20230315093000",
        "artifact": "tug", "start_s": 120, "end_s": 135,
        "segment": 0, "scoring": 0, "review": 1,
        "user": "demo_user",
        "notes": "hard to distinguish from normal walking",
    },
]

# ---------------------------------------------------------------------------
# Dataset download and parsing
# ---------------------------------------------------------------------------

def download_dataset(cache_dir=None):
    """Download the UCI accelerometer dataset (2 MB). Returns parsed DataFrame."""
    if cache_dir is None:
        cache_dir = os.path.join(tempfile.gettempdir(), "uci_accel_cache")
    os.makedirs(cache_dir, exist_ok=True)

    cached_csv = os.path.join(cache_dir, DATASET_CSV)
    if os.path.exists(cached_csv):
        print("  Using cached dataset...")
        return _parse_dataset(cached_csv)

    print(f"  Downloading accelerometer dataset from UCI (~2 MB)...")
    try:
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp_path = tmp.name
            req = urllib.request.Request(DATASET_URL, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=60)
            tmp.write(resp.read())

        with zipfile.ZipFile(tmp_path, "r") as zf:
            # Find the CSV entry
            entry = None
            for name in zf.namelist():
                if name.endswith(".csv"):
                    entry = name
                    break
            if entry is None:
                raise FileNotFoundError("No CSV found in zip")
            with zf.open(entry) as src, open(cached_csv, "wb") as dst:
                dst.write(src.read())

        return _parse_dataset(cached_csv)
    except (urllib.error.URLError, OSError, zipfile.BadZipFile, FileNotFoundError) as exc:
        print(f"\n  WARNING: Dataset download failed: {exc}")
        return None
    finally:
        try:
            os.unlink(tmp_path)
        except (OSError, UnboundLocalError):
            pass


def _parse_dataset(path):
    """Parse the accelerometer CSV into a DataFrame with activity, x, y, z.

    The UCI dataset has columns: accX, accY, accZ, gyroX, gyroY, gyroZ,
    timestamp, Activity.  Activity is integer-coded (1=walking, 0=standing).
    Accelerometer values are in m/s².
    """
    df = pd.read_csv(path)
    # Rename to our internal names
    col_map = {"accX": "x", "accY": "y", "accZ": "z", "Activity": "activity"}
    df = df.rename(columns=col_map)

    if not {"x", "y", "z", "activity"}.issubset(df.columns):
        raise ValueError(f"Expected accX, accY, accZ, Activity columns; got {list(df.columns)}")

    # Drop rows with NaN accelerometer values
    df = df.dropna(subset=["x", "y", "z"]).reset_index(drop=True)

    # Convert m/s² to g-units (gravity ≈ 9.81 m/s²)
    df[["x", "y", "z"]] = df[["x", "y", "z"]] / 9.81

    return df[["activity", "x", "y", "z"]]


def _extract_activity_pools(df):
    """Group data by activity into pools of (x, y, z) arrays."""
    pools = {}
    for label in [SRC_WALKING, SRC_STANDING]:
        mask = df["activity"] == label
        subset = df.loc[mask, ["x", "y", "z"]].values
        pools[label] = subset
    return pools


def _sample_from_pool(pool, n_samples, rng):
    """Extract n_samples from a pool, tiling if needed. Random start offset."""
    if len(pool) == 0:
        return rng.normal(0, 0.02, (n_samples, 3))
    offset = rng.integers(0, max(1, len(pool)))
    repeats = (n_samples // len(pool)) + 2
    tiled = np.tile(pool, (repeats, 1))
    return tiled[offset:offset + n_samples]


def _estimate_hz(df):
    """Estimate sampling rate from row count and known dataset properties.

    The UCI accelerometer dataset uses timestamps in MM:SS.d format at ~10 Hz.
    We estimate from the data length and activity distribution.
    """
    # 31,991 rows over ~53 minutes ≈ 10 Hz
    # Use a simple heuristic: total rows / estimated duration
    n = len(df)
    if n > 30000:
        return 10  # matches the known ~10 Hz sampling of this dataset
    return 50  # fallback for unknown datasets


# ---------------------------------------------------------------------------
# File generation — real data
# ---------------------------------------------------------------------------

def generate_file_real(spec, pools, source_hz, output_dir, rng):
    """Compose an HDF5 file from real accelerometer data segments."""
    segments_xyz = []
    for src_activity, dur_s in spec["sequence"]:
        n_source = dur_s * source_hz
        n_target = dur_s * TARGET_HZ
        pool = pools.get(src_activity, pools[SRC_STANDING])
        raw = _sample_from_pool(pool, n_source, rng)

        # For "sitting" segments (standing data used as rest), attenuate the
        # signal toward gravity-only to simulate a quiet wrist
        if src_activity == SRC_STANDING:
            # Keep ~30% of the real variance + add subtle noise
            mean_xyz = raw.mean(axis=0)
            raw = mean_xyz + (raw - mean_xyz) * 0.3
            raw += rng.normal(0, 0.01, raw.shape)

        # Resample from source_hz to TARGET_HZ
        resampled = np.column_stack([
            np.interp(
                np.linspace(0, 1, n_target),
                np.linspace(0, 1, n_source),
                raw[:, i],
            )
            for i in range(3)
        ])
        segments_xyz.append(resampled)

    data = np.concatenate(segments_xyz, axis=0)

    # Smooth segment boundaries with a short crossfade (10 samples)
    offset = 0
    for src_activity, dur_s in spec["sequence"][:-1]:
        n = dur_s * TARGET_HZ
        offset += n
        fade = min(10, n, len(data) - offset)
        if fade > 1 and offset > fade:
            w = np.linspace(0, 1, fade).reshape(-1, 1)
            data[offset - fade:offset] = (
                data[offset - fade:offset] * (1 - w)
                + data[offset:offset + fade] * w
            )

    total = len(data)

    # Auxiliary channels (synthetic — source dataset doesn't have these)
    light = rng.uniform(100, 800, total).astype(np.float64)
    button = np.zeros(total, dtype=np.float64)
    temperature = (25.0 + rng.normal(0, 0.5, total)).astype(np.float64)

    timestamps = pd.date_range(
        start=spec["start"], periods=total,
        freq=pd.Timedelta(seconds=1 / TARGET_HZ),
    )

    df = pd.DataFrame({
        "timestamp": timestamps,
        "x": data[:, 0].astype(np.float64),
        "y": data[:, 1].astype(np.float64),
        "z": data[:, 2].astype(np.float64),
        "light": light,
        "button": button,
        "temperature": temperature,
    })

    filepath = os.path.join(output_dir, spec["filename"])
    df.to_hdf(
        filepath, key="readings", format="table",
        data_columns=["timestamp"], complevel=9, complib="zlib",
    )
    size_mb = os.path.getsize(filepath) / 1e6
    print(f"  wrote {filepath}  ({len(df):,} rows, {size_mb:.1f} MB) [UCI accelerometer]")


# ---------------------------------------------------------------------------
# File generation — synthetic fallback
# ---------------------------------------------------------------------------

SYNTHETIC_ACTIVITIES = [
    # (label, duration_s, x_freq, y_freq, z_freq, x_amp, y_amp, z_amp)
    ("sitting",      45, 0.1,  0.1,  0.05, 0.02, 0.02, 1.00),
    ("standing",     20, 0.2,  0.15, 0.1,  0.05, 0.05, 1.00),
    ("walking",      60, 1.8,  0.9,  1.8,  0.30, 0.15, 0.40),
    ("sitting",      30, 0.1,  0.1,  0.05, 0.02, 0.02, 1.00),
    ("chair_stand",  25, 0.5,  0.3,  0.8,  0.50, 0.20, 0.80),
    ("sitting",      20, 0.1,  0.1,  0.05, 0.02, 0.02, 1.00),
    ("tug",          15, 1.5,  0.8,  1.5,  0.35, 0.18, 0.45),
    ("sitting",      25, 0.1,  0.1,  0.05, 0.02, 0.02, 1.00),
    ("3m_walk",      20, 1.8,  0.9,  1.8,  0.28, 0.14, 0.38),
    ("sitting",      30, 0.1,  0.1,  0.05, 0.02, 0.02, 1.00),
    ("6min_walk",    90, 1.6,  0.8,  1.6,  0.25, 0.12, 0.35),
    ("sitting",      45, 0.1,  0.1,  0.05, 0.02, 0.02, 1.00),
    ("walking",      60, 1.7,  0.85, 1.7,  0.32, 0.16, 0.42),
    ("sitting",      30, 0.1,  0.1,  0.05, 0.02, 0.02, 1.00),
    ("standing",     30, 0.2,  0.15, 0.1,  0.05, 0.05, 1.00),
    ("walking",      30, 1.8,  0.9,  1.8,  0.30, 0.15, 0.40),
    ("sitting",      25, 0.1,  0.1,  0.05, 0.02, 0.02, 1.00),
]


def _synth_signal(n_samples, freq, amplitude, noise_std=0.03):
    """Sine wave + Gaussian noise."""
    t = np.linspace(0, n_samples / TARGET_HZ, n_samples, endpoint=False)
    return amplitude * np.sin(2 * np.pi * freq * t) + np.random.normal(0, noise_std, n_samples)


def generate_file_synthetic(spec, output_dir):
    """Build one HDF5 file from synthetic sine-wave patterns."""
    rng = np.random.default_rng(42)
    segments = []
    for _label, dur_s, xf, yf, zf, xa, ya, za in SYNTHETIC_ACTIVITIES:
        n = dur_s * TARGET_HZ
        segments.append({
            "x": _synth_signal(n, xf, xa),
            "y": _synth_signal(n, yf, ya),
            "z": _synth_signal(n, zf, za),
        })

    used = sum(d for _, d, *_ in SYNTHETIC_ACTIVITIES)
    remaining = max(0, DURATION_S - used)
    if remaining > 0:
        n = remaining * TARGET_HZ
        segments.append({
            "x": _synth_signal(n, 0.1, 0.02),
            "y": _synth_signal(n, 0.1, 0.02),
            "z": _synth_signal(n, 0.05, 1.00),
        })

    x = np.concatenate([s["x"] for s in segments]).astype(np.float64)
    y = np.concatenate([s["y"] for s in segments]).astype(np.float64)
    z = np.concatenate([s["z"] for s in segments]).astype(np.float64)
    total = len(x)

    light = rng.uniform(100, 800, total).astype(np.float64)
    button = np.zeros(total, dtype=np.float64)
    temperature = (25.0 + rng.normal(0, 0.5, total)).astype(np.float64)

    timestamps = pd.date_range(
        start=spec["start"], periods=total,
        freq=pd.Timedelta(seconds=1 / TARGET_HZ),
    )

    df = pd.DataFrame({
        "timestamp": timestamps,
        "x": x, "y": y, "z": z,
        "light": light, "button": button, "temperature": temperature,
    })

    filepath = os.path.join(output_dir, spec["filename"])
    df.to_hdf(
        filepath, key="readings", format="table",
        data_columns=["timestamp"], complevel=9, complib="zlib",
    )
    size_mb = os.path.getsize(filepath) / 1e6
    print(f"  wrote {filepath}  ({len(df):,} rows, {size_mb:.1f} MB) [synthetic]")


# ---------------------------------------------------------------------------
# Annotation generation
# ---------------------------------------------------------------------------

def generate_annotations(output_dir):
    """Create per-user annotation Excel files from ANNOTATION_DEFS."""
    rows = []
    for defn in ANNOTATION_DEFS:
        file_start = None
        for spec in FILE_SPECS:
            if spec["filename"].replace(".h5", "") == defn["fname"]:
                file_start = spec["start"]
                break
        if file_start is None:
            continue

        start_time = file_start + pd.Timedelta(seconds=defn["start_s"])
        end_time = file_start + pd.Timedelta(seconds=defn["end_s"])

        rows.append({
            "fname": defn["fname"],
            "artifact": defn["artifact"],
            "segment": defn["segment"],
            "scoring": defn["scoring"],
            "review": defn["review"],
            "start_epoch": start_time.timestamp(),
            "end_epoch": end_time.timestamp(),
            "start_time": start_time,
            "end_time": end_time,
            "annotated_at": pd.Timestamp("2023-03-17 10:00:00"),
            "user": defn["user"],
            "notes": defn["notes"],
        })

    df = pd.DataFrame(rows)

    for user, user_df in df.groupby("user"):
        path = os.path.join(output_dir, f"annotations_{user}.xlsx")
        user_df.to_excel(path, index=False)
        n = len(user_df)
        print(f"  wrote {path}  ({n} annotation{'s' if n != 1 else ''})")


# ---------------------------------------------------------------------------
# Demo configuration file generators
# ---------------------------------------------------------------------------

def create_demo_credentials(demo_dir):
    """Write demo/credentials.json with demo users."""
    creds = {"demo_admin": "demo", "demo_user": "demo"}
    path = os.path.join(demo_dir, "credentials.json")
    with open(path, "w") as f:
        json.dump(creds, f, indent=4)
    print(f"  wrote {path}")


def create_config_overrides(demo_dir):
    """Write demo/config_overrides.py that patches config for demo mode."""
    path = os.path.join(demo_dir, "config_overrides.py")
    content = '''\
"""
Demo-mode configuration overrides.

When DEMO_MODE=1 is set in the environment, the app entrypoint
(demo/app.py) imports this module to patch config values
before the UI is built.
"""

import os


def apply():
    """Patch visualize_accelerometry.config for demo deployment."""
    from visualize_accelerometry import config

    demo_dir = os.path.dirname(os.path.abspath(__file__))

    # Point data paths at the demo directory
    config.DATA_FOLDER = os.path.join(demo_dir, "data")
    config.READINGS_FOLDER = os.path.join(config.DATA_FOLDER, "readings")
    config.OUTPUT_FOLDER = os.path.join(config.DATA_FOLDER, "output")
    config.ANNOTATIONS_GLOB = os.path.join(config.OUTPUT_FOLDER, "annotations_*.xlsx")

    # Replace real users with demo users
    config.ADMIN_USERS[:] = ["demo_admin"]
    config.ANNOTATOR_USERS[:] = sorted(["demo_admin", "demo_user"])
    config.KNOWN_USERS[:] = sorted(set(config.ADMIN_USERS + config.ANNOTATOR_USERS))

    # Ensure output directory exists
    os.makedirs(config.OUTPUT_FOLDER, exist_ok=True)

    # Point CREDENTIALS_FILE at the demo credentials.
    config.CREDENTIALS_FILE = os.path.join(demo_dir, "credentials.json")
'''
    with open(path, "w") as f:
        f.write(content)
    print(f"  wrote {path}")


def create_demo_entrypoint(demo_dir):
    """Write demo/app.py — the Panel entrypoint for demo mode."""
    path = os.path.join(demo_dir, "app.py")
    content = '''\
"""
Demo-mode entrypoint for panel serve.

This script applies demo configuration overrides (demo users, demo data paths)
and then loads the real app module so Panel picks up the servable objects.

Usage:
    panel serve demo/app.py --basic-auth demo/credentials.json ...
"""

import os
import sys

# Ensure project root is importable
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Ensure demo dir is importable
_demo_dir = os.path.dirname(os.path.abspath(__file__))
if _demo_dir not in sys.path:
    sys.path.insert(0, _demo_dir)

# Apply demo overrides BEFORE the app module runs
from config_overrides import apply
apply()

# Now import the real app -- Panel discovers its servable objects
from visualize_accelerometry.app import *  # noqa: F401, F403
'''
    with open(path, "w") as f:
        f.write(content)
    print(f"  wrote {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    use_synthetic = "--synthetic" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("-")]

    readings_dir = args[0] if args else os.path.join(repo_root, "demo", "data", "readings")
    demo_dir = os.path.join(repo_root, "demo")
    output_dir = os.path.join(demo_dir, "data", "output")

    os.makedirs(readings_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    # --- Generate accelerometry HDF5 files ---
    pools = None
    source_hz = TARGET_HZ  # default; overridden if real data loaded
    if not use_synthetic:
        print("Downloading real accelerometry data from UCI...")
        src_df = download_dataset()
        if src_df is not None:
            pools = _extract_activity_pools(src_df)
            if any(len(v) == 0 for v in pools.values()):
                print("  WARNING: Some activity pools are empty, falling back to synthetic")
                pools = None
            else:
                source_hz = _estimate_hz(src_df)
                print(f"  Estimated source sampling rate: {source_hz} Hz")
                for label, arr in pools.items():
                    print(f"  Pool '{label}': {len(arr):,} samples ({len(arr)/source_hz:.0f}s)")

    if pools is not None:
        print("\nGenerating HDF5 files from real accelerometer data...")
        rng = np.random.default_rng(42)
        for spec in FILE_SPECS:
            generate_file_real(spec, pools, source_hz, readings_dir, rng)
    else:
        if not use_synthetic:
            print("\nFalling back to synthetic data generation...")
        else:
            print("Generating synthetic accelerometry data...")
        for spec in FILE_SPECS:
            generate_file_synthetic(spec, readings_dir)

    # --- Generate example annotations ---
    print("\nGenerating example annotations...")
    generate_annotations(output_dir)

    # --- Generate demo configuration files ---
    # Only write config files if they don't already exist, so that manual
    # edits to demo/app.py or demo/config_overrides.py are preserved.
    print("\nCreating demo configuration files...")
    create_demo_credentials(demo_dir)
    if not os.path.exists(os.path.join(demo_dir, "config_overrides.py")):
        create_config_overrides(demo_dir)
    else:
        print(f"  skipped {os.path.join(demo_dir, 'config_overrides.py')} (already exists)")
    if not os.path.exists(os.path.join(demo_dir, "app.py")):
        create_demo_entrypoint(demo_dir)
    else:
        print(f"  skipped {os.path.join(demo_dir, 'app.py')} (already exists)")

    print("\nDone. To run the demo locally:")
    print("  panel serve demo/app.py \\")
    print("    --basic-auth demo/credentials.json \\")
    print('    --cookie-secret $(python -c "import secrets; print(secrets.token_hex(32))") \\')
    print("    --allow-websocket-origin localhost:5006")


if __name__ == "__main__":
    main()
