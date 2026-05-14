"""
UI callback logic for annotation management.

Contains the ``CallbackManager`` class that wires widget events to
state mutations + view updates, plus helper functions for creating
annotation rows and building summary HTML.
"""

import os
from datetime import datetime, timedelta

import pandas as pd
import bokeh.plotting as bp

from .config import (
    DISPLAYED_ANNOTATION_COLUMNS, TIME_FMT, WALKING_SUGGESTION_COLUMNS,
)
from .data_loading import save_annotations


def _row_to_segment(row):
    """Convert a walking-suggestions xlsx row to the in-memory segment dict."""
    return {
        "start_time": pd.to_datetime(row["start_time"]),
        "end_time": pd.to_datetime(row["end_time"]),
        "duration_s": float(row["duration_s"]),
        "mean_step_freq_hz": float(row["mean_step_freq_hz"]),
        "dismissed": bool(row.get("deleted", False)),
    }


def capture_new_annotation(start_ts, end_ts, artifact, fname, uname):
    """Create a single-row DataFrame representing a new annotation.

    Parameters
    ----------
    start_ts, end_ts : Timestamp
        Time bounds of the annotated segment.
    artifact : str
        Activity type (e.g. ``"chair_stand"``, ``"tug"``).
    fname : str
        Path to the signal file (basename is extracted).
    uname : str
        Username of the annotator.

    Returns
    -------
    DataFrame
        One-row DataFrame matching ``ANNOTATION_COLUMNS``.
    """
    pdf = pd.DataFrame(
        {
            "fname": os.path.basename(fname),
            "artifact": artifact,
            "segment": 0,
            "scoring": 0,
            "review": 0,
            "start_epoch": pd.to_datetime(start_ts).timestamp(),
            "end_epoch": pd.to_datetime(end_ts).timestamp(),
            "start_time": str(start_ts),
            "end_time": str(end_ts),
            "annotated_at": str(datetime.now()),
            "user": uname,
            "notes": "",
        },
        index=[0],
    )
    return pdf


def build_summary_html(state):
    """Build an HTML summary table for all annotations on the current file.

    Parameters
    ----------
    state : AppState
        Current session state.

    Returns
    -------
    str
        HTML string for the summary pane.
    """
    pdf_annotations = state.pdf_annotations
    fname = state.fname
    file_start = state.file_start_timestamp
    file_end = state.file_end_timestamp

    artifacts = ""
    notes = ""
    reviews = ""

    if pdf_annotations.shape[0] > 0:
        pdf_sel = pdf_annotations.loc[
            pdf_annotations["fname"] == os.path.basename(fname)
        ].reset_index(drop=True)

        if pdf_sel.shape[0] > 0:
            # Filter out rows with NaT timestamps (review-only flags)
            # before calling dt.strftime, which would raise on NaT.
            has_time = pdf_sel["start_time"].notna() & pdf_sel["end_time"].notna()
            pdf_timed = pdf_sel.loc[has_time].copy()

            if pdf_timed.shape[0] > 0:
                pdf_timed = pdf_timed.assign(
                    **{
                        col: pdf_timed[col].dt.strftime("%d-%m %H:%M:%S")
                        for col in ["start_time", "end_time"]
                    }
                )
                pdf_timed = pdf_timed.assign(
                    annotations_txt=pdf_timed.apply(
                        lambda x: f"{x['start_time']} - {x['end_time']} ({x['user']})",
                        axis=1,
                    ),
                    notes_txt=pdf_timed.apply(
                        lambda x: f"{x['notes']} ({x['user']})", axis=1
                    ),
                )

                dct_artifacts = {
                    artifact: "<br/>".join(
                        pdf_timed.loc[
                            (pdf_timed["artifact"] == artifact)
                            & (pdf_timed["scoring"] == 0)
                            & (pdf_timed["segment"] == 0)
                        ]["annotations_txt"].tolist()
                    )
                    for artifact in ["chair_stand", "6min_walk", "3m_walk", "tug"]
                }
                dct_artifacts = {k: v for k, v in dct_artifacts.items() if v}

                artifacts = (
                    "<table cellpadding='2'>"
                    + "<tr>"
                    + "".join(f"<td><b>{a}</b></td>" for a in dct_artifacts)
                    + "</tr><tr>"
                    + "".join(f"<td>{dct_artifacts[a]}</td>" for a in dct_artifacts)
                    + "</tr></table>"
                )
                notes = "<br/>".join(
                    pdf_timed.loc[pdf_timed["notes"].fillna("").str.strip() != ""][
                        "notes_txt"
                    ].tolist()
                )

            # Reviews can exist without time ranges, so use the full pdf_sel
            pdf_reviews = pdf_sel.loc[pdf_sel["review"] == 1].drop_duplicates(
                subset=["user", "artifact"]
            )
            if pdf_reviews.shape[0] > 0:
                pdf_reviews = (
                    pdf_reviews.groupby("artifact")["user"]
                    .apply(lambda x: ",".join(x))
                    .reset_index()
                )
                pdf_reviews = pdf_reviews.assign(
                    review_txt=pdf_reviews.apply(
                        lambda x: f"{x['artifact']} : {x['user']}", axis=1
                    ),
                )
                reviews = "<br/>".join(pdf_reviews["review_txt"].tolist())

    # Guard against None timestamps before first file load
    start_str = (
        pd.to_datetime(file_start).strftime("%d-%m-%Y %H:%M:%S")
        if file_start else "N/A"
    )
    end_str = (
        pd.to_datetime(file_end).strftime("%d-%m-%Y %H:%M:%S")
        if file_end else "N/A"
    )

    return f"""
    <table style="width:100%; border-collapse:collapse; font-size:12px;
     margin-top:8px; font-family:'Montserrat',Helvetica,Arial,sans-serif;">
    <tr style="background-color:#58595b;">
    <th style="padding:5px 10px; color:#fff; font-size:11px; text-align:left;">Start Time</th>
    <th style="padding:5px 10px; color:#fff; font-size:11px; text-align:left;">End Time</th>
    <th style="padding:5px 10px; color:#fff; font-size:11px; text-align:left;">Annotations</th>
    <th style="padding:5px 10px; color:#fff; font-size:11px; text-align:left;">Notes</th>
    <th style="padding:5px 10px; color:#fff; font-size:11px; text-align:left;">Reviews</th>
    </tr>
    <tr>
    <td style="padding:5px 10px; border-bottom:1px solid #e0e0e0; font-size:11px;">{start_str}</td>
    <td style="padding:5px 10px; border-bottom:1px solid #e0e0e0; font-size:11px;">{end_str}</td>
    <td style="padding:5px 10px; border-bottom:1px solid #e0e0e0; font-size:11px;">{artifacts}</td>
    <td style="padding:5px 10px; border-bottom:1px solid #e0e0e0; font-size:11px;">{notes}</td>
    <td style="padding:5px 10px; border-bottom:1px solid #e0e0e0; font-size:11px;">{reviews}</td>
    </tr>
    </table>
    """


def _filter_annotations_in_range(pdf_annotations, start_ts, end_ts, uname, fname):
    """Return a boolean mask of annotations within a time range for one user/file.

    Parameters
    ----------
    pdf_annotations : DataFrame
        Full annotations DataFrame.
    start_ts, end_ts : Timestamp
        Time bounds of the selection.
    uname : str
        Filter to this user.
    fname : str
        Filter to this file (basename is extracted).

    Returns
    -------
    Series[bool]
        Mask aligned with *pdf_annotations*.
    """
    annot_start = pd.to_datetime(pdf_annotations["start_time"], errors="coerce")
    annot_end = pd.to_datetime(pdf_annotations["end_time"], errors="coerce")
    mask = (
        annot_start.between(start_ts, end_ts, inclusive="both")
        & annot_end.between(start_ts, end_ts, inclusive="both")
        & (pdf_annotations["user"] == uname)
        & (pdf_annotations["fname"] == os.path.basename(fname))
    )
    return mask


class CallbackManager:
    """Orchestrates UI callbacks between widget events and AppState.

    Parameters
    ----------
    state : AppState
        Per-session state object.
    widgets : dict
        Name-to-widget mapping populated by ``app.py``.  Must include
        keys for all buttons, labels, and layout containers.
    """

    def __init__(self, state, widgets):
        self.state = state
        self.w = widgets

    # ------------------------------------------------------------------
    # Plot lifecycle
    # ------------------------------------------------------------------

    def _notify(self, msg, duration=3000, kind="info"):
        """Show a toast notification in the bottom-right corner."""
        import panel as pn
        getattr(pn.state.notifications, kind)(msg, duration=duration)

    def update_plot(self, force_rebuild=False, _empty_depth=0):
        """Load data for the current file/anchor and update the plot.

        When an existing plot exists and *force_rebuild* is False, only
        the CDS data and axis ranges are patched (much faster than a
        full figure rebuild).  Falls back to a full rebuild when no
        existing plot is available or when the fast path fails.

        If the file is empty or unreadable, shows a notification and
        advances to the next file in the dropdown.
        """
        self._notify("Building plot\u2026", duration=2000)
        basename = os.path.splitext(os.path.basename(self.state.fname))[0]
        # Find the file picker entry (e.g. "alan--060294-20221208125829")
        # which includes the assigned user prefix
        label = basename
        for entry in self.state.lst_fnames:
            if entry.endswith(basename):
                label = entry
                break
        self.w["file_label"].object = f"### Annotating: {label}"
        try:
            pdf = self.state.load_file_data()
        except Exception as ex:
            pdf = None
            print(f"Error loading file {self.state.fname}: {ex}")

        if pdf is None or len(pdf) == 0:
            self._handle_empty_file(_depth=_empty_depth)
            return

        # Fast path: update existing CDS + ranges without rebuilding
        if (
            not force_rebuild
            and self.state.signal_cds is not None
            and self.w.get("main_fig") is not None
        ):
            from .plotting import update_plot_data
            updated = update_plot_data(
                pdf,
                self.state.signal_cds,
                self.w["main_fig"],
                range_source=self.w.get("range_source"),
            )
            if updated:
                self.state.selection_bounds = None
                self.update_annotations()
                self._update_nav_buttons()
                return

        # Full rebuild (first load or fast path failed)
        self._refresh_plot(pdf)
        self.state.selection_bounds = None
        self.update_annotations()
        self._update_nav_buttons()

    def _handle_empty_file(self, _depth=0):
        """Show a notification and skip to the next non-empty file.

        Uses a depth counter to prevent unbounded recursion when
        consecutive files are all empty.
        """
        if _depth >= len(self.state.lst_fnames):
            self._notify("All files are empty or unreadable.", duration=5000)
            return

        basename = os.path.basename(self.state.fname)
        self._notify(
            f"File '{basename}' is empty or could not be loaded. Skipping to next file.",
            duration=5000,
        )
        # Find the next file in the dropdown list
        current_fnames = self.state.lst_fnames
        current_basename = basename
        # Find which entries match this file (ignoring user prefix)
        current_idx = None
        for i, fn in enumerate(current_fnames):
            parts = fn.split("--", 1)
            if len(parts) == 2 and parts[1] == os.path.splitext(current_basename)[0]:
                current_idx = i
                break

        if current_idx is not None and current_idx + 1 < len(current_fnames):
            next_fname = current_fnames[current_idx + 1]
        elif len(current_fnames) > 0:
            # Wrap around to the first file
            next_fname = current_fnames[0]
        else:
            return

        self.plot_new_file(next_fname, _empty_depth=_depth + 1)

    def _refresh_plot(self, pdf):
        """Rebuild Bokeh figures with new signal data.

        Swaps panes in the stable ``main_content`` Column by index so
        that the Panel layout reference stays valid across rebuilds.
        Re-wires the box-select callback on the new signal CDS.
        """
        from .plotting import make_plot
        main_pane, range_pane, main_fig, signal_cds, range_source = make_plot(
            pdf, self.state.annotation_cds
        )
        # Swap panes by index in the stable parent Column
        container = self.w["main_content"]
        container[self.w["main_plot_idx"]] = main_pane
        container[self.w["range_plot_idx"]] = range_pane
        self.w["main_plot"] = main_pane
        self.w["range_plot"] = range_pane
        self.w["main_fig"] = main_fig
        self.w["range_source"] = range_source
        self.state.signal_cds = signal_cds
        # Re-attach the selection callback to the new CDS
        if self.w.get("_selection_wire_fn"):
            signal_cds.selected.on_change("indices", self.w["_selection_wire_fn"])

    # ------------------------------------------------------------------
    # Annotation overlays (no plot rebuild — just CDS data updates)
    # ------------------------------------------------------------------

    def update_annotations(self):
        """Sync annotation overlay CDS data and refresh selection state."""
        self.state.update_annotation_sources()
        self.update_selection()

    def update_selection(self):
        """Update button states and selection tables based on current bounds.

        Enables/disables annotation buttons depending on whether a region
        is selected and whether existing annotations fall within it.
        """
        s = self.state
        w = self.w

        s.pdf_displayed_annotations = s.get_displayed_annotations()
        bounds = s.selection_bounds

        pdf_sel_data = pd.DataFrame(columns=["start_time", "end_time"])
        pdf_sel_annot = pd.DataFrame(columns=s.pdf_annotations.columns)

        has_selection = bounds is not None and s.username != "None"

        if has_selection:
            start_ts, end_ts = bounds
            # Enable annotation creation buttons
            w["btn_clear"].disabled = False
            w["btn_tug"].disabled = False
            w["btn_3m_walk"].disabled = False
            w["btn_6min_walk"].disabled = False
            w["btn_chairstand"].disabled = False

            pdf_sel_data = pd.DataFrame(
                {"start_time": str(start_ts), "end_time": str(end_ts)}, index=[0]
            )

            # Find existing annotations within the selected bounds
            disp_start = pd.to_datetime(s.pdf_displayed_annotations["start_time"], errors="coerce")
            disp_end = pd.to_datetime(s.pdf_displayed_annotations["end_time"], errors="coerce")
            pdf_sel_annot = s.pdf_displayed_annotations.loc[
                disp_start.between(start_ts, end_ts, inclusive="both")
                & disp_end.between(start_ts, end_ts, inclusive="both")
            ]
            # Convert datetimes to strings for Bokeh DataTable display
            pdf_sel_annot = pdf_sel_annot.assign(
                **{col: pdf_sel_annot[col].astype(str) for col in ["start_time", "end_time"]}
            )

            # Modification buttons only enabled when annotations exist in the selection
            has_annots = pdf_sel_annot.shape[0] > 0
            w["btn_remove"].disabled = not has_annots
            w["btn_segment"].disabled = not has_annots
            w["btn_scoring"].disabled = not has_annots
            w["btn_review"].disabled = not has_annots
            w["btn_notes"].disabled = not has_annots
            w["notes_input"].disabled = not has_annots
        else:
            for key in [
                "btn_clear", "btn_tug", "btn_3m_walk",
                "btn_6min_walk", "btn_chairstand", "btn_remove",
                "btn_segment", "btn_scoring", "btn_review",
                "btn_notes",
            ]:
                w[key].disabled = True
            w["notes_input"].disabled = True

        # Push data to the Bokeh DataTable sources
        s.selected_data.data = dict(bp.ColumnDataSource(pdf_sel_data).data)
        annot_cols = [c for c in DISPLAYED_ANNOTATION_COLUMNS if c in pdf_sel_annot.columns]
        if not annot_cols:
            pdf_sel_annot = pd.DataFrame(columns=DISPLAYED_ANNOTATION_COLUMNS)
        else:
            pdf_sel_annot = pdf_sel_annot[annot_cols]
        s.selected_annotations.data = dict(bp.ColumnDataSource(pdf_sel_annot).data)

    # ------------------------------------------------------------------
    # Annotation CRUD
    # ------------------------------------------------------------------

    def mark_annotation(self, artifact):
        """Add a new annotation for the selected time range."""
        s = self.state
        if s.selection_bounds:
            start_ts, end_ts = s.selection_bounds
            pdf_new = capture_new_annotation(
                start_ts, end_ts, artifact, s.fname, s.username
            )
            s.pdf_annotations = pd.concat(
                [s.pdf_annotations, pdf_new], ignore_index=True
            )
        self.update_annotations()

    def toggle_flag(self, flag_name):
        """Toggle a boolean flag (segment/scoring/review) on selected annotations.

        Parameters
        ----------
        flag_name : str
            Column name to toggle (``"segment"``, ``"scoring"``, or ``"review"``).
        """
        s = self.state
        if not s.selection_bounds:
            self.update_annotations()
            return

        start_ts, end_ts = s.selection_bounds
        mask = _filter_annotations_in_range(
            s.pdf_annotations, start_ts, end_ts, s.username, s.fname
        )
        selected = s.pdf_annotations.loc[mask].copy()
        s.pdf_annotations = s.pdf_annotations.loc[~mask]
        # Flip: 0→1, 1→0
        selected = selected.assign(
            **{flag_name: (selected[flag_name] != 1).astype(int)}
        )
        s.pdf_annotations = pd.concat(
            [s.pdf_annotations, selected], ignore_index=True
        )
        self.update_annotations()

    def remove_selected_annotations(self):
        """Delete all annotations within the current selection bounds."""
        s = self.state
        if s.selection_bounds:
            start_ts, end_ts = s.selection_bounds
            mask = _filter_annotations_in_range(
                s.pdf_annotations, start_ts, end_ts, s.username, s.fname
            )
            s.pdf_annotations = s.pdf_annotations.loc[~mask]
        self.update_annotations()

    def add_notes(self, notes_text=""):
        """Set notes text on all annotations within the selection."""
        s = self.state
        if not s.selection_bounds:
            self.update_annotations()
            return

        start_ts, end_ts = s.selection_bounds
        mask = _filter_annotations_in_range(
            s.pdf_annotations, start_ts, end_ts, s.username, s.fname
        )
        selected = s.pdf_annotations.loc[mask].reset_index(drop=True)
        s.pdf_annotations = s.pdf_annotations.loc[~mask]
        selected = selected.assign(notes=notes_text)
        s.pdf_annotations = pd.concat([s.pdf_annotations, selected], ignore_index=True)
        self.w["notes_input"].value = ""
        self.update_annotations()

    def save(self):
        """Persist annotations to disk and refresh the summary."""
        s = self.state
        s.pdf_annotations = save_annotations(
            s.pdf_annotations, s.username, s.fname
        )
        self.update_annotations()
        self.w["summary"].object = build_summary_html(s)
        self._notify("Annotations exported", duration=3000, kind="success")

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def plot_new_file(self, fname_with_user, _empty_depth=0):
        """Switch to a different file and update the plot.

        Parameters
        ----------
        fname_with_user : str
            ``"username--filename"`` string from the file picker.
        """
        self._notify("Loading file\u2026", duration=3000)
        s = self.state
        s.anchor_timestamp = None
        parts = fname_with_user.split("--", 1)
        s.fname = os.path.join(
            os.path.dirname(s.fname),
            parts[1] if len(parts) == 2 else parts[0],
        )
        # Walking suggestions are file-specific; load any persisted ones
        # for the new file so the user sees their prior detection state.
        # If no saved suggestions exist for this file, the list is empty.
        s.clear_walking_suggestions()
        self.load_persisted_walking_suggestions()
        self.update_plot(_empty_depth=_empty_depth)
        self.w["summary"].object = build_summary_html(s)

    def move_next_window(self):
        """Advance the anchor timestamp by one full window, clamped to file end."""
        s = self.state
        if not s.file_end_timestamp:
            return
        anchor_dt = datetime.strptime(s.anchor_timestamp, TIME_FMT)
        end_dt = datetime.strptime(s.file_end_timestamp, TIME_FMT)
        new_anchor = anchor_dt + timedelta(seconds=s.windowsize)
        # Don't advance past the point where the window would exceed file end
        if new_anchor > end_dt:
            new_anchor = end_dt - timedelta(seconds=s.windowsize / 2)
        if new_anchor <= anchor_dt:
            return
        s.anchor_timestamp = new_anchor.strftime(TIME_FMT)
        self.update_plot()

    def move_prev_window(self):
        """Move the anchor timestamp back by one full window, clamped to file start."""
        s = self.state
        if not s.file_start_timestamp:
            return
        anchor_dt = datetime.strptime(s.anchor_timestamp, TIME_FMT)
        start_dt = datetime.strptime(s.file_start_timestamp, TIME_FMT)
        new_anchor = anchor_dt - timedelta(seconds=s.windowsize)
        # Don't go before the point where the window would precede file start
        if new_anchor < start_dt:
            new_anchor = start_dt + timedelta(seconds=s.windowsize / 2)
        if new_anchor >= anchor_dt:
            return
        s.anchor_timestamp = new_anchor.strftime(TIME_FMT)
        self.update_plot()

    def _update_nav_buttons(self):
        """Enable or disable prev/next buttons based on file boundaries."""
        s = self.state
        if not s.file_start_timestamp or not s.file_end_timestamp or not s.anchor_timestamp:
            return
        anchor_dt = datetime.strptime(s.anchor_timestamp, TIME_FMT)
        start_dt = datetime.strptime(s.file_start_timestamp, TIME_FMT)
        end_dt = datetime.strptime(s.file_end_timestamp, TIME_FMT)
        half_win = timedelta(seconds=s.windowsize / 2)
        self.w["btn_prev"].disabled = (anchor_dt - half_win) <= start_dt
        self.w["btn_next"].disabled = (anchor_dt + half_win) >= end_dt

    def update_anchor_timestamp(self, value):
        """Parse and store a user-entered anchor time string.

        Parameters
        ----------
        value : str
            Time string in ``TIME_FMT``.
        """
        try:
            self.state.anchor_timestamp = datetime.strptime(
                value, TIME_FMT
            ).strftime(TIME_FMT)
        except Exception as ex:
            print(f"Invalid time entered: {value} ({ex})")

    def update_windowsize(self, value):
        """Parse and store a user-entered window size.

        Parameters
        ----------
        value : str
            Numeric string, optionally suffixed with ``"s"``.
        """
        try:
            self.state.windowsize = float(str(value).strip().replace("s", ""))
        except Exception as ex:
            print(f"Invalid windowsize: {value} ({ex})")

    def update_review_flags(self, new_reviews):
        """Sync file-level review flags with the multi-select widget.

        Review flags are annotation rows with ``review=1`` and no time
        range (``start_time`` is NaT).  This method diffs the widget
        state against the current review flags and adds/removes rows
        accordingly.

        Parameters
        ----------
        new_reviews : list of str
            Currently selected artifact types in the review widget.
        """
        s = self.state
        basename = os.path.basename(s.fname)

        # Get the current review-flag artifacts (rows without time ranges)
        current_reviews = s.pdf_annotations.loc[
            (s.pdf_annotations["user"] == s.username)
            & (s.pdf_annotations["fname"] == basename)
            & (s.pdf_annotations["review"] == 1)
            & (s.pdf_annotations["start_time"].isna())
        ]["artifact"].tolist()

        if set(new_reviews) != set(current_reviews):
            # Remove existing review-only rows for this user/file
            s.pdf_annotations = s.pdf_annotations.loc[
                ~(
                    (s.pdf_annotations["user"] == s.username)
                    & (s.pdf_annotations["fname"] == basename)
                    & (s.pdf_annotations["review"] == 1)
                    & (s.pdf_annotations["start_time"].isna())
                )
            ]
            # Add new review-flag rows (no time range)
            if new_reviews:
                new_rows = pd.DataFrame(
                    [
                        {
                            "fname": basename,
                            "artifact": artifact,
                            "segment": 0,
                            "scoring": 0,
                            "review": 1,
                            "annotated_at": str(datetime.now()),
                            "user": s.username,
                        }
                        for artifact in new_reviews
                    ]
                )
                s.pdf_annotations = pd.concat(
                    [s.pdf_annotations, new_rows], ignore_index=True
                ).reset_index(drop=True)
            s.get_displayed_annotations()

    # ------------------------------------------------------------------
    # Walking detection (Urbanek 2015 SHW)
    # ------------------------------------------------------------------

    def load_persisted_walking_suggestions(self):
        """Populate the in-memory suggestion list from the shared xlsx
        for the currently-loaded file.

        Loads *all* rows for this file, including dismissed ones — the
        UI displays dismissed entries as red rows so the user can toggle
        their state.  Only non-dismissed entries appear in the plot
        overlay CDS.

        Called on session start and after a file switch so that prior
        detection runs survive page refresh.
        """
        from .data_loading import load_walking_suggestions

        s = self.state
        try:
            saved = load_walking_suggestions()
        except Exception as ex:
            print(f"Walking suggestions: failed to load xlsx: {ex}")
            saved = None

        s.walking_suggestions = []
        s.walking_suggestion_idx = None

        if saved is not None and not saved.empty:
            basename = os.path.basename(s.fname)
            mine = saved.loc[saved["fname"] == basename]
            loaded = [_row_to_segment(row) for _, row in mine.iterrows()]
            s.walking_suggestions = loaded
            if loaded:
                # Land on the first non-dismissed if any, else the first row
                first_active = next(
                    (i for i, seg in enumerate(loaded) if not seg["dismissed"]),
                    0,
                )
                s.walking_suggestion_idx = first_active

        self._sync_walking_overlay_cds()
        self._update_walking_nav_state()

    def _sync_walking_overlay_cds(self):
        """Push only non-dismissed segments into the plot overlay CDS."""
        s = self.state
        active = [
            seg for seg in s.walking_suggestions if not seg["dismissed"]
        ]
        s.annotation_cds["walking_suggestion"].data = {
            "start_time": [seg["start_time"] for seg in active],
            "end_time": [seg["end_time"] for seg in active],
        }

    def detect_walking(self):
        """Run sustained-harmonic-walking detection on the entire file.

        Loads the whole HDF5 file (not just the visible window), scans
        it with the SHW algorithm, persists the result to the user's
        walking-suggestions xlsx, then populates the in-memory list and
        plot overlay with the non-deleted entries.  Dismissals from prior
        sessions for the same file are preserved by matching
        (start_epoch, end_epoch).
        """
        from .data_loading import (
            get_full_filedata, load_walking_suggestions, save_walking_suggestions,
        )
        from .walking_detection import detect_walking_segments

        s = self.state
        basename = os.path.basename(s.fname)
        self._notify("Scanning file for walking segments…", duration=4000)
        try:
            pdf_full = get_full_filedata(s.fname)
        except Exception as ex:
            print(f"Walking detect: failed to load {s.fname}: {ex}")
            self._notify("Could not load file for detection.", duration=3000, kind="error")
            return

        segments = detect_walking_segments(pdf_full)

        # Preserve prior dismissals for this file
        existing = load_walking_suggestions()
        deleted_keys = set()
        if not existing.empty:
            this_file = existing.loc[existing["fname"] == basename]
            for _, row in this_file.iterrows():
                if bool(row.get("deleted", False)):
                    deleted_keys.add(
                        (float(row["start_epoch"]), float(row["end_epoch"]))
                    )

        # Build fresh rows for this file, marking previously-dismissed ones
        detected_at = str(pd.Timestamp.now())
        new_rows = []
        for seg in segments:
            start_epoch = pd.to_datetime(seg["start_time"]).timestamp()
            end_epoch = pd.to_datetime(seg["end_time"]).timestamp()
            new_rows.append(
                {
                    "fname": basename,
                    "start_time": str(seg["start_time"]),
                    "end_time": str(seg["end_time"]),
                    "start_epoch": start_epoch,
                    "end_epoch": end_epoch,
                    "duration_s": seg["duration_s"],
                    "mean_step_freq_hz": seg["mean_step_freq_hz"],
                    "detected_at": detected_at,
                    "deleted": (start_epoch, end_epoch) in deleted_keys,
                }
            )

        # Replace just this file's rows; keep rows for other files intact
        other_rows = (
            existing.loc[existing["fname"] != basename]
            if not existing.empty else existing
        )
        merged = pd.concat(
            [other_rows, pd.DataFrame(new_rows, columns=WALKING_SUGGESTION_COLUMNS)],
            ignore_index=True,
        )
        save_walking_suggestions(merged)

        # In-memory list: store all segments (including dismissed) so the
        # UI can render dismissed ones as red rows that can be toggled.
        in_memory = []
        for seg, row in zip(segments, new_rows):
            in_memory.append(
                {
                    "start_time": seg["start_time"],
                    "end_time": seg["end_time"],
                    "duration_s": seg["duration_s"],
                    "mean_step_freq_hz": seg["mean_step_freq_hz"],
                    "dismissed": bool(row["deleted"]),
                }
            )
        s.walking_suggestions = in_memory
        # Land on the first non-dismissed entry, or 0 if everything's dismissed
        if in_memory:
            s.walking_suggestion_idx = next(
                (i for i, seg in enumerate(in_memory) if not seg["dismissed"]),
                0,
            )
        else:
            s.walking_suggestion_idx = None

        self._sync_walking_overlay_cds()
        self._update_walking_nav_state()

        dismissed_count = sum(1 for seg in in_memory if seg["dismissed"])
        active_count = len(in_memory) - dismissed_count
        if not in_memory:
            self._notify("No sustained walking detected.", duration=3000)
            return

        if active_count == 0:
            self._notify(
                f"All {len(in_memory)} detected segments are dismissed.",
                duration=3000,
            )
            return

        suffix = "s" if active_count != 1 else ""
        dismissed_note = (
            f" ({dismissed_count} dismissed)" if dismissed_count else ""
        )
        self._notify(
            f"Found {active_count} walking segment{suffix}{dismissed_note}.",
            duration=3000,
        )
        # Jump to the first non-dismissed candidate so the user sees one in context
        self._navigate_to_current_walking()

    def jump_to_walking_suggestion(self, idx):
        """Jump directly to the i-th walking candidate (from the list click)."""
        s = self.state
        if not s.walking_suggestions:
            return
        if idx < 0 or idx >= len(s.walking_suggestions):
            return
        s.walking_suggestion_idx = idx
        self._navigate_to_current_walking()
        self._update_walking_nav_state()

    def toggle_walking_dismissed(self, idx):
        """Flip the ``dismissed`` flag on a single walking candidate.

        Dismissed segments stay in the list (rendered red) so the user
        can reinstate them with another click on the ✕.  The plot
        overlay shows only non-dismissed segments.  Change is persisted
        immediately to the shared walking-suggestions xlsx.
        """
        from .data_loading import (
            load_walking_suggestions, save_walking_suggestions,
        )

        s = self.state
        if not s.walking_suggestions:
            return
        if idx < 0 or idx >= len(s.walking_suggestions):
            return

        seg = s.walking_suggestions[idx]
        new_state = not seg["dismissed"]
        seg["dismissed"] = new_state

        # Refresh the plot overlay so the dismissed segment disappears
        # (or reappears) from the orange dashed boxes
        self._sync_walking_overlay_cds()

        # Persist via (fname, start_epoch, end_epoch) match — exact across
        # the Excel round-trip because epoch is stored as a float.
        try:
            existing = load_walking_suggestions()
            if not existing.empty:
                basename = os.path.basename(s.fname)
                start_epoch = pd.to_datetime(seg["start_time"]).timestamp()
                end_epoch = pd.to_datetime(seg["end_time"]).timestamp()
                mask = (
                    (existing["fname"] == basename)
                    & (existing["start_epoch"].astype(float) == start_epoch)
                    & (existing["end_epoch"].astype(float) == end_epoch)
                )
                if mask.any():
                    existing.loc[mask, "deleted"] = new_state
                    save_walking_suggestions(existing)
        except Exception as ex:
            print(f"Walking toggle: failed to persist deleted flag: {ex}")

        self._update_walking_nav_state()

    def clear_walking_suggestions(self):
        """Discard the current candidate list and clear the overlay."""
        self.state.clear_walking_suggestions()
        self._update_walking_nav_state()

    def _navigate_to_current_walking(self):
        """Recenter the time window on the active walking candidate."""
        s = self.state
        if s.walking_suggestion_idx is None:
            return
        seg = s.walking_suggestions[s.walking_suggestion_idx]
        # Center the window on the candidate's midpoint so the annotator
        # sees context on both sides.  Keeps the current windowsize —
        # the user can zoom independently if they want a tighter view.
        midpoint = seg["start_time"] + (seg["end_time"] - seg["start_time"]) / 2
        s.anchor_timestamp = midpoint.strftime(TIME_FMT)
        self.w["time_input"].value = s.anchor_timestamp
        self.update_plot()

    def _update_walking_nav_state(self):
        """Refresh the walking-detection status pane and button states."""
        s = self.state
        segs = s.walking_suggestions
        idx = s.walking_suggestion_idx

        # Status text
        if not segs:
            html = (
                "<div style='font-size:11px;color:#666;padding:4px 0;'>"
                "No walking suggestions yet.</div>"
            )
        else:
            seg = segs[idx]
            dismissed_count = sum(1 for x in segs if x.get("dismissed", False))
            tail = (
                f" &middot; <span style='color:#c62828;'>{dismissed_count} "
                f"dismissed</span>" if dismissed_count else ""
            )
            current_note = (
                " <span style='color:#c62828;'>(dismissed)</span>"
                if seg.get("dismissed", False) else ""
            )
            html = (
                f"<div style='font-size:11px;padding:4px 0;'>"
                f"<b>{idx + 1} / {len(segs)}</b>"
                f"{tail}<br>"
                f"{seg['duration_s']:.0f}s &middot; "
                f"{seg['mean_step_freq_hz']:.2f} Hz{current_note}"
                f"</div>"
            )
        if "walking_status" in self.w:
            self.w["walking_status"].object = html

        # Clear button: disabled when nothing to clear
        if "btn_clear_walking" in self.w:
            self.w["btn_clear_walking"].disabled = not segs

        # Scrollable click-to-jump list
        if "walking_list_col" in self.w:
            self._populate_walking_list()

    def _populate_walking_list(self):
        """Rebuild the click-to-jump button list of detected segments.

        Each row is a (jump_button, ✕_button) pair.  The ✕ toggles the
        segment's ``dismissed`` state; dismissed rows are rendered with
        a red, struck-through label.  The wide jump button still
        navigates regardless of dismissed state, so users can review a
        dismissed segment without reinstating it.
        """
        import panel as pn

        col = self.w["walking_list_col"]
        segs = self.state.walking_suggestions
        active_idx = self.state.walking_suggestion_idx
        if not segs:
            col.objects = []
            return

        jump_css_active = [
            ":host { font-size: 10px; flex: 1 1 auto !important; }"
            "button { text-align: left !important; padding: 2px 6px !important; "
            "white-space: nowrap !important; overflow: hidden !important; "
            "text-overflow: ellipsis !important; }"
        ]
        # Dismissed rows: muted background, red strike-through text.
        jump_css_dismissed = [
            ":host { font-size: 10px; flex: 1 1 auto !important; }"
            "button { text-align: left !important; padding: 2px 6px !important; "
            "white-space: nowrap !important; overflow: hidden !important; "
            "text-overflow: ellipsis !important; "
            "color: #c62828 !important; text-decoration: line-through !important; "
            "background: #fce4ec !important; border-color: #f4c2c2 !important; }"
        ]
        toggle_css = [
            ":host { font-size: 10px; flex: 0 0 24px !important; }"
            "button { padding: 2px 4px !important; color: #888 !important; }"
        ]

        rows = []
        for i, seg in enumerate(segs):
            label = (
                f"{seg['start_time'].strftime('%b %d %H:%M:%S')} "
                f"· {seg['duration_s']:.0f}s · {seg['mean_step_freq_hz']:.2f} Hz"
            )
            is_active = i == active_idx
            is_dismissed = bool(seg.get("dismissed", False))
            if is_dismissed:
                btn_type = "light"
                css = jump_css_dismissed
            else:
                btn_type = "success" if is_active else "light"
                css = jump_css_active

            jump_btn = pn.widgets.Button(
                name=label, button_type=btn_type, margin=(1, 0), stylesheets=css,
            )
            jump_btn.on_click(lambda e, idx=i: self.jump_to_walking_suggestion(idx))

            toggle_btn = pn.widgets.Button(
                name="✕", button_type="light", width=24,
                margin=(1, 0), stylesheets=toggle_css,
            )
            toggle_btn.on_click(lambda e, idx=i: self.toggle_walking_dismissed(idx))

            rows.append(
                pn.Row(jump_btn, toggle_btn, sizing_mode="stretch_width", margin=(0, 0))
            )
        col.objects = rows
