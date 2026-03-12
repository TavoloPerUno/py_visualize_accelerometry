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
