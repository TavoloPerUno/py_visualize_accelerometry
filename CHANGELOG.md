# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.3.22] - 2026-03-14

### Changed
- perf: speed up data loading, add latency monitoring

## [3.3.21] - 2026-03-14

### Changed
- perf: speed up data loading and add latency monitoring

## [3.3.20] - 2026-03-14

### Fixed
- prevent SSH tunnel from closing immediately

## [3.3.19] - 2026-03-14

### Changed
- docs: add Zenodo DOI badge to README

## [3.3.18] - 2026-03-14

### Changed
- docs: regenerate SVGs with realistic signal characteristics

## [3.3.17] - 2026-03-14

### Fixed
- pin numpy<2 for Python 3.9 to fix PyTables compatibility

## [3.3.16] - 2026-03-14

### Changed
- docs: recreate signal SVGs with realistic accelerometry patterns

## [3.3.15] - 2026-03-14

### Fixed
- use in-memory timestamp filter instead of HDF5 where clause for cross-version compatibility

## [3.3.14] - 2026-03-14

### Changed
- docs: rewrite SVGs as static (no JS), make device-placement agnostic

## [3.3.13] - 2026-03-14

### Fixed
- use ISO timestamps in HDF5 queries, fix StringDtype test assertion

## [3.3.12] - 2026-03-14

### Changed
- docs: add signal pattern diagrams and step-by-step annotation walkthrough

## [3.3.11] - 2026-03-14

### Fixed
- handle SSH tunnel managed by ControlMaster, keep script alive

## [3.3.10] - 2026-03-14

### Fixed
- keep tunnel process alive with ControlMaster=no on tunnel connection

## [3.3.9] - 2026-03-14

### Fixed
- shorten SSH control socket path to avoid macOS length limit

## [3.3.8] - 2026-03-14

### Fixed
- use SSH ControlMaster so users only authenticate once

## [3.3.7] - 2026-03-14

### Changed
- docs: enhance Sphinx site with annotation guide, data format reference, and improved index
- docs: add segment/scoring/review flag context and chair stand workflow example

## [3.3.6] - 2026-03-14

### Changed
- docs: switch to Furo theme with UChicago maroon branding

## [3.3.5] - 2026-03-14

### Changed
- docs: add favicon, PyPI install instructions, fix Slurm job name

## [3.3.4] - 2026-03-14

### Fixed
- remove /en/ prefix from sitemap URLs

## [3.3.3] - 2026-03-13

### Changed
- Fix factual errors found during documentation proofreading

## [3.3.2] - 2026-03-12

### Changed
- docs: fix outdated URLs and demo data description

## [3.3.1] - 2026-03-12

### Fixed
- use late-bound ANNOTATOR_USERS and prevent config file overwrites

## [3.3.0] - 2026-03-12

### Added
- add test suite and CI, fix global RNG pollution and HDF5 last-row read

### Changed
- chore: gitignore JOSS manuscript files

## [3.2.1] - 2026-03-12

### Changed
- docs: add PyPI, license, demo, and docs badges to README

## [3.2.0] - 2026-03-12

### Added
- add PyPI packaging, MIT license, and citation metadata

## [3.1.8] - 2026-03-12

### Changed
- docs: crop whitespace from README hero image

## [3.1.7] - 2026-03-12

### Changed
- docs: update README hero image with regenerated UCI demo data

## [3.1.6] - 2026-03-12

### Changed
- docs: replace README hero image with high-res demo data screenshot

## [3.1.5] - 2026-03-12

### Fixed
- tighten bokeh/panel version pins to prevent blank page on HF Spaces

## [3.1.4] - 2026-03-12

### Fixed
- pin bokeh/panel versions and update README screenshot

## [3.1.3] - 2026-03-12

### Fixed
- use late-bound config paths to fix blank page in demo deployment

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
- docs: add Google Search Console verification file

### Fixed
- include Google verification file in html_extra_path

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
- Canvas rendering with LTTB downsampling for performance
- Responsive toolbar layout for different screen sizes
- Sphinx documentation with GitHub Pages CI
- Live demo hosted on Hugging Face Spaces with auto-deploy
- Synthetic data generator for demo deployment
- Auto-version workflow for conventional commit-based releases
- Release workflow with CHANGELOG-based notes

[2.0.0]: https://github.com/TavoloPerUno/py_visualize_accelerometry/releases/tag/v2.0.0

[2.1.0]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v2.0.0...v2.1.0

[2.1.1]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v2.1.0...v2.1.1

[2.2.0]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v2.1.1...v2.2.0

[2.2.1]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v2.2.0...v2.2.1

[3.1.0]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v3.0.0...v3.1.0

[3.0.0]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v2.2.1...v3.0.0

[3.1.1]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v3.1.0...v3.1.1

[3.1.2]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v3.1.1...v3.1.2

[3.1.3]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v3.1.2...v3.1.3

[3.1.4]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v3.1.3...v3.1.4

[3.1.5]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v3.1.4...v3.1.5

[3.1.6]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v3.1.5...v3.1.6

[3.1.7]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v3.1.6...v3.1.7

[3.1.8]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v3.1.7...v3.1.8

[3.2.0]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v3.1.8...v3.2.0

[3.2.1]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v3.2.0...v3.2.1

[3.3.0]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v3.2.1...v3.3.0

[3.3.1]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v3.3.0...v3.3.1

[3.3.2]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v3.3.1...v3.3.2

[3.3.3]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v3.3.2...v3.3.3

[3.3.4]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v3.3.3...v3.3.4

[3.3.5]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v3.3.4...v3.3.5

[3.3.6]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v3.3.5...v3.3.6

[3.3.7]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v3.3.6...v3.3.7

[3.3.8]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v3.3.7...v3.3.8

[3.3.9]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v3.3.8...v3.3.9

[3.3.10]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v3.3.9...v3.3.10

[3.3.11]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v3.3.10...v3.3.11

[3.3.12]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v3.3.11...v3.3.12

[3.3.13]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v3.3.12...v3.3.13

[3.3.14]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v3.3.13...v3.3.14

[3.3.15]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v3.3.14...v3.3.15

[3.3.16]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v3.3.15...v3.3.16

[3.3.17]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v3.3.16...v3.3.17

[3.3.18]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v3.3.17...v3.3.18

[3.3.19]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v3.3.18...v3.3.19

[3.3.20]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v3.3.19...v3.3.20

[3.3.21]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v3.3.20...v3.3.21

[3.3.22]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v3.3.21...v3.3.22
