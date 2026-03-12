# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.1.2] - 2026-03-12

### Changed
- docs: add app screenshots to README

## [3.1.1] - 2026-03-12

### Fixed
- rename app_demo.py to app.py so Panel serves at /app

## [3.1.0] - 2026-03-12

### Added
- Demo now uses real accelerometer data from the UCI Accelerometer & Gyro Mobile Phone Dataset (CC BY 4.0)
- Pre-populated example annotations for both demo users showcasing all activity types, flags, and inter-annotator variability
- Port auto-increment fallback in `connect.sh` when preferred local port is unavailable
- `--synthetic` flag for `demo/generate_data.py` to force synthetic data generation

### Changed
- Renamed `scripts/` to `devops/` for dev/CI tooling
- Moved `generate_demo_data.py` into `demo/generate_data.py` (co-located with demo deployment)
- Moved startup guides from repo root into `docs/` with kebab-case filenames
- Updated all downstream references (Dockerfile, CI workflow, README, docs)

### Removed
- Tracked `hpc_utils/dask.log` (now gitignored)

## [3.0.0] - 2026-03-11

### Added
- Self-service `connect.sh` — auto-detects running jobs, submits new ones if needed, creates SSH tunnel, and opens browser
- Stale SSH tunnel detection and cleanup on reconnect
- Proper HPC environment setup in `start_server.sh` (module loads, conda activation)
- Persistent Slurm jobs using `nohup` + `sleep.py`
- Organized log output in `hpc_utils/logs/`

### Changed
- Consolidated `slurm/` into `hpc_utils/` — single folder for all HPC deployment scripts
- App URL changed from `/visualize_accelerometry/app` to `/app`
- Updated all documentation to reflect the new self-service workflow

### Removed
- Per-user job submission model (replaced by shared server with auto-detection)

## [2.2.1] - 2026-03-11

### Fixed
- correct REMOTE_DIR path

## [2.2.0] - 2026-03-11

### Added
- self-service connect script with auto job submission and SSH_USER config

## [2.1.1] - 2026-03-11

### Changed
- docs: add shared app start-up guide
- docs: add Slurm shared server deployment guide

## [2.1.2] - 2026-03-11

### Fixed
- include Google verification file in html_extra_path

## [2.1.1] - 2026-03-11

### Changed
- docs: add Google Search Console verification file

## [2.1.0] - 2026-03-11

### Added
- add SEO improvements — sitemap, meta tags, Open Graph, robots.txt

## [2.0.0] - 2026-03-11

### Added
- Panel-based web app with OAuth and BasicAuth support
- Tri-axial (x, y, z) accelerometry signal plotting with range selector
- LTTB downsampling for smooth rendering of large datasets
- Box-select annotation tool for labeling activity segments
- Support for Chair Stand, TUG, 3-Meter Walk, and 6-Minute Walk tests
- Segment, scoring, and review flag overlays with hatch patterns
- Free-text notes on annotations
- Multi-user file assignment with even splitting across annotators
- Auto-save annotations to per-user Excel files
- WebGL rendering for performance
- Responsive toolbar layout for different screen sizes
- Sphinx documentation with GitHub Pages CI
- Live demo hosted on Hugging Face Spaces with auto-deploy
- Synthetic data generator for demo deployment
- Auto-version workflow for conventional commit-based releases
- Release workflow with CHANGELOG-based notes

[2.0.0]: https://github.com/TavoloPerUno/py_visualize_accelerometry/releases/tag/v2.0.0

[2.1.0]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v2.0.0...v2.1.0

[2.1.1]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v2.1.0...v2.1.1

[2.1.2]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v2.1.1...v2.1.2

[2.1.1]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v2.1.0...v2.1.1

[2.2.0]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v2.1.1...v2.2.0

[2.2.1]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v2.2.0...v2.2.1

[3.1.0]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v3.0.0...v3.1.0

[3.0.0]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v2.2.1...v3.0.0

[3.1.1]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v3.1.0...v3.1.1

[3.1.2]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v3.1.1...v3.1.2
