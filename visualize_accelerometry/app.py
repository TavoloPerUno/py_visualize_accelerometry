"""
Panel-based accelerometry annotation app with OAuth support.

Launch with:
    # Basic auth (for development):
    panel serve visualize_accelerometry/app.py --basic-auth credentials.json --cookie-secret mysecret

    # OAuth (for production, e.g. GitHub):
    panel serve visualize_accelerometry/app.py \
        --oauth-provider github \
        --oauth-key <CLIENT_ID> \
        --oauth-secret <CLIENT_SECRET> \
        --cookie-secret <RANDOM_SECRET> \
        --oauth-redirect-uri http://localhost:5006/app \
        --oauth-encryption-key <FERNET_KEY>

    # To generate a Fernet encryption key:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

    # For basic-auth, credentials.json should look like:
    {
        "natasha": "password1",
        "rusi": "password2",
        ...
    }
"""

import os

import panel as pn
from bokeh.models import ColumnDataSource
from bokeh.models.widgets import Button, DataTable, MultiSelect, TableColumn
from bokeh.models import Div, Select, TextInput

from visualize_accelerometry.callbacks import CallbackManager, build_summary_html
from visualize_accelerometry.config import DEFAULT_WINDOW_SIZE, DISPLAYED_ANNOTATION_COLUMNS
from visualize_accelerometry.plotting import make_plot
from visualize_accelerometry.state import AppState

pn.extension(sizing_mode="stretch_width")


def create_app():
    """Create one app instance per user session."""

    # Get authenticated user from Panel OAuth / BasicAuth
    user = pn.state.user if pn.state.user else "anonymous"

    # Initialize per-session state
    state = AppState(username=user)

    # Load initial data
    srs, colsource_init = state.load_file_data()
    state.colsource.data.update(colsource_init.data)

    # --- Widgets ---
    file_picker = Select(
        value=state.lst_fnames[0],
        title="Select a file",
        options=sorted(state.lst_fnames),
    )
    user_display = Div(
        text=f"<b>Logged in as:</b> {user}",
        styles={"font-size": "14px", "padding": "10px"},
    )
    time_input = TextInput(
        value=state.anchor_timestamp or "",
        title="Enter anchor time in the format Jun 1 2005 1:33 PM",
    )
    windowsize_input = TextInput(
        value=str(state.windowsize),
        title="Enter anchor windowsize in seconds",
    )

    review_multi_select = MultiSelect(
        title="Mark for review",
        value=[],
        options=[
            ("chair_stand", "Chairstand"),
            ("tug", "TUG"),
            ("3m_walk", "3MW"),
            ("6min_walk", "6MW"),
        ],
    )

    summary_box = Div(text="")

    # Buttons
    btn_update = Button(label="Update Plot", button_type="success", width=20)
    btn_prev = Button(label="Previous window", button_type="success", width=5)
    btn_next = Button(label="Next window", button_type="success", width=5)
    btn_clear = Button(label="Clear Selection", button_type="success", width=20)
    btn_clear.disabled = True
    btn_chairstand = Button(label="Mark Chairstand", button_type="success", width=20)
    btn_chairstand.disabled = True
    btn_tug = Button(label="Mark TUG", button_type="success", width=15)
    btn_tug.disabled = True
    btn_3m_walk = Button(label="Mark 3 m walk", button_type="success", width=15)
    btn_3m_walk.disabled = True
    btn_6min_walk = Button(label="Mark 6 min walk", button_type="success", width=15)
    btn_6min_walk.disabled = True
    btn_segment = Button(label="(Un/)Mark as segment", button_type="success", width=20)
    btn_segment.disabled = True
    btn_scoring = Button(label="(Un/)Mark for scoring", button_type="success", width=20)
    btn_scoring.disabled = True
    btn_review = Button(label="(Un/)Flag for review", button_type="success", width=20)
    btn_review.disabled = True
    btn_remove = Button(label="Remove annotations", button_type="success", width=20)
    btn_remove.disabled = True
    btn_export = Button(label="Export annotations", button_type="success", width=20)
    btn_notes = Button(label="Add notes", button_type="success", width=15)
    btn_notes.disabled = True

    # Data tables
    selected_data_table = DataTable(
        source=state.selected_data,
        columns=[
            TableColumn(field="start_time", title="Start time"),
            TableColumn(field="end_time", title="End time"),
        ],
        height=200,
        height_policy="auto",
        sortable=True,
        selectable=True,
        editable=True,
    )
    selected_annotations_table = DataTable(
        source=state.selected_annotations,
        columns=[
            TableColumn(field="artifact", title="Artifact"),
            TableColumn(field="segment", title="Segment"),
            TableColumn(field="scoring", title="Scoring"),
            TableColumn(field="review", title="Review"),
            TableColumn(field="start_time", title="Start Time"),
            TableColumn(field="end_time", title="End Time"),
            TableColumn(field="annotated_at", title="Annotated at"),
            TableColumn(field="user", title="User"),
            TableColumn(field="notes", title="Notes"),
        ],
        height=200,
        height_policy="auto",
        sortable=True,
        selectable=True,
        editable=True,
    )

    # Create plots
    p, select_plot, range_tool = make_plot(
        srs, state.colsource, state.annotation_sources, file_picker.value
    )

    # Widget references for callbacks
    widgets = {
        "plot": p,
        "select_plot": select_plot,
        "file_picker": file_picker,
        "time_input": time_input,
        "windowsize_input": windowsize_input,
        "summary": summary_box,
        "btn_clear": btn_clear,
        "btn_chairstand": btn_chairstand,
        "btn_tug": btn_tug,
        "btn_3m_walk": btn_3m_walk,
        "btn_6min_walk": btn_6min_walk,
        "btn_segment": btn_segment,
        "btn_scoring": btn_scoring,
        "btn_review": btn_review,
        "btn_remove": btn_remove,
        "btn_notes": btn_notes,
        "selected_data_table": selected_data_table,
        "selected_annotations_table": selected_annotations_table,
    }

    cb = CallbackManager(state, widgets)

    # Initial annotation update
    cb.update_annotations()
    summary_box.text = build_summary_html(state)

    # --- Wire up callbacks ---
    btn_update.on_click(lambda: cb.update_plot())
    btn_prev.on_click(lambda: cb.move_prev_window())
    btn_next.on_click(lambda: cb.move_next_window())
    btn_clear.on_click(lambda: _clear_selection())
    btn_chairstand.on_click(lambda: cb.mark_annotation("chair_stand"))
    btn_tug.on_click(lambda: cb.mark_annotation("tug"))
    btn_3m_walk.on_click(lambda: cb.mark_annotation("3m_walk"))
    btn_6min_walk.on_click(lambda: cb.mark_annotation("6min_walk"))
    btn_segment.on_click(lambda: cb.toggle_flag("segment"))
    btn_scoring.on_click(lambda: cb.toggle_flag("scoring"))
    btn_review.on_click(lambda: cb.toggle_flag("review"))
    btn_remove.on_click(lambda: cb.remove_selected_annotations())
    btn_export.on_click(lambda: cb.save())
    btn_notes.on_click(lambda: cb.add_notes())

    def _clear_selection():
        state.colsource.selected.indices = []

    def _on_file_change(attr, old, new):
        cb.plot_new_file(new)
        time_input.value = state.anchor_timestamp or ""
        windowsize_input.value = str(state.windowsize)

    def _on_time_change(attr, old, new):
        cb.update_anchor_timestamp(new)

    def _on_windowsize_change(attr, old, new):
        cb.update_windowsize(new)

    def _on_selection_change(attr, old, new):
        cb.update_selection()

    def _on_review_change(attr, old, new):
        cb.update_review_flags(review_multi_select.value)

    file_picker.on_change("value", _on_file_change)
    time_input.on_change("value", _on_time_change)
    windowsize_input.on_change("value", _on_windowsize_change)
    state.colsource.selected.on_change("indices", _on_selection_change)
    review_multi_select.on_change("value", _on_review_change)

    # --- Layout using Panel ---
    header = pn.Row(
        pn.pane.Bokeh(file_picker),
        pn.pane.Bokeh(user_display),
        pn.pane.Bokeh(time_input),
        pn.pane.Bokeh(windowsize_input),
        sizing_mode="stretch_width",
    )

    controls_row1 = pn.Row(
        pn.pane.Bokeh(btn_update),
        pn.pane.Bokeh(btn_prev),
        pn.pane.Bokeh(btn_next),
        pn.pane.Bokeh(btn_clear),
        pn.pane.Bokeh(btn_review),
        pn.pane.Bokeh(btn_remove),
        pn.pane.Bokeh(btn_export),
        sizing_mode="stretch_width",
    )

    controls_row2 = pn.Row(
        pn.pane.Bokeh(btn_chairstand),
        pn.pane.Bokeh(btn_tug),
        pn.pane.Bokeh(btn_3m_walk),
        pn.pane.Bokeh(btn_6min_walk),
        pn.pane.Bokeh(btn_segment),
        pn.pane.Bokeh(btn_scoring),
        pn.pane.Bokeh(btn_notes),
        sizing_mode="stretch_width",
    )

    controls = pn.Column(
        pn.Row(
            pn.pane.Bokeh(review_multi_select),
            pn.Column(controls_row1, controls_row2, sizing_mode="stretch_width"),
            sizing_mode="stretch_width",
        ),
        sizing_mode="stretch_width",
    )

    plots = pn.Column(
        pn.pane.Bokeh(p, sizing_mode="stretch_width"),
        pn.pane.Bokeh(select_plot, sizing_mode="stretch_width"),
        sizing_mode="stretch_width",
    )

    tables = pn.Row(
        pn.Column(
            pn.pane.Str("**Selected segment bounds**"),
            pn.pane.Bokeh(selected_data_table),
        ),
        pn.Column(
            pn.pane.Str("**Selected annotations**"),
            pn.pane.Bokeh(selected_annotations_table),
        ),
        sizing_mode="stretch_width",
    )

    layout = pn.Column(
        header,
        controls,
        pn.pane.Bokeh(summary_box, sizing_mode="stretch_width"),
        plots,
        tables,
        sizing_mode="stretch_both",
    )

    return layout


# When served with `panel serve app.py`, Panel calls create_app() per session,
# giving each user isolated state.
create_app().servable(title="Visualize Accelerometry")
