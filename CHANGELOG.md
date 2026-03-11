# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-03-10

### Changed
- Responsive toolbar layout for different screen sizes
- Header icons redesigned for clarity
- Logo redesign

### Fixed
- Documentation updated to reflect new UI changes

## [1.0.0] - 2026-03-09

### Added
- Panel app with OAuth and BasicAuth support
- LTTB downsampling for smooth rendering of large datasets
- README, Sphinx documentation, and GitHub Pages CI
- UI screenshots and academic references for physical tests
- FastListTemplate layout

### Changed
- Migrated from Bokeh standalone app to Panel framework
- Updated user list and layout

### Removed
- Obsolete Heroku deployment files
- Outdated conda-environment.yml
- Outdated App start-up.md

### Fixed
- SLURM log filenames and project path
- Hardcoded username in SLURM script paths

## [0.1.0] - 2025-12-01

### Added
- Bokeh-based accelerometry visualization app
- Tri-axial (x, y, z) signal plotting with range selector
- Box-select annotation tool for labeling activity segments
- Support for Chair Stand, TUG, 3-Meter Walk, and 6-Minute Walk tests
- Segment, scoring, and review flag overlays with hatch patterns
- Free-text notes on annotations
- Multi-user file assignment with even splitting across annotators
- Auto-save annotations to per-user Excel files
- WebGL rendering for performance

### Fixed
- File loading for small files
- Old annotation filename reads causing annotations to disappear
- Summary end timestamp calculation
- Next window scrolling behavior
- Selected indices error

[1.1.0]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/TavoloPerUno/py_visualize_accelerometry/compare/v0.1.0...v1.0.0
[0.1.0]: https://github.com/TavoloPerUno/py_visualize_accelerometry/releases/tag/v0.1.0
