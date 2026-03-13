# Architecture

## Overview

The application is built on [Panel](https://panel.holoviz.org/) (which wraps [Bokeh](https://bokeh.org/) server) and follows a clear separation between state management, UI callbacks, plotting, and data I/O.

```
app.py ──────── Layout, widget creation, callback wiring
    │
    ├── state.py ──────── Per-session state (AppState class)
    │
    ├── callbacks.py ──── Event handlers (CallbackManager class)
    │
    ├── plotting.py ───── Bokeh figure creation with LTTB downsampling
    │
    ├── data_loading.py ─ HDF5 reading, annotation Excel I/O
    │
    └── config.py ─────── Constants, paths, color palettes, user lists
```

## Key design decisions

### Per-session state

Each browser session gets its own `AppState` instance. This avoids shared mutable state between users. The only shared state is the module-level user lists in `config.py`, which admins can modify at runtime.

### Persistent ColumnDataSources

Annotation overlays use persistent `ColumnDataSource` objects that are created once and shared between `AppState` and the Bokeh figure. Updating `.data` on these sources triggers Bokeh to re-render the overlay quads without rebuilding the entire plot. This is critical for responsiveness — annotation changes are near-instant.

### LTTB downsampling

Raw accelerometry files can contain 500K+ data points per axis. Sending all of them to the browser would be slow and unresponsive. The plotting module uses the **Largest Triangle Three Buckets** (LTTB) algorithm to reduce each axis to ~10,000 visually representative points for the main plot and ~2,000 for the range selector minimap. LTTB preserves the visual shape of the signal — peaks, valleys, and rapid transitions are retained while flat regions are compressed. If the `lttbc` C extension is not installed, it falls back to uniform strided sampling.

### Box-select via invisible scatter points

Bokeh's `BoxSelectTool` selects data indices from point-based glyphs (scatter, circle) but not from line glyphs. To enable time-range selection on signal lines, invisible scatter points (size=0, alpha=0) are rendered on top of the lines. The `selected.on_change("indices", ...)` callback converts selected indices to timestamps.

### Explicit y-range

The plot uses `Range1d` (not `DataRange1d`) for the y-axis. This is because `DataRange1d` auto-expands to include all renderers — including annotation quad overlays — which would squash the signal to a thin line. The y-range is computed from the actual signal data with 5% padding.

### Canvas rendering (not WebGL)

Despite having up to 10,000 points per axis, the app uses the default canvas backend instead of WebGL. This is because:
- WebGL doesn't support hatch patterns (used for segment/scoring/review overlays)
- WebGL has rendering glitches when updating CDS data in-place
- With LTTB downsampling, canvas performance is more than adequate

## Data flow

### Signal loading
```
File picker change
  → CallbackManager.plot_new_file()
    → AppState.load_file_data()
      → data_loading.get_filedata() — reads HDF5 with time-window query
    → CallbackManager._refresh_plot()
      → plotting.make_plot() — LTTB downsample + create Bokeh figures
```

### Annotation lifecycle
```
Box-select on plot
  → _on_selection_change() — converts indices to timestamps
    → state.selection_bounds = (start, end)
    → CallbackManager.update_selection() — enable/disable buttons

Click annotation button
  → CallbackManager.mark_annotation()
    → capture_new_annotation() — create DataFrame row
    → AppState.update_annotation_sources() — update overlay CDS

Click Export
  → CallbackManager.save()
    → data_loading.save_annotations() — write Excel, reload from disk
```
