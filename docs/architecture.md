# Architecture

## Overview

The app is built on [Panel](https://panel.holoviz.org/) (which wraps Bokeh server) with separate modules for state, UI callbacks, plotting, and data I/O.

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

Annotation overlays use persistent `ColumnDataSource` objects created once and shared between `AppState` and the Bokeh figure. Updating `.data` on a source re-renders just the overlay quads, not the whole plot. Annotation changes appear immediately.

### LTTB downsampling

Raw files can hold 500K+ points per axis. Sending them all to the browser would be slow. The plotting module uses Largest Triangle Three Buckets (LTTB) to reduce each axis to ~10,000 points for the main plot and ~2,000 for the range selector. LTTB keeps the shape of the signal: peaks, valleys, and rapid transitions stay; flat regions compress. The `lttbc` C extension makes this fast; without it, the code falls back to uniform strided sampling.

### Box-select via invisible scatter points

Bokeh's `BoxSelectTool` selects data indices from point-based glyphs (scatter, circle) but not from line glyphs. To enable time-range selection on signal lines, invisible scatter points (size=0, alpha=0) are rendered on top of the lines. The `selected.on_change("indices", ...)` callback converts selected indices to timestamps.

### HDF5 server-side filtering

Data loading uses PyTables `where` clauses (`pd.read_hdf(..., where="timestamp >= ts_start & timestamp <= ts_end")`) so only the visible time window leaves disk. On a 123 MB file, that's 14 ms instead of 1.38 s. Fixed-format HDF5 files fall back to in-memory filtering.

### Fast-path navigation

Previous/Next patches the existing `ColumnDataSource.data` and adjusts axis ranges in place instead of rebuilding the figure. Bokeh ships this as a small websocket data-patch. Annotation quad bounds (`top`/`bottom`) update to match the new y-range. Full figure rebuild only happens on the first load.

### Explicit y-range

The plot uses `Range1d`, not `DataRange1d`, for the y-axis. `DataRange1d` would auto-expand to include the annotation quad overlays, which would squash the signal to a thin line. The y-range is computed from the signal with 5% padding.

### Canvas rendering, not WebGL

The app uses the default canvas backend instead of WebGL because:
- WebGL doesn't support hatch patterns (used for segment/scoring/review overlays)
- WebGL has rendering glitches when updating CDS data in place
- With LTTB, canvas is fast enough at 10,000 points per axis

## Data flow

### Network latency indicator

The header includes a network latency indicator that pings `/favicon.ico` every 10 seconds and displays the round-trip time. Because Panel's `pn.pane.HTML` renders inside Shadow DOM using `innerHTML` (which doesn't execute `<script>` tags), the ping JavaScript is injected via a Bokeh `Div` model with a `CustomJS` callback on the `DocumentReady` event.

### Signal loading
```
File picker change
  → CallbackManager.plot_new_file()
    → AppState.load_file_data()
      → data_loading.get_filedata() — reads HDF5 with time-window query
    → CallbackManager.update_plot()
      → Fast path: plotting.update_plot_data() — update CDS + ranges in place
      → Full rebuild: plotting.make_plot() — LTTB downsample + create Bokeh figures
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
