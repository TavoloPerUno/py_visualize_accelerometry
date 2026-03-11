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

import json
import os
import sys

import pandas as pd

# Ensure the project root is on sys.path so package imports work
# regardless of how panel serve is invoked.
try:
    _project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
except NameError:
    _project_root = os.getcwd()
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import panel as pn
from bokeh.models.widgets import DataTable, TableColumn
from bokeh.models import Div

from visualize_accelerometry.callbacks import CallbackManager, build_summary_html
from visualize_accelerometry import config as _config
from visualize_accelerometry.config import (
    ADMIN_USERS, ANNOTATOR_USERS, ARTIFACT_COLORS,
    KNOWN_USERS, LST_COLORS, UCHICAGO_MAROON,
)
from visualize_accelerometry.plotting import make_plot
from visualize_accelerometry.state import AppState

pn.extension(sizing_mode="stretch_width", notifications=True)

# Theme notification toasts to UChicago palette
pn.state.notifications.types = [
    {"type": "warning", "background": "#58595b",
     "icon": {"className": "fas fa-exclamation-triangle", "tagName": "i", "color": "white"}},
    {"type": "info", "background": "#800000",
     "icon": {"className": "fas fa-info-circle", "tagName": "i", "color": "white"}},
    {"type": "success", "background": "#7EBEC5",
     "icon": {"className": "fas fa-check-circle", "tagName": "i", "color": "white"}},
]

# Set custom logout template to match login page styling
_logout_template_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "templates", "logout.html"
)
if os.path.exists(_logout_template_path):
    from panel.auth import LogoutHandler
    from jinja2 import Environment
    _jinja_env = Environment()
    with open(_logout_template_path) as _f:
        LogoutHandler._logout_template = _jinja_env.from_string(_f.read())

ACCENT_COLOR = UCHICAGO_MAROON


def _load_credentials():
    with open(_config.CREDENTIALS_FILE, "r") as f:
        return json.load(f)


def _save_credentials(creds):
    with open(_config.CREDENTIALS_FILE, "w") as f:
        json.dump(creds, f, indent=4)


def create_app():
    """Create one app instance per user session.

    Called once per browser session by Panel.  Builds all widgets,
    wires callbacks, assembles the layout, and returns the template.

    Returns
    -------
    pn.template.FastListTemplate
        Fully configured Panel template ready to be served.
    """

    # Get authenticated user from Panel OAuth / BasicAuth
    user = pn.state.user if pn.state.user else "anonymous"
    is_admin = user in ADMIN_USERS

    # Initialize per-session state
    state = AppState(username=user)

    # Load initial data
    pdf_signal = state.load_file_data()

    # --- Sidebar widgets (Panel native for responsive layout) ---
    file_picker = pn.widgets.Select(
        name="File",
        value=state.lst_fnames[0],
        options=sorted(state.lst_fnames),
        sizing_mode="stretch_width",
    )
    time_input = pn.widgets.TextInput(
        name="Anchor time",
        value=state.anchor_timestamp or "",
        placeholder="Jun 1 2005 1:33 PM",
        sizing_mode="stretch_width",
    )
    windowsize_input = pn.widgets.TextInput(
        name="Window size (seconds)",
        value=str(state.windowsize),
        sizing_mode="stretch_width",
    )
    review_multi_select = pn.widgets.MultiSelect(
        name="Flag file for review",
        value=[],
        options={
            "Chairstand": "chair_stand",
            "TUG": "tug",
            "3MW": "3m_walk",
            "6MW": "6min_walk",
        },
        size=4,
        sizing_mode="stretch_width",
    )

    # Navigation buttons
    # Maroon gradient style for primary action buttons (Update Plot, Admin)
    _maroon_btn_css = [
        ".bk-btn-success {"
        "  background: linear-gradient(180deg, #8a0000 0%, #700000 100%) !important;"
        "  border: 1px solid rgba(255,255,255,0.18) !important;"
        "  box-shadow: 0 1px 4px rgba(128,0,0,0.3),"
        "    inset 0 1px 0 rgba(255,255,255,0.2) !important;"
        "  color: #fff !important;"
        "}",
        ".bk-btn-success:hover {"
        "  background: linear-gradient(180deg, #700000 0%, #5a0000 100%)"
        " !important;"
        "}",
    ]
    btn_update = pn.widgets.Button(
        name="Update Plot", button_type="success", sizing_mode="stretch_width",
        stylesheets=_maroon_btn_css,
    )
    btn_prev = pn.widgets.Button(
        name="\u25c0 Previous", button_type="default", sizing_mode="stretch_width",
    )
    btn_next = pn.widgets.Button(
        name="Next \u25b6", button_type="default", sizing_mode="stretch_width",
    )
    # Annotation buttons
    # Override Bokeh's default flex sizing so toolbar buttons grow to
    # fill the Row, wrap on narrow screens, and never clip their text.
    _toolbar_btn_css = [
        ":host {"
        "  flex: 1 1 auto !important;"
        "  min-width: fit-content !important;"
        "  max-width: none !important;"
        "  width: auto !important;"
        "}"
    ]

    btn_export = pn.widgets.Button(
        name="Export", button_type="warning", stylesheets=_toolbar_btn_css,
    )

    # --- Main area widgets ---
    summary_pn = pn.pane.HTML("", sizing_mode="stretch_width")
    btn_chairstand = pn.widgets.Button(
        name="Chairstand", button_type="success", disabled=True, stylesheets=_toolbar_btn_css,
    )
    btn_tug = pn.widgets.Button(
        name="TUG", button_type="success", disabled=True, stylesheets=_toolbar_btn_css,
    )
    btn_3m_walk = pn.widgets.Button(
        name="3m Walk", button_type="success", disabled=True, stylesheets=_toolbar_btn_css,
    )
    btn_6min_walk = pn.widgets.Button(
        name="6min Walk", button_type="success", disabled=True, stylesheets=_toolbar_btn_css,
    )
    btn_segment = pn.widgets.Button(
        name="Segment", button_type="primary", disabled=True, stylesheets=_toolbar_btn_css,
    )
    btn_scoring = pn.widgets.Button(
        name="Scoring", button_type="primary", disabled=True, stylesheets=_toolbar_btn_css,
    )
    btn_review = pn.widgets.Button(
        name="Review", button_type="primary", disabled=True, stylesheets=_toolbar_btn_css,
    )
    notes_input = pn.widgets.TextInput(
        name="Notes",
        placeholder="Type notes here...",
        sizing_mode="stretch_width",
        disabled=True,
    )
    btn_notes = pn.widgets.Button(
        name="Save notes", button_type="warning", disabled=True,
    )
    btn_clear = pn.widgets.Button(
        name="Clear", button_type="danger", disabled=True, stylesheets=_toolbar_btn_css,
    )
    btn_remove = pn.widgets.Button(
        name="Delete", button_type="danger", disabled=True, stylesheets=_toolbar_btn_css,
    )

    # Data tables (Bokeh — they bind to ColumnDataSources)
    from bokeh.models import InlineStyleSheet
    table_css = InlineStyleSheet(css="""
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600&display=swap');
        .slick-header-columns, .slick-cell {
            font-family: 'Montserrat', Helvetica, Arial, sans-serif !important;
        }
        .slick-header-columns {
            background-color: #58595b !important;
            border-bottom: none !important;
        }
        .slick-header-column {
            color: #fff !important;
            font-size: 11px !important;
            font-weight: 600 !important;
            border-right: 1px solid #6e6f71 !important;
        }
        .slick-cell {
            border-bottom: 1px solid #e0e0e0 !important;
            border-right: 1px solid #e0e0e0 !important;
            font-size: 11px !important;
            padding: 2px 6px !important;
        }
        .slick-row:nth-child(even) {
            background-color: #f5f5f5 !important;
        }
        .slick-row:nth-child(odd) {
            background-color: #fff !important;
        }
    """)

    selected_data_table = DataTable(
        source=state.selected_data,
        columns=[
            TableColumn(field="start_time", title="Start time"),
            TableColumn(field="end_time", title="End time"),
        ],
        height=80,
        sortable=True,
        selectable=True,
        editable=True,
        sizing_mode="stretch_width",
        fit_columns=True,
        stylesheets=[table_css],
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
        height=150,
        sortable=True,
        selectable=True,
        editable=True,
        sizing_mode="stretch_width",
        fit_columns=True,
        stylesheets=[table_css],
    )

    # File label at top of main area
    file_label = pn.pane.Markdown(
        f"### Annotating: {file_picker.value}",
        styles={"color": UCHICAGO_MAROON, "margin": "0", "padding": "0"},
        margin=(0, 0),
    )

    # Create plots (native Bokeh with LTTB downsampling)
    main_plot_pane, range_plot_pane, main_bokeh_fig, signal_cds = make_plot(
        pdf_signal, state.annotation_cds
    )
    state.signal_cds = signal_cds

    # Widget references for callbacks
    widgets = {
        "main_plot": main_plot_pane,
        "range_plot": range_plot_pane,
        "main_fig": main_bokeh_fig,
        "summary": summary_pn,
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
        "notes_input": notes_input,
        "file_label": file_label,
        "selected_data_table": selected_data_table,
        "selected_annotations_table": selected_annotations_table,
        "btn_prev": btn_prev,
        "btn_next": btn_next,
    }

    cb = CallbackManager(state, widgets)

    # Wire box-select callback on the signal CDS.
    # Uses state.signal_cds (not the local signal_cds variable) so that
    # after a plot rebuild — which creates a new CDS — this callback
    # still reads timestamps from the *current* data source.
    def _on_selection_change(attr, old, new):
        cds = state.signal_cds
        if new and cds is not None:
            ts = cds.data["timestamp"]
            min_idx, max_idx = min(new), max(new)
            # Guard against stale indices from a previous CDS
            if max_idx < len(ts):
                state.selection_bounds = (
                    pd.to_datetime(ts[min_idx]),
                    pd.to_datetime(ts[max_idx]),
                )
            else:
                state.selection_bounds = None
        else:
            state.selection_bounds = None
        cb.update_selection()

    signal_cds.selected.on_change("indices", _on_selection_change)
    widgets["_selection_wire_fn"] = _on_selection_change

    # --- Wire up callbacks ---
    def _nav(fn):
        def wrapper(event):
            fn()
            time_input.value = state.anchor_timestamp or ""
        return wrapper

    btn_update.on_click(_nav(cb.update_plot))
    btn_prev.on_click(_nav(cb.move_prev_window))
    btn_next.on_click(_nav(cb.move_next_window))
    btn_clear.on_click(lambda e: _clear_selection())
    btn_chairstand.on_click(lambda e: cb.mark_annotation("chair_stand"))
    btn_tug.on_click(lambda e: cb.mark_annotation("tug"))
    btn_3m_walk.on_click(lambda e: cb.mark_annotation("3m_walk"))
    btn_6min_walk.on_click(lambda e: cb.mark_annotation("6min_walk"))
    btn_segment.on_click(lambda e: cb.toggle_flag("segment"))
    btn_scoring.on_click(lambda e: cb.toggle_flag("scoring"))
    btn_review.on_click(lambda e: cb.toggle_flag("review"))
    btn_remove.on_click(lambda e: cb.remove_selected_annotations())
    btn_export.on_click(lambda e: cb.save())
    btn_notes.on_click(lambda e: cb.add_notes(notes_input.value))

    def _clear_selection():
        state.selection_bounds = None
        state.signal_cds.selected.indices = []
        cb.update_selection()

    def _on_file_change(event):
        cb.plot_new_file(event.new)
        time_input.value = state.anchor_timestamp or ""
        windowsize_input.value = str(state.windowsize)

    def _on_time_change(event):
        cb.update_anchor_timestamp(event.new)

    def _on_windowsize_change(event):
        cb.update_windowsize(event.new)

    def _on_review_change(event):
        cb.update_review_flags(event.new)

    file_picker.param.watch(_on_file_change, "value")
    time_input.param.watch(_on_time_change, "value")
    windowsize_input.param.watch(_on_windowsize_change, "value")
    review_multi_select.param.watch(_on_review_change, "value")

    # --- Layout ---
    sidebar_items = [
        file_picker,
        time_input,
        windowsize_input,
        pn.layout.Divider(),
        pn.Row(btn_prev, btn_next, sizing_mode="stretch_width"),
        btn_update,
        pn.layout.Divider(),
        review_multi_select,
        pn.layout.Divider(),
        notes_input,
        btn_notes,
    ]

    # --- Admin panel in sidebar (for admin users) ---
    admin_section = None
    if is_admin:
        admin_status = pn.pane.HTML("", sizing_mode="stretch_width")
        admin_user_list_col = pn.Column(sizing_mode="stretch_width")
        add_username = pn.widgets.TextInput(placeholder="username", sizing_mode="stretch_width")
        add_password = pn.widgets.PasswordInput(placeholder="password", sizing_mode="stretch_width")
        add_role = pn.widgets.Select(
            options=["annotator", "admin", "both"], value="annotator",
            sizing_mode="stretch_width",
        )
        add_btn = pn.widgets.Button(
            name="Add User", button_type="primary", sizing_mode="stretch_width",
        )

        def _admin_msg(text, error=False):
            """Format an admin status message (success or error)."""
            bg = "#fce4ec" if error else "#e8f5e9"
            fg = "#c62828" if error else "#2e7d32"
            return (
                f"<div style='padding:4px 8px;background:{bg};"
                f"color:{fg};border-radius:3px;"
                f"font-size:11px;'>{text}</div>"
            )

        def _get_user_role(u):
            if u in ADMIN_USERS and u in ANNOTATOR_USERS:
                return "both"
            elif u in ADMIN_USERS:
                return "admin"
            elif u in ANNOTATOR_USERS:
                return "annotator"
            return "login only"

        def _make_remove_cb(uname):
            def _remove(event):
                if uname == user:
                    admin_status.object = _admin_msg(
                        "Cannot remove yourself.", error=True
                    )
                    return
                creds = _load_credentials()
                if uname in creds:
                    del creds[uname]
                    _save_credentials(creds)
                if uname in ANNOTATOR_USERS:
                    ANNOTATOR_USERS.remove(uname)
                if uname in ADMIN_USERS:
                    ADMIN_USERS.remove(uname)
                KNOWN_USERS.clear()
                KNOWN_USERS.extend(sorted(set(ADMIN_USERS + ANNOTATOR_USERS)))
                admin_status.object = _admin_msg(
                    f"Removed <b>{uname}</b>."
                )
                _refresh_user_list()
            return _remove

        def _make_role_cb(uname):
            def _change_role(event):
                new_role = event.new
                # Remove from both lists first
                if uname in ANNOTATOR_USERS:
                    ANNOTATOR_USERS.remove(uname)
                if uname in ADMIN_USERS:
                    ADMIN_USERS.remove(uname)
                # Re-add based on new role
                if new_role in ("annotator", "both"):
                    ANNOTATOR_USERS.append(uname)
                    ANNOTATOR_USERS.sort()
                if new_role in ("admin", "both"):
                    ADMIN_USERS.append(uname)
                KNOWN_USERS.clear()
                KNOWN_USERS.extend(sorted(set(ADMIN_USERS + ANNOTATOR_USERS)))
                admin_status.object = _admin_msg(
                    f"<b>{uname}</b> role \u2192 {new_role}."
                )
            return _change_role

        def _refresh_user_list():
            creds = _load_credentials()
            all_users = sorted(set(list(creds.keys()) + ADMIN_USERS + ANNOTATOR_USERS))
            rows = []
            for u in all_users:
                role_select = pn.widgets.Select(
                    options=["annotator", "admin", "both"], value=_get_user_role(u),
                    width=90, margin=(0, 2),
                    stylesheets=[":host { font-size: 9px; }"],
                )
                role_select.param.watch(_make_role_cb(u), "value")
                del_btn = pn.widgets.Button(
                    name="\u2715", button_type="light",
                    width=24, margin=(0, 0),
                    stylesheets=[
                        ":host .bk-btn { font-size:11px;"
                        " padding:0 4px; color:#c62828;"
                        " border:none; min-width:24px; }"
                    ],
                )
                del_btn.on_click(_make_remove_cb(u))
                name_html = pn.pane.HTML(
                    f"<span style='font-size:11px;font-family:Montserrat,sans-serif;'>{u}</span>",
                    sizing_mode="stretch_width", align="center", margin=(0, 0),
                )
                row = pn.Row(name_html, role_select, del_btn, sizing_mode="stretch_width",
                             margin=(0, 0),
                             styles={"border-bottom": "1px solid #e0e0e0", "padding": "1px 0"})
                rows.append(row)
            admin_user_list_col.clear()
            admin_user_list_col.extend(rows)

        def _add_user(event):
            uname = add_username.value.strip().lower()
            pwd = add_password.value
            role = add_role.value
            if not uname or not pwd:
                admin_status.object = _admin_msg(
                    "Username and password required.", error=True
                )
                return
            creds = _load_credentials()
            if uname in creds:
                admin_status.object = _admin_msg(
                    f"User <b>{uname}</b> already exists.", error=True
                )
                return
            creds[uname] = pwd
            _save_credentials(creds)
            if role in ("annotator", "both"):
                if uname not in ANNOTATOR_USERS:
                    ANNOTATOR_USERS.append(uname)
                    ANNOTATOR_USERS.sort()
            if role in ("admin", "both"):
                if uname not in ADMIN_USERS:
                    ADMIN_USERS.append(uname)
            KNOWN_USERS.clear()
            KNOWN_USERS.extend(sorted(set(ADMIN_USERS + ANNOTATOR_USERS)))
            admin_status.object = _admin_msg(
                f"User <b>{uname}</b> added as {role}."
            )
            add_username.value = ""
            add_password.value = ""
            _refresh_user_list()

        add_btn.on_click(_add_user)
        _refresh_user_list()

        # Custom collapsible admin section (avoids Card shadow DOM
        # issues with title font and width changes on expand).
        _add_user_label = pn.pane.HTML(
            "<b style='font-size:11px;color:#58595b;"
            "font-family:Montserrat,sans-serif;'>Add User</b>",
            sizing_mode="stretch_width",
        )
        admin_body = pn.Column(
            admin_status,
            admin_user_list_col,
            pn.layout.Divider(),
            _add_user_label,
            add_username, add_password, add_role, add_btn,
            sizing_mode="stretch_width",
            visible=False,
            margin=(0, 10),
            styles={
                "border": "1px solid rgba(128,0,0,0.2)",
                "border-top": "none",
                "border-radius": "0 0 8px 8px",
                "padding": "6px",
                "background": "rgba(255,255,255,0.65)",
            },
        )
        admin_toggle_btn = pn.widgets.Button(
            name="User Admin",
            button_type="success",
            sizing_mode="stretch_width",
            margin=(5, 10, 0, 10),
            stylesheets=_maroon_btn_css,
        )

        def _toggle_admin(event):
            admin_body.visible = not admin_body.visible

        admin_toggle_btn.on_click(_toggle_admin)
        admin_section = pn.Column(
            admin_toggle_btn, admin_body,
            sizing_mode="stretch_width", margin=(5, 0),
        )
        sidebar_items += [pn.layout.Divider(), admin_section]

    sidebar = pn.Column(*sidebar_items, sizing_mode="stretch_width")

    # Enable flex-wrap on the Row so toolbar buttons wrap on
    # narrow screens instead of overflowing.
    _row_wrap_css = [
        ":host { flex-wrap: wrap !important;"
        " gap: 4px !important; }",
        ":host > * { flex: 1 1 auto !important;"
        " max-width: none !important;"
        " width: auto !important;"
        " min-width: fit-content !important; }",
    ]
    annotation_tools = pn.Row(
        btn_chairstand, btn_tug, btn_3m_walk, btn_6min_walk,
        btn_segment, btn_scoring,
        btn_clear, btn_remove, btn_review, btn_export,
        sizing_mode="stretch_width",
        styles={"padding": "6px 0", "background": "#f7f7f7", "border-radius": "4px"},
        stylesheets=_row_wrap_css,
    )

    # Tables are still Bokeh DataTables (lightweight, few rows)
    from bokeh.layouts import column as bk_column, row as bk_row

    _tbl_title_css = (
        "font-size:12px; font-family:Montserrat,sans-serif;"
    )
    selected_data_title = Div(
        text=f"<b style='{_tbl_title_css}'>Selected segment bounds</b>"
    )
    selected_annotations_title = Div(
        text=f"<b style='{_tbl_title_css}'>Selected annotations</b>"
    )

    tables_block = bk_row(
        bk_column(selected_data_title, selected_data_table, width_policy="fixed", width=300),
        bk_column(selected_annotations_title, selected_annotations_table, sizing_mode="stretch_width"),
        sizing_mode="stretch_width",
    )

    # Color key strip — shows signal colors, activity overlays, and flags
    def _color_dot(color, label):
        """Return an HTML snippet for a colored dot + label."""
        return (
            f"<span style='display:inline-flex; align-items:center;"
            f" margin-right:12px;'>"
            f"<span style='width:10px; height:10px; border-radius:50%;"
            f" background:{color}; display:inline-block;"
            f" margin-right:4px;'></span>"
            f"<span style='font-size:10px; color:#58595b;'>"
            f"{label}</span></span>"
        )

    signal_keys = [
        _color_dot(LST_COLORS[i], ax)
        for i, ax in enumerate(["X", "Y", "Z"])
    ]
    activity_keys = [
        _color_dot(c, n) for n, c in ARTIFACT_COLORS.items()
    ]

    m = UCHICAGO_MAROON  # shorthand for flag CSS patterns
    flag_styles = {
        "segment": (
            f"border:2px solid {m}; background:"
            f"repeating-linear-gradient(45deg,transparent,"
            f"transparent 2px,{m} 2px,{m} 3px)"
        ),
        "scoring": (
            f"border:2px solid {m}; background:"
            f"radial-gradient(circle, {m} 1.5px, transparent 1.5px);"
            f" background-size:5px 5px"
        ),
        "review": (
            f"border:2px solid {m}; background:"
            f"repeating-conic-gradient({m} 0% 25%,"
            f" transparent 0% 50%) 50%/6px 6px"
        ),
    }
    flag_keys = [
        f"<span style='display:inline-flex; align-items:center;"
        f" margin-right:12px;'>"
        f"<span style='width:14px; height:14px; display:inline-block;"
        f" margin-right:4px; {style}'></span>"
        f"<span style='font-size:10px; color:#58595b;'>"
        f"{label}</span></span>"
        for label, style in flag_styles.items()
    ]

    _sep = (
        "<span style='border-left:1px solid #ccc;"
        " height:14px; margin:0 4px;'></span>"
    )
    _hdr = (
        "<span style='font-size:10px; font-weight:600;"
        " color:#58595b; margin-right:4px;'>"
    )
    color_key_html = (
        "<div style='display:flex; align-items:center; gap:6px;"
        " padding:4px 8px; background:#f7f7f7; border-radius:3px;"
        " font-family:Montserrat,sans-serif; flex-wrap:wrap;'>"
        f"{_hdr}Signals:</span>{''.join(signal_keys)}"
        f"{_sep}"
        f"{_hdr}Activities:</span>{''.join(activity_keys)}"
        f"{_sep}"
        f"{_hdr}Flags:</span>{''.join(flag_keys)}"
        "</div>"
    )
    color_key = pn.pane.HTML(color_key_html, sizing_mode="stretch_width")

    main_content = pn.Column(
        file_label,
        annotation_tools,
        color_key,
        summary_pn,
        main_plot_pane,       # index 4
        range_plot_pane,      # index 5
        pn.pane.Bokeh(tables_block, sizing_mode="stretch_width"),
        sizing_mode="stretch_both",
        margin=(0, 0),
    )
    # Give callbacks access to the layout so they can swap plot panes in-place
    widgets["main_content"] = main_content
    widgets["main_plot_idx"] = 4
    widgets["range_plot_idx"] = 5

    # Initial load (must be after main_content is in widgets)
    cb.update_annotations()
    cb._update_nav_buttons()
    summary_pn.object = build_summary_html(state)

    uchicago_css = """
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap');
    :root {
        --accent-color: #800000;
    }
    /* Hide the default hamburger button */
    #sidebar-button {
        display: none !important;
    }
    /* Hide busy indicator */
    .pn-busy-container {
        display: none !important;
    }
    /* Reduce whitespace in main content pane */
    #main {
        padding: 0 4px !important;
    }
    .main-margin {
        margin-top: 0 !important;
    }
    .card-margin {
        margin: 2px 0 !important;
    }
    #content {
        padding: 0 !important;
    }
    body, .bk, .bk-root, .pn-widget, .card-title, input, select, button, .markdown {
        font-family: 'Montserrat', Helvetica, Arial, sans-serif !important;
    }

    /* ── Liquid Glass: Header ── */
    #header {
        background: linear-gradient(
            135deg,
            rgba(128, 0, 0, 0.85) 0%,
            rgba(128, 0, 0, 0.72) 50%,
            rgba(128, 0, 0, 0.85) 100%
        ) !important;
        backdrop-filter: blur(24px) saturate(180%) !important;
        -webkit-backdrop-filter: blur(24px) saturate(180%) !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.15) !important;
        box-shadow: 0 2px 16px rgba(0, 0, 0, 0.12) !important;
    }

    /* ── Liquid Glass: Sidebar ── */
    #sidebar {
        background: linear-gradient(
            180deg,
            rgba(245, 245, 247, 0.82) 0%,
            rgba(240, 240, 242, 0.75) 100%
        ) !important;
        backdrop-filter: blur(40px) saturate(200%) !important;
        -webkit-backdrop-filter: blur(40px) saturate(200%) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.5) !important;
        box-shadow: 1px 0 20px rgba(0, 0, 0, 0.06) !important;
        overflow-x: hidden !important;
    }

    /* ── Liquid Glass: Buttons ── */
    .bk-btn {
        font-size: 9px !important;
        padding: 2px 6px !important;
        border-radius: 8px !important;
        transition: all 0.2s ease !important;
    }
    .bk-btn-success {
        background: linear-gradient(180deg, #8a0000 0%, #700000 100%) !important;
        border: 1px solid rgba(255, 255, 255, 0.18) !important;
        box-shadow: 0 1px 4px rgba(128, 0, 0, 0.3),
                    inset 0 1px 0 rgba(255, 255, 255, 0.2) !important;
        color: #fff !important;
    }
    .bk-btn-success:hover {
        background: linear-gradient(180deg, #700000 0%, #5a0000 100%) !important;
        box-shadow: 0 2px 6px rgba(128, 0, 0, 0.4),
                    inset 0 1px 0 rgba(255, 255, 255, 0.18) !important;
    }
    .bk-btn-warning {
        background: linear-gradient(
            180deg,
            rgba(126, 190, 197, 0.85) 0%,
            rgba(106, 170, 177, 0.92) 100%
        ) !important;
        border: 1px solid rgba(255, 255, 255, 0.25) !important;
        box-shadow: 0 1px 3px rgba(126, 190, 197, 0.3),
                    inset 0 1px 0 rgba(255, 255, 255, 0.2) !important;
        color: #000 !important;
    }
    .bk-btn-warning:hover {
        background: linear-gradient(
            180deg,
            rgba(106, 170, 177, 0.9) 0%,
            rgba(86, 150, 157, 1) 100%
        ) !important;
        box-shadow: 0 2px 6px rgba(126, 190, 197, 0.4),
                    inset 0 1px 0 rgba(255, 255, 255, 0.22) !important;
    }
    .bk-btn-danger {
        background: linear-gradient(
            180deg,
            rgba(88, 89, 91, 0.85) 0%,
            rgba(68, 69, 71, 0.92) 100%
        ) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        box-shadow: 0 1px 3px rgba(88, 89, 91, 0.3),
                    inset 0 1px 0 rgba(255, 255, 255, 0.12) !important;
        color: #fff !important;
    }
    .bk-btn-danger:hover {
        background: linear-gradient(
            180deg,
            rgba(68, 69, 71, 0.9) 0%,
            rgba(48, 49, 51, 1) 100%
        ) !important;
    }
    .bk-btn-primary {
        background: linear-gradient(
            180deg,
            rgba(255, 255, 255, 0.9) 0%,
            rgba(245, 245, 247, 0.95) 100%
        ) !important;
        border: 1.5px solid rgba(128, 0, 0, 0.5) !important;
        color: #800000 !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08),
                    inset 0 1px 0 rgba(255, 255, 255, 0.8) !important;
    }
    .bk-btn-primary:hover {
        background: linear-gradient(
            180deg,
            rgba(128, 0, 0, 0.88) 0%,
            rgba(100, 0, 0, 0.95) 100%
        ) !important;
        color: #fff !important;
        border-color: transparent !important;
        box-shadow: 0 2px 6px rgba(128, 0, 0, 0.35),
                    inset 0 1px 0 rgba(255, 255, 255, 0.15) !important;
    }
    .bk-btn-light {
        background: linear-gradient(
            180deg,
            rgba(247, 247, 247, 0.8) 0%,
            rgba(235, 235, 237, 0.85) 100%
        ) !important;
        border: 1px solid rgba(88, 89, 91, 0.25) !important;
        color: #58595b !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05),
                    inset 0 1px 0 rgba(255, 255, 255, 0.6) !important;
    }
    .bk-btn-light:hover {
        background: linear-gradient(
            180deg,
            rgba(235, 235, 237, 0.85) 0%,
            rgba(225, 225, 227, 0.9) 100%
        ) !important;
    }

    /* ── Liquid Glass: Cards ── */
    .card {
        background: rgba(255, 255, 255, 0.65) !important;
        backdrop-filter: blur(20px) saturate(180%) !important;
        -webkit-backdrop-filter: blur(20px) saturate(180%) !important;
        border: 1px solid rgba(255, 255, 255, 0.5) !important;
        border-radius: 12px !important;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06),
                    inset 0 1px 0 rgba(255, 255, 255, 0.7) !important;
        overflow: hidden !important;
    }
    .card-header {
        background: linear-gradient(
            135deg,
            rgba(128, 0, 0, 0.88) 0%,
            rgba(128, 0, 0, 0.75) 50%,
            rgba(128, 0, 0, 0.88) 100%
        ) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        padding: 4px 8px !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.12) !important;
    }
    .card-body {
        padding: 4px !important;
    }

    /* ── Liquid Glass: Inputs ── */
    .bk-input {
        border-radius: 8px !important;
        border: 1px solid rgba(0, 0, 0, 0.1) !important;
        background: rgba(255, 255, 255, 0.7) !important;
        backdrop-filter: blur(8px) !important;
        -webkit-backdrop-filter: blur(8px) !important;
        box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.04) !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
    }
    .bk-input:focus {
        border-color: rgba(128, 0, 0, 0.4) !important;
        box-shadow: 0 0 0 3px rgba(128, 0, 0, 0.08),
                    inset 0 1px 2px rgba(0, 0, 0, 0.04) !important;
    }

    /* ── Liquid Glass: Data tables ── */
    .slick-header-columns {
        background: linear-gradient(
            180deg,
            rgba(128, 0, 0, 0.88) 0%,
            rgba(100, 0, 0, 0.95) 100%
        ) !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
    }
    .slick-header-column {
        color: #fff !important;
        font-size: 11px !important;
        font-weight: 600 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.1) !important;
    }
    .slick-cell {
        border: 1px solid rgba(0, 0, 0, 0.06) !important;
        font-size: 11px !important;
    }
    .slick-row:nth-child(even) {
        background-color: rgba(250, 250, 250, 0.7) !important;
    }
    .slick-row:nth-child(odd) {
        background-color: rgba(255, 255, 255, 0.8) !important;
    }
    .slick-row.selected .slick-cell {
        background-color: rgba(128, 0, 0, 0.08) !important;
    }


    /* ── Liquid Glass: Notification toasts ── */
    .notyf__toast {
        border-radius: 14px !important;
        backdrop-filter: blur(20px) saturate(180%) !important;
        -webkit-backdrop-filter: blur(20px) saturate(180%) !important;
        border: 1px solid rgba(255, 255, 255, 0.18) !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15) !important;
    }
    """

    # Header bar: [spacer] Logged in as user | Impersonate | Logout icon
    header_user_label = pn.pane.HTML(
        f"<span style='color:#fff; font-size:11px;"
        f" font-family:Montserrat,sans-serif;"
        f" white-space:nowrap;'>Logged in as <b>{user}</b></span>",
        sizing_mode="fixed", align="center", margin=(0, 2),
    )

    _imp_default = "Impersonate as"
    _imp_stop = "Stop impersonating"
    impersonate_options = [_imp_default] + [u for u in KNOWN_USERS if u != user]
    impersonate_select = pn.widgets.Select(
        name="",
        options=impersonate_options,
        value=_imp_default,
        width=130,
        margin=(0, 2),
        stylesheets=[
            ":host { font-size: 10px; }"
            " :host select { color: #333 !important;"
            " background: #fff !important; }"
        ],
    )

    def _on_impersonate(event):
        if not event.new or event.new == _imp_default or event.new == _imp_stop:
            state.username = user
            cb.update_annotations()
            summary_pn.object = build_summary_html(state)
            header_user_label.object = (
                f"<span style='color:#fff; font-size:11px; font-family:Montserrat,sans-serif; white-space:nowrap;'>"
                f"Logged in as <b>{user}</b></span>"
            )
            impersonate_select.options = [_imp_default] + [u for u in KNOWN_USERS if u != user]
            impersonate_select.value = _imp_default
        else:
            state.username = event.new
            cb.update_annotations()
            summary_pn.object = build_summary_html(state)
            header_user_label.object = (
                f"<span style='color:#fff; font-size:11px; font-family:Montserrat,sans-serif; white-space:nowrap;'>"
                f"<b>{user}</b> impersonating as</span>"
            )
            impersonate_select.options = [_imp_stop] + [u for u in KNOWN_USERS if u != user]

    impersonate_select.param.watch(_on_impersonate, "value")

    _header_icon_style = (
        "color:#fff; text-decoration:none; font-size:12px; "
        "font-family:Montserrat,sans-serif; opacity:0.7; display:inline-flex; align-items:center; "
        "justify-content:center; height:100%;"
    )
    _header_icon_kw = dict(sizing_mode="fixed", width=20, align="center", margin=(0, 2),
                           styles={"display": "flex", "align-items": "center"})

    help_link = pn.pane.HTML(
        f"<a href='https://tavoloperuno.github.io/py_visualize_accelerometry/' target='_blank' "
        f"title='Documentation' style='{_header_icon_style}'>"
        "<svg width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' "
        "stroke-linecap='round' stroke-linejoin='round'>"
        "<circle cx='12' cy='12' r='10'/>"
        "<path d='M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3'/>"
        "<line x1='12' y1='17' x2='12.01' y2='17'/>"
        "</svg></a>",
        **_header_icon_kw,
    )

    about_link = pn.pane.HTML(
        f"<a href='https://github.com/TavoloPerUno/py_visualize_accelerometry' target='_blank' "
        f"title='GitHub' style='{_header_icon_style}'>"
        "<svg width='14' height='14' viewBox='0 0 24 24' fill='currentColor'>"
        "<path d='M12 0C5.37 0 0 5.37 0 12c0 5.3 3.44 9.8 8.2 11.39.6.11.82-.26.82-.58 "
        "0-.28-.01-1.04-.02-2.04-3.34.73-4.04-1.61-4.04-1.61-.55-1.39-1.33-1.76-1.33-1.76-1.09-.74.08-.73.08-.73 "
        "1.2.08 1.84 1.24 1.84 1.24 1.07 1.83 2.8 1.3 3.49 1 .11-.78.42-1.3.76-1.6-2.67-.3-5.47-1.33-5.47-5.93 "
        "0-1.31.47-2.38 1.24-3.22-.13-.3-.54-1.52.12-3.18 0 0 1.01-.32 3.3 1.23a11.5 11.5 0 0 1 6.02 0c2.28-1.55 "
        "3.29-1.23 3.29-1.23.66 1.66.25 2.88.12 3.18.77.84 1.24 1.91 1.24 3.22 0 4.61-2.81 5.63-5.48 5.92.43.37.81 "
        "1.1.81 2.22 0 1.6-.01 2.9-.01 3.29 0 .32.21.7.82.58A12.01 12.01 0 0 0 24 12c0-6.63-5.37-12-12-12z'/>"
        "</svg></a>",
        **_header_icon_kw,
    )

    logout_link = pn.pane.HTML(
        f"<a href='/logout' title='Sign out' style='{_header_icon_style}'>"
        "<svg width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' "
        "stroke-linecap='round' stroke-linejoin='round'>"
        "<path d='M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4'/>"
        "<polyline points='16 17 21 12 16 7'/>"
        "<line x1='21' y1='12' x2='9' y2='12'/>"
        "</svg></a>",
        sizing_mode="fixed", width=20, align="center", margin=(0, 8, 0, 2),
        styles={"display": "flex", "align-items": "center"},
    )

    header_row = pn.Row(
        pn.Spacer(),
        header_user_label,
        impersonate_select,
        help_link,
        about_link,
        logout_link,
        sizing_mode="stretch_width",
        align="center",
        styles={"margin-right": "0px", "gap": "2px"},
    )

    template = pn.template.FastListTemplate(
        title="Visualize/ Annotate Accelerometry Data",
        favicon="visualize_accelerometry/static/favicon.svg",
        logo="visualize_accelerometry/static/logo.svg",
        sidebar=sidebar,
        main=[main_content],
        header=[header_row],
        accent_base_color=ACCENT_COLOR,
        header_background=ACCENT_COLOR,
        sidebar_width=280,
        theme_toggle=False,
        raw_css=[uchicago_css, """
            #sidebar-toggle {
                position: fixed;
                top: 50%;
                transform: translateY(-50%);
                z-index: 10000;
                width: 16px;
                height: 48px;
                background: linear-gradient(
                    180deg,
                    rgba(128, 0, 0, 0.82) 0%,
                    rgba(128, 0, 0, 0.68) 100%
                );
                backdrop-filter: blur(16px) saturate(180%);
                -webkit-backdrop-filter: blur(16px) saturate(180%);
                border: none;
                border-left: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 0 10px 10px 0;
                color: #fff;
                font-size: 11px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.25s cubic-bezier(0.945, 0.02, 0.27, 0.665);
                box-shadow: 2px 0 12px rgba(0, 0, 0, 0.1),
                            inset 0 1px 0 rgba(255, 255, 255, 0.15);
                padding: 0;
                line-height: 1;
                user-select: none;
            }
            #sidebar-toggle:hover {
                background: linear-gradient(
                    180deg,
                    rgba(100, 0, 0, 0.9) 0%,
                    rgba(80, 0, 0, 0.8) 100%
                );
                width: 20px;
            }
        """],
    )

    # Inject the sidebar toggle button via JS so it's a floating DOM element,
    # not part of the Panel layout flow.
    sidebar_toggle_js = """
    <script>
    (function() {
        function setup() {
            var sidebar = document.getElementById('sidebar');
            if (!sidebar) { setTimeout(setup, 200); return; }
            if (document.getElementById('sidebar-toggle')) return;

            var btn = document.createElement('div');
            btn.id = 'sidebar-toggle';
            btn.innerHTML = '&#9664;';
            document.body.appendChild(btn);

            function reposition() {
                var isHidden = sidebar.classList.contains('hidden');
                if (isHidden) {
                    btn.style.left = '0px';
                    btn.innerHTML = '&#9654;';
                } else {
                    btn.style.left = sidebar.offsetWidth + 'px';
                    btn.innerHTML = '&#9664;';
                }
            }

            reposition();

            btn.addEventListener('click', function() {
                var isHidden = sidebar.classList.contains('hidden');
                if (isHidden) {
                    if (typeof openNav === 'function') openNav();
                    else sidebar.classList.remove('hidden');
                } else {
                    if (typeof closeNav === 'function') closeNav();
                    else sidebar.classList.add('hidden');
                }
                setTimeout(reposition, 300);
            });

            new MutationObserver(function() {
                setTimeout(reposition, 50);
            }).observe(sidebar, { attributes: true, attributeFilter: ['class', 'style'] });
        }

        if (document.readyState === 'loading')
            document.addEventListener('DOMContentLoaded', setup);
        else
            setup();
    })();
    </script>
    """
    # Append to header row (horizontal) so it doesn't create vertical space in main
    header_row.append(pn.pane.HTML(
        sidebar_toggle_js, sizing_mode="fixed",
        width=0, height=0, margin=0,
    ))

    return template


create_app().servable()
