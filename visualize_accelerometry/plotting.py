from bokeh.models import ColumnDataSource, DatetimeTickFormatter, RangeTool
from bokeh.plotting import figure
import bokeh.plotting as bp

from .config import LST_COLORS


def make_plot(srs, colsource, annotation_sources, title):
    """Create the main signal plot and range selector.

    Args:
        srs: array of timestamp values
        colsource: ColumnDataSource with signal data
        annotation_sources: dict with keys 'chair_stand', '3m_walk', '6min_walk',
            'tug', 'segment', 'scoring', 'review' mapping to ColumnDataSources
        title: plot title string

    Returns:
        (main_plot, range_selector, range_tool)
    """
    tools = "box_select"
    p = figure(
        height=300,
        tools=tools,
        toolbar_location="left",
        x_axis_type="datetime",
        x_axis_location="above",
        background_fill_color="#efefef",
        x_range=(srs[400], srs[min(3000, len(srs) - 1)]),
        title=title,
        sizing_mode="stretch_width",
        output_backend="webgl",
    )
    p.xaxis.axis_label = "Timestamp"

    lst_col = ["x", "y", "z"]
    for colr, leg in zip(LST_COLORS, lst_col):
        p.line(
            "timestamp", leg, color=colr, legend_label=leg,
            source=colsource, name="wave",
            nonselection_alpha=0.2, selection_alpha=1,
        )
        p.scatter(
            "timestamp", leg, color=None, legend_label=leg,
            source=colsource, name="wave",
        )

    p.xaxis.formatter = DatetimeTickFormatter(
        days=["%Y/%m/%d"],
        months=["%Y/%m/%d %H:%M"],
        hours=["%Y/%m/%d %H:%M"],
        minutes=["%H:%M"],
        seconds=["%H:%M:%S"],
        milliseconds=["%Ss:%3Nms"],
    )
    p.xaxis.minor_tick_line_color = "black"
    p.xgrid.minor_grid_line_alpha = 0.2

    # Range selector
    select = figure(
        title="Drag the middle and edges of the selection box to change the range above",
        height=130,
        y_range=p.y_range,
        x_axis_type="datetime",
        y_axis_type=None,
        tools="",
        toolbar_location=None,
        background_fill_color="#efefef",
        sizing_mode="stretch_width",
        output_backend="webgl",
    )
    select.ygrid.grid_line_color = None
    for colr, leg in zip(LST_COLORS, lst_col):
        select.line(
            "timestamp", leg, color=colr, source=colsource,
            nonselection_alpha=0.4, selection_alpha=1,
        )
    select.xaxis.formatter = DatetimeTickFormatter(
        days=["%m/%d %H:%M"],
        months=["%m/%d %H:%M"],
        hours=["%m/%d %H:%M"],
        minutes=["%m/%d %H:%M"],
        seconds=["%m/%d %H:%M:%S"],
        milliseconds=["%m/%d %H:%M:%Ss:%3Nms"],
    )

    # Annotation overlays
    artifact_configs = [
        ("chair_stand", "cyan", "chairstand"),
        ("3m_walk", "magenta", "3m_walk"),
        ("6min_walk", "green", "6min_walk"),
        ("tug", "yellow", "tug"),
    ]
    for key, color, label in artifact_configs:
        p.quad(
            left="start_time", right="end_time", top=4, bottom=-4,
            fill_color=color, fill_alpha=0.2,
            source=annotation_sources[key], legend_label=label,
        )

    # Hatched overlays for flags
    flag_configs = [
        ("segment", "cross", "segment"),
        ("scoring", "dot", "scoring"),
        ("review", "spiral", "review"),
    ]
    for key, pattern, label in flag_configs:
        p.quad(
            left="start_time", right="end_time", top=4, bottom=-4,
            fill_color=None, fill_alpha=0,
            source=annotation_sources[key], legend_label=label,
            hatch_pattern=pattern, hatch_color="black",
            hatch_weight=0.5, hatch_alpha=0.1,
        )

    p.legend.background_fill_alpha = 0.0
    p.legend.label_text_font_size = "7pt"

    # Range tool
    range_tool = RangeTool(x_range=p.x_range)
    range_tool.overlay.fill_color = "navy"
    range_tool.overlay.fill_alpha = 0.2
    select.add_tools(range_tool)
    select.toolbar.active_multi = "auto"

    return p, select, range_tool
