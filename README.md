# Accelerometry Annotation Tool

A web-based application for visualizing and annotating wrist-worn accelerometry data from physical performance assessments. Built with [Panel](https://panel.holoviz.org/) and [Bokeh](https://bokeh.org/), it enables research teams to collaboratively label activity segments in large time-series recordings.

## Live Demo

A publicly accessible demo is hosted on Hugging Face Spaces:

**[Launch Demo](https://tavoloperuno-accelerometry-viewer-demo.hf.space/)**

| Username | Password | Role |
|---|---|---|
| `demo_admin` | `demo` | Admin (can manage users, impersonate) |
| `demo_user` | `demo` | Annotator |

> **Note:** The demo uses synthetic accelerometry data generated from sine waves
> and noise. It does not contain real participant recordings. File sizes are
> small (~1 hour at 85 Hz) to keep the free deployment responsive.

## Shared Server Deployment (HPC / Slurm)

For HPC environments, you can run a single shared instance via Slurm that all team members connect to through SSH tunneling.

**Connect** (each user — submits job automatically if not running):
```bash
bash hpc_utils/connect.sh
```

**Stop the server**:
```bash
bash hpc_utils/stop_server.sh
```

## What it does

Researchers collect tri-axial accelerometry signals (x, y, z) during standardized physical performance tests. This tool lets annotators visually inspect those signals and mark the time boundaries of each test:

- **Chair Stand Test** — Measures lower-extremity strength by timing repeated sit-to-stand cycles from a standard chair. A key indicator of fall risk and functional independence in older adults.
- **Timed Up and Go (TUG)** — Assesses functional mobility: the participant rises from a chair, walks 3 meters, turns, walks back, and sits down. Taking 12+ seconds indicates increased fall risk (CDC STEADI).
- **3-Meter Walk Test** — Measures gait speed over a short distance as a proxy for mobility and physical function. Gait speed is widely regarded as "the sixth vital sign" for predicting disability and mortality.
- **6-Minute Walk Test** — A submaximal endurance test where the participant walks as far as possible in 6 minutes. Used to evaluate aerobic capacity in cardiac and pulmonary research.

## Features

- **LTTB downsampling** — Renders 500K+ data points smoothly by reducing to ~5,000 visually representative points using the Largest Triangle Three Buckets algorithm
- **Range selector** — Minimap for navigating long recordings without losing context
- **Box-select annotation** — Select a time range and label it with one click
- **Segment, scoring, and review flags** — Mark annotations for segmentation, scoring, or review with distinct hatch-pattern overlays
- **Notes** — Attach free-text notes to any annotation
- **Multi-user collaboration** — Each annotator sees their own file assignments; admins can impersonate users and manage accounts
- **Authentication** — Built-in basic auth (or OAuth for production deployments)
- **Auto-save to Excel** — Per-user annotation files for easy downstream analysis

## Installation

### Prerequisites

- Python 3.9+
- Conda (recommended) or pip

### Setup

```bash
# Clone the repository
git clone git@github.com:TavoloPerUno/py_visualize_accelerometry.git
cd py_visualize_accelerometry

# Create and activate conda environment
conda create -n panel_app python=3.12
conda activate panel_app

# Install dependencies
pip install -r requirements.txt
```

### Data setup

Place HDF5 accelerometry files (`.h5`) in:
```
visualize_accelerometry/data/readings/
```

Each file should contain a `readings` table with columns: `timestamp`, `x`, `y`, `z`.

### Credentials

Create a `credentials.json` file in the project root:
```json
{
    "username1": "password1",
    "username2": "password2"
}
```

See `credentials.json.example` for reference.

## Running the app

### Local development

```bash
panel serve visualize_accelerometry/app.py \
    --port 5601 \
    --basic-auth credentials.json \
    --cookie-secret $(python -c "import secrets; print(secrets.token_hex(32))") \
    --allow-websocket-origin localhost:5601 \
    --basic-login-template visualize_accelerometry/templates/login.html
```

Then open http://localhost:5601/app in your browser.

### HPC (SLURM)

See [Shared server startup](docs/shared-server-startup.md) for the self-service shared server workflow, or [Slurm deployment guide](docs/slurm-deployment.md) for the full deployment guide.

## Project structure

```
py_visualize_accelerometry/
├── visualize_accelerometry/
│   ├── app.py              # Main Panel application and layout
│   ├── callbacks.py         # UI event handlers and annotation logic
│   ├── config.py            # Colors, paths, user lists, constants
│   ├── data_loading.py      # HDF5 I/O, annotation file management
│   ├── plotting.py          # Bokeh plots with LTTB downsampling
│   ├── state.py             # Per-session state management
│   ├── templates/           # Login/logout HTML templates
│   ├── static/              # Favicon, logo
│   └── data/
│       ├── readings/        # HDF5 accelerometry files
│       └── output/          # Per-user annotation Excel files
├── hpc_utils/               # HPC deployment scripts (Slurm, SSH tunneling)
│   ├── connect.sh           # Self-service connect script
│   ├── start_server.sh      # Slurm job script
│   ├── stop_server.sh       # Stop running server
│   └── logs/                # Job and server logs
├── requirements.txt
└── credentials.json         # Auth credentials (not in repo)
```

## Documentation

Full documentation is available at [https://tavoloperuno.github.io/py_visualize_accelerometry/](https://tavoloperuno.github.io/py_visualize_accelerometry/).

To build documentation locally:

```bash
pip install sphinx sphinx-rtd-theme myst-parser
cd docs
make html
open _build/html/index.html
```

## Versioning and releases

This project uses [Semantic Versioning](https://semver.org/). The canonical version lives in `visualize_accelerometry/__init__.py` as `__version__`.

### Cutting a release

1. Update `__version__` in `visualize_accelerometry/__init__.py`
2. Update `CHANGELOG.md` with the new version's changes
3. Commit the changes:
   ```bash
   git add visualize_accelerometry/__init__.py CHANGELOG.md
   git commit -m "release: v<VERSION>"
   ```
4. Create and push the tag:
   ```bash
   git tag v<VERSION>
   git push git v<VERSION>
   ```
5. The `release.yml` GitHub Actions workflow will automatically create a GitHub Release with auto-generated notes from commits since the last tag.

## License

This project is developed by the [National Social Life, Health, and Aging Project (NSHAP)](https://www.norc.org/research/projects/national-social-life-health-and-aging-project.html) lab at the University of Chicago.
