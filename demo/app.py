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
