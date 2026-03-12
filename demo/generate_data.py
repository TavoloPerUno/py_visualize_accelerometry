#!/usr/bin/env python3
"""Generate synthetic accelerometry HDF5 files for the demo deployment.

Creates small but realistic-looking data that exercises every feature of the
annotation UI without requiring access to real participant recordings.

Usage:
    python demo/generate_data.py            # writes to demo/data/readings/
    python demo/generate_data.py /tmp/out   # writes to custom directory
"""

import json
import os
import sys

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SAMPLING_HZ = 85
DURATION_SECONDS = 600  # 10 minutes per file — keeps HDF5 under 10 MB (HF limit)
N_ROWS = SAMPLING_HZ * DURATION_SECONDS  # ~51 000

# Two synthetic files that follow the real naming convention:
# <subject_id>-<YYYYMMDDHHmmss>.h5
FILE_SPECS = [
    {
        "filename": "900001-20230315093000.h5",
        "start": pd.Timestamp("2023-03-15 09:30:00"),
    },
    {
        "filename": "900002-20230316140000.h5",
        "start": pd.Timestamp("2023-03-16 14:00:00"),
    },
]

# Activity patterns with approximate durations (seconds) and repeats.
# Each pattern modulates x/y/z differently so the waveform is visually
# distinguishable in the annotation UI.
ACTIVITIES = [
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
# Total: sums to ~600 s (10 min); remainder filled with sitting.


def _generate_signal(n_samples, freq, amplitude, noise_std=0.03):
    """Sine wave + Gaussian noise, mimicking a single accelerometry axis."""
    t = np.linspace(0, n_samples / SAMPLING_HZ, n_samples, endpoint=False)
    signal = amplitude * np.sin(2 * np.pi * freq * t)
    signal += np.random.normal(0, noise_std, n_samples)
    return signal


def generate_file(spec, output_dir):
    """Build one synthetic HDF5 file from the activity schedule."""
    rng = np.random.default_rng(42)

    segments = []
    for label, dur_s, xf, yf, zf, xa, ya, za in ACTIVITIES:
        n = dur_s * SAMPLING_HZ
        segments.append(
            {
                "x": _generate_signal(n, xf, xa),
                "y": _generate_signal(n, yf, ya),
                "z": _generate_signal(n, zf, za),
            }
        )

    # Fill remaining time with sitting
    used = sum(dur_s for _, dur_s, *_ in ACTIVITIES)
    remaining = max(0, DURATION_SECONDS - used)
    if remaining > 0:
        n = remaining * SAMPLING_HZ
        segments.append(
            {
                "x": _generate_signal(n, 0.1, 0.02),
                "y": _generate_signal(n, 0.1, 0.02),
                "z": _generate_signal(n, 0.05, 1.00),
            }
        )

    x = np.concatenate([s["x"] for s in segments]).astype(np.float64)
    y = np.concatenate([s["y"] for s in segments]).astype(np.float64)
    z = np.concatenate([s["z"] for s in segments]).astype(np.float64)
    total = len(x)

    # Auxiliary sensor channels
    light = rng.uniform(100, 800, total).astype(np.float64)
    button = np.zeros(total, dtype=np.float64)
    temperature = (25.0 + rng.normal(0, 0.5, total)).astype(np.float64)

    timestamps = pd.date_range(
        start=spec["start"], periods=total, freq=pd.Timedelta(seconds=1 / SAMPLING_HZ)
    )

    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "x": x,
            "y": y,
            "z": z,
            "light": light,
            "button": button,
            "temperature": temperature,
        }
    )

    filepath = os.path.join(output_dir, spec["filename"])
    df.to_hdf(
        filepath,
        key="readings",
        format="table",
        data_columns=["timestamp"],
        complevel=9,
        complib="zlib",
    )
    print(f"  wrote {filepath}  ({len(df):,} rows, {os.path.getsize(filepath) / 1e6:.1f} MB)")


def create_demo_credentials(demo_dir):
    """Write demo/credentials.json with demo users.

    Panel basic-auth compares passwords as plain strings, so
    credentials are stored in plain text.
    """
    creds = {
        "demo_admin": "demo",
        "demo_user": "demo",
    }
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
(demo/app_demo.py) imports this module to patch config values
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
    """Write demo/app_demo.py -- the Panel entrypoint for demo mode."""
    path = os.path.join(demo_dir, "app_demo.py")
    content = '''\
"""
Demo-mode entrypoint for panel serve.

This script applies demo configuration overrides (demo users, demo data paths)
and then loads the real app module so Panel picks up the servable objects.

Usage:
    panel serve demo/app_demo.py --basic-auth demo/credentials.json ...
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


def main():
    # Determine output directory
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if len(sys.argv) > 1:
        readings_dir = sys.argv[1]
    else:
        readings_dir = os.path.join(repo_root, "demo", "data", "readings")

    demo_dir = os.path.join(repo_root, "demo")

    os.makedirs(readings_dir, exist_ok=True)
    os.makedirs(os.path.join(demo_dir, "data", "output"), exist_ok=True)

    print("Generating synthetic accelerometry data...")
    for spec in FILE_SPECS:
        generate_file(spec, readings_dir)

    print("\nCreating demo configuration files...")
    create_demo_credentials(demo_dir)
    create_config_overrides(demo_dir)
    create_demo_entrypoint(demo_dir)

    print("\nDone. To run the demo locally:")
    print(f"  panel serve demo/app_demo.py \\")
    print(f"    --basic-auth demo/credentials.json \\")
    print(f'    --cookie-secret $(python -c "import secrets; print(secrets.token_hex(32))") \\')
    print(f"    --allow-websocket-origin localhost:5006")


if __name__ == "__main__":
    main()
