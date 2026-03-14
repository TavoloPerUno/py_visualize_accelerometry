"""
Plotting module — native Bokeh figures with LTTB downsampling.

Creates a main signal plot (with annotation overlays and box-select)
and a range selector (minimap) for navigating large time series.
LTTB downsampling keeps the browser responsive by limiting the number
of points sent over the websocket while preserving visual fidelity.
"""

import numpy as np
from bokeh.models import (
    BoxSelectTool, ColumnDataSource, DatetimeTickFormatter,
    Range1d, RangeTool,
)
from bokeh.plotting import figure

from .config import ARTIFACT_COLORS, LST_COLORS, UCHICAGO_MAROON

# Maximum points to send to the browser per signal axis.
# 10000 provides high visual fidelity while remaining responsive
# with the canvas backend (no WebGL).
MAX_POINTS = 10000


def _downsample(timestamps, values, n_out):
    """Downsample a time series using LTTB (Largest Triangle Three Buckets).

    LTTB selects representative points that preserve the visual shape
    of the signal.  Falls back to uniform strided sampling if the
    ``lttbc`` C extension is not installed.

    Parameters
    ----------
    timestamps : ndarray
        Datetime64 array of timestamps.
    values : ndarray
        Signal values corresponding to *timestamps*.
    n_out : int
        Target number of output points.

    Returns
    -------
    tuple of (ndarray, ndarray)
        Downsampled ``(timestamps, values)``.
    """
    if len(timestamps) <= n_out:
        return timestamps, values
    try:
        import lttbc
        # lttbc operates on float64 arrays
        ts_float = timestamps.astype(np.float64)
        vals_float = values.astype(np.float64)
        ds_ts, ds_vals = lttbc.downsample(ts_float, vals_float, n_out)
        return ds_ts.astype(timestamps.dtype), ds_vals
    except Exception:
        # Graceful fallback: take every Nth sample
        step = max(1, len(timestamps) // n_out)
        return timestamps[::step], values[::step]


def make_plot(pdf, annotation_cds):
    """Create the main signal plot and range selector.

    Parameters
    ----------
    pdf : DataFrame or None
        Signal data with columns ``timestamp``, ``x``, ``y``, ``z``.
        If None or empty, returns empty placeholder plots.
    annotation_cds : dict[str, ColumnDataSource]
        Persistent Bokeh ColumnDataSources keyed by annotation type
        (``"chair_stand"``, ``"segment"``, etc.).  Their ``.data`` is
        updated externally; the plot just references them so overlays
        refresh without rebuilding the figure.

    Returns
    -------
    tuple of (Panel.pane.Bokeh, Panel.pane.Bokeh, Figure, ColumnDataSource, ColumnDataSource)
        ``(main_pane, range_pane, main_fig, signal_cds, range_source)``
        where ``signal_cds`` is the downsampled signal data source and
        ``range_source`` is the minimap CDS (both needed for fast
        in-place data updates on navigation).
    """
    import panel as pn

    if pdf is None or len(pdf) == 0:
        empty_fig1 = figure(height=300, sizing_mode="stretch_width")
        empty_fig2 = figure(height=130, sizing_mode="stretch_width")
        empty_cds = ColumnDataSource(data=dict(timestamp=[], x=[], y=[], z=[]))
        return (
            pn.pane.Bokeh(empty_fig1, sizing_mode="stretch_width"),
            pn.pane.Bokeh(empty_fig2, sizing_mode="stretch_width"),
            empty_fig1,
            empty_cds,
            empty_cds,
        )

    ts_raw = pdf["timestamp"].values

    # --- Downsample each axis independently via LTTB ---
    # Each axis may pick slightly different representative timestamps,
    # but we reuse the first axis's timestamps for all three.  This is
    # a minor approximation that keeps the code simple without visible
    # impact on the plot.
    ds_data = {"timestamp": None}
    for col in ["x", "y", "z"]:
        ds_ts, ds_vals = _downsample(ts_raw, pdf[col].values, MAX_POINTS)
        if ds_data["timestamp"] is None:
            ds_data["timestamp"] = ds_ts
        ds_data[col] = ds_vals

    colsource = ColumnDataSource(data=ds_data)

    full_start = ts_raw[0]
    # Show ~10% of the file initially so the user sees detail
    initial_end_idx = min(len(ts_raw) - 1, int(len(ts_raw) * 0.1))
    initial_end = ts_raw[initial_end_idx]

    # Explicit y_range computed from signal data.  Using Range1d (not
    # DataRange1d) is critical because DataRange1d would auto-expand to
    # include annotation quad bounds, squashing the signal to a thin line.
    y_min = float(np.nanmin([np.nanmin(ds_data["x"]), np.nanmin(ds_data["y"]), np.nanmin(ds_data["z"])]))
    y_max = float(np.nanmax([np.nanmax(ds_data["x"]), np.nanmax(ds_data["y"]), np.nanmax(ds_data["z"])]))
    y_pad = max((y_max - y_min) * 0.05, 0.1)
    y_range = Range1d(start=y_min - y_pad, end=y_max + y_pad)

    # --- Main signal plot ---
    main_fig = figure(
        height=300,
        x_axis_type="datetime",
        x_axis_location="above",
        background_fill_color="#e8e8e8",
        x_range=Range1d(start=full_start, end=initial_end),
        y_range=y_range,
        sizing_mode="stretch_width",
        toolbar_location=None,
    )
    main_fig.yaxis.visible = False

    for color, col in zip(LST_COLORS, ["x", "y", "z"]):
        main_fig.line(
            "timestamp", col, color=color, source=colsource,
            alpha=0.95, line_width=1.5,
            # Dim unselected data so the box-selected region stands out
            nonselection_alpha=0.2, selection_alpha=1,
        )
        # Invisible scatter points on top of lines so that BoxSelectTool
        # can select data indices.  Line glyphs alone don't support
        # index-based hit testing.
        main_fig.scatter(
            "timestamp", col, color=None, source=colsource,
            size=0, alpha=0, nonselection_alpha=0, selection_alpha=0,
        )

    main_fig.xaxis.formatter = DatetimeTickFormatter(
        days="%Y/%m/%d",
        months="%Y/%m/%d %H:%M",
        hours="%Y/%m/%d %H:%M",
        minutes="%H:%M",
        seconds="%H:%M:%S",
        milliseconds="%Ss:%3Nms",
    )

    # Width-only box select for time-range annotation
    box_select = BoxSelectTool(dimensions="width")
    main_fig.add_tools(box_select)
    main_fig.toolbar.active_drag = box_select

    # --- Annotation overlay quads ---
    # Quads span the full y_range so they are visible behind the signal.
    q_top = y_max + y_pad
    q_bot = y_min - y_pad

    # Activity type overlays (semi-transparent colored fills)
    for key, color in ARTIFACT_COLORS.items():
        main_fig.quad(
            left="start_time", right="end_time", top=q_top, bottom=q_bot,
            fill_color=color, fill_alpha=0.2, line_alpha=0,
            source=annotation_cds[key], level="overlay",
            name="annotation_quad",
        )

    # Flag overlays (hatch patterns with no fill, matching the original app)
    flag_hatches = {
        "segment": "cross",
        "scoring": "dot",
        "review": "spiral",
    }
    for key, hatch in flag_hatches.items():
        main_fig.quad(
            left="start_time", right="end_time", top=q_top, bottom=q_bot,
            fill_color=None, fill_alpha=0, line_alpha=0,
            hatch_pattern=hatch, hatch_color="black",
            hatch_weight=0.5, hatch_alpha=0.1,
            source=annotation_cds[key], level="overlay",
            name="annotation_quad",
        )

    # --- Range selector (minimap) ---
    # Subsample from the already-downsampled main data (10K → 2K)
    # instead of re-running LTTB on the full raw signal.
    n_main = len(ds_data["timestamp"])
    step = max(1, n_main // 2000)
    range_data = {
        "timestamp": ds_data["timestamp"][::step],
        "x": ds_data["x"][::step],
        "y": ds_data["y"][::step],
        "z": ds_data["z"][::step],
    }
    range_source = ColumnDataSource(data=range_data)

    range_fig = figure(
        height=130,
        y_range=main_fig.y_range,
        x_axis_type="datetime",
        y_axis_type=None,
        tools="",
        toolbar_location=None,
        background_fill_color="#e8e8e8",
        sizing_mode="stretch_width",
    )

    for color, col in zip(LST_COLORS, ["x", "y", "z"]):
        range_fig.line(
            "timestamp", col, color=color, source=range_source,
            alpha=0.8, line_width=1.2,
        )

    range_fig.xaxis.formatter = DatetimeTickFormatter(
        days="%m/%d %H:%M",
        months="%m/%d %H:%M",
        hours="%m/%d %H:%M",
        minutes="%m/%d %H:%M",
        seconds="%m/%d %H:%M:%S",
    )

    # RangeTool links the minimap's draggable overlay to main_fig.x_range
    range_tool = RangeTool(x_range=main_fig.x_range)
    range_tool.overlay.fill_color = UCHICAGO_MAROON
    range_tool.overlay.fill_alpha = 0.15
    range_fig.add_tools(range_tool)
    range_fig.toolbar.active_multi = "auto"

    main_pane = pn.pane.Bokeh(main_fig, sizing_mode="stretch_width")
    range_pane = pn.pane.Bokeh(range_fig, sizing_mode="stretch_width")

    return main_pane, range_pane, main_fig, colsource, range_source


def update_plot_data(pdf, signal_cds, main_fig, range_source=None):
    """Update an existing plot's data without rebuilding figures.

    Replaces the signal CDS data, adjusts x/y ranges, and optionally
    updates the range selector CDS.  Much faster than ``make_plot``
    because Bokeh sends only a data-patch over the websocket instead
    of tearing down and reconstructing the entire document subtree.

    Parameters
    ----------
    pdf : DataFrame
        New signal data with ``timestamp``, ``x``, ``y``, ``z``.
    signal_cds : ColumnDataSource
        The main signal CDS to update (returned by ``make_plot``).
    main_fig : Figure
        The main plot figure (for x_range / y_range adjustment).
    range_source : ColumnDataSource or None
        The range selector CDS.  If None, the minimap is not updated.

    Returns
    -------
    bool
        True if updated successfully, False if a full rebuild is needed.
    """
    if pdf is None or len(pdf) == 0:
        return False

    ts_raw = pdf["timestamp"].values

    # Downsample
    ds_data = {"timestamp": None}
    for col in ["x", "y", "z"]:
        ds_ts, ds_vals = _downsample(ts_raw, pdf[col].values, MAX_POINTS)
        if ds_data["timestamp"] is None:
            ds_data["timestamp"] = ds_ts
        ds_data[col] = ds_vals

    # Update signal CDS in one shot (triggers a single websocket push)
    signal_cds.data = ds_data

    # Adjust y_range to fit new data
    y_min = float(np.nanmin([np.nanmin(ds_data["x"]), np.nanmin(ds_data["y"]), np.nanmin(ds_data["z"])]))
    y_max = float(np.nanmax([np.nanmax(ds_data["x"]), np.nanmax(ds_data["y"]), np.nanmax(ds_data["z"])]))
    y_pad = max((y_max - y_min) * 0.05, 0.1)
    q_top = y_max + y_pad
    q_bot = y_min - y_pad
    main_fig.y_range.start = q_bot
    main_fig.y_range.end = q_top

    # Update annotation quad renderers to match new y_range.
    # Annotation quads are tagged with name="annotation_quad" at creation.
    for renderer in main_fig.renderers:
        if getattr(renderer, "name", None) == "annotation_quad":
            renderer.glyph.top = q_top
            renderer.glyph.bottom = q_bot

    # Reset x_range to show ~10% of the file initially (matches make_plot)
    main_fig.x_range.start = ts_raw[0]
    initial_end_idx = min(len(ts_raw) - 1, int(len(ts_raw) * 0.1))
    main_fig.x_range.end = ts_raw[initial_end_idx]

    # Update range selector if provided
    if range_source is not None:
        n_main = len(ds_data["timestamp"])
        step = max(1, n_main // 2000)
        range_source.data = {
            "timestamp": ds_data["timestamp"][::step],
            "x": ds_data["x"][::step],
            "y": ds_data["y"][::step],
            "z": ds_data["z"][::step],
        }

    return True
