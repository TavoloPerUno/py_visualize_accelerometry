import os
from datetime import datetime, timedelta

import pandas as pd
import bokeh.plotting as bp

from .config import ANNOTATIONS_GLOB, DISPLAYED_ANNOTATION_COLUMNS, TIME_FMT
from .data_loading import cleanup_annotations, get_annotations_from_files, save_annotations


def capture_new_annotation(colsource, selected_indices, artifact, fname, uname):
    """Create a new annotation DataFrame row from the selected time range."""
    min_index = min(selected_indices)
    max_index = max(selected_indices)
    pdf = pd.DataFrame(
        {
            "fname": os.path.basename(fname),
            "artifact": artifact,
            "segment": 0,
            "scoring": 0,
            "review": 0,
            "start_epoch": colsource.data["timestamp"][min_index],
            "end_epoch": colsource.data["timestamp"][max_index],
            "start_time": colsource.data["timestamp"][min_index],
            "end_time": colsource.data["timestamp"][max_index],
            "annotated_at": datetime.now(),
            "user": uname,
            "notes": "",
        },
        index=[0],
    )
    pdf = pdf.assign(
        **{
            col: (pdf[col] - datetime(1970, 1, 1)).dt.total_seconds()
            for col in ["start_epoch", "end_epoch"]
        },
        **{
            col: pdf[col].astype(str)
            for col in ["start_time", "end_time", "annotated_at"]
        },
    )
    return pdf


def build_summary_html(state):
    """Build the summary HTML table for the current file."""
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
            pdf_sel = pdf_sel.assign(
                **{
                    col: pdf_sel[col].dt.strftime("%d-%m %H:%M:%S")
                    for col in ["start_time", "end_time"]
                }
            )
            pdf_sel = pdf_sel.assign(
                annotations_txt=pdf_sel.apply(
                    lambda x: f"{x['start_time']} - {x['end_time']} ({x['user']})",
                    axis=1,
                ),
                notes_txt=pdf_sel.apply(
                    lambda x: f"{x['notes']} ({x['user']})", axis=1
                ),
            )
            pdf_reviews = pdf_sel.loc[pdf_sel["review"] == 1].drop_duplicates(
                subset=["user", "artifact"]
            )
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

            dct_artifacts = {
                artifact: "<br/>".join(
                    pdf_sel.loc[
                        (pdf_sel["artifact"] == artifact)
                        & (pdf_sel["scoring"] == 0)
                        & (pdf_sel["segment"] == 0)
                        & (~pdf_sel["start_time"].isna())
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
                pdf_sel.loc[pdf_sel["notes"].fillna("").str.strip() != ""][
                    "notes_txt"
                ].tolist()
            )
            reviews = "<br/>".join(pdf_reviews["review_txt"].tolist())

    return f"""
    <br/>
    <table cellpadding='2'>
    <tr>
    <td><b>Start Time</b></td>
    <td><b>End Time</b></td>
    <td><b>Annotations</b></td>
    <td><b>Notes</b></td>
    <td><b>Reviews</b></td>
    </tr>
    <tr>
    <td>{pd.to_datetime(file_start).strftime('%d-%m-%Y %H:%M:%S')}</td>
    <td>{pd.to_datetime(file_end).strftime('%d-%m-%Y %H:%M:%S')}</td>
    <td>{artifacts}</td>
    <td>{notes}</td>
    <td>{reviews}</td>
    </tr>
    </table>
    """


def _get_selected_range(state):
    """Return (min_index, max_index) from current selection, or None."""
    indices = state.colsource.selected.indices
    if not indices:
        return None
    return min(indices), max(indices)


def _filter_annotations_in_range(pdf_annotations, colsource, min_idx, max_idx, uname, fname):
    """Filter annotations that fall within the selected time range for a given user/file."""
    start_ts = colsource.data["timestamp"][min_idx]
    end_ts = colsource.data["timestamp"][max_idx]
    mask = (
        pd.to_datetime(
            pd.to_numeric(pdf_annotations["start_epoch"], errors="coerce"),
            unit="s", errors="coerce",
        ).between(start_ts, end_ts, inclusive="both")
        & pd.to_datetime(
            pd.to_numeric(pdf_annotations["end_epoch"], errors="coerce"),
            unit="s", errors="coerce",
        ).between(start_ts, end_ts, inclusive="both")
        & (pdf_annotations["user"] == uname)
        & (pdf_annotations["fname"] == os.path.basename(fname))
    )
    return mask


class CallbackManager:
    """Manages all UI callbacks bound to a specific AppState + widget set."""

    def __init__(self, state, widgets):
        self.state = state
        self.w = widgets  # dict of widget references

    def update_plot(self):
        self.w["plot"].title.text = os.path.basename(self.state.fname)
        new_srs, new_colsource = self.state.load_file_data()
        self.state.colsource.data.update(new_colsource.data)
        self.w["plot"].x_range.update(start=new_srs[400])
        self.w["plot"].x_range.update(end=new_srs[min(3000, len(new_srs) - 1)])
        self.state.colsource.selected.indices = []
        self.update_annotations()

    def update_annotations(self):
        self.state.update_annotation_sources()
        self.update_selection()

    def update_selection(self):
        s = self.state
        w = self.w

        s.pdf_displayed_annotations = s.get_displayed_annotations()
        selected_indices = s.colsource.selected.indices

        pdf_sel_data = pd.DataFrame(columns=["start_time", "end_time"])
        pdf_sel_annot = pd.DataFrame(columns=s.pdf_annotations.columns)

        has_selection = bool(selected_indices) and s.username != "None"

        if has_selection:
            w["btn_clear"].disabled = False
            w["btn_tug"].disabled = False
            w["btn_3m_walk"].disabled = False
            w["btn_6min_walk"].disabled = False
            w["btn_chairstand"].disabled = False

            min_idx = min(selected_indices)
            max_idx = max(selected_indices)

            start = pd.to_datetime(str(s.colsource.data["timestamp"][min_idx]))
            end = pd.to_datetime(str(s.colsource.data["timestamp"][max_idx]))

            pdf_sel_data = pd.DataFrame(
                {"start_time": str(start), "end_time": str(end)}, index=[0]
            )

            pdf_sel_annot = s.pdf_displayed_annotations.loc[
                pd.to_datetime(
                    pd.to_numeric(s.pdf_displayed_annotations["start_time"], errors="coerce"),
                    errors="coerce",
                ).between(start, end, inclusive="both")
                & pd.to_datetime(
                    pd.to_numeric(s.pdf_displayed_annotations["end_time"], errors="coerce"),
                    errors="coerce",
                ).between(start, end, inclusive="both")
            ]
            pdf_sel_annot = pdf_sel_annot.assign(
                **{col: pdf_sel_annot[col].astype(str) for col in ["start_time", "end_time"]}
            )

            has_annots = pdf_sel_annot.shape[0] > 0
            w["btn_remove"].disabled = not has_annots
            w["btn_segment"].disabled = not has_annots
            w["btn_scoring"].disabled = not has_annots
            w["btn_review"].disabled = not has_annots
            w["btn_notes"].disabled = not has_annots
        else:
            for key in ["btn_clear", "btn_tug", "btn_3m_walk", "btn_6min_walk",
                         "btn_chairstand", "btn_remove", "btn_segment",
                         "btn_scoring", "btn_review", "btn_notes"]:
                w[key].disabled = True

        s.selected_data.data.update(bp.ColumnDataSource(pdf_sel_data).data)
        annot_cols = [c for c in DISPLAYED_ANNOTATION_COLUMNS if c in pdf_sel_annot.columns]
        if not annot_cols:
            pdf_sel_annot = pd.DataFrame(columns=DISPLAYED_ANNOTATION_COLUMNS)
        else:
            pdf_sel_annot = pdf_sel_annot[annot_cols]
        s.selected_annotations.data.update(bp.ColumnDataSource(pdf_sel_annot).data)

    def mark_annotation(self, artifact):
        s = self.state
        indices = s.colsource.selected.indices
        if indices:
            pdf_new = capture_new_annotation(
                s.colsource, indices, artifact, s.fname, s.username
            )
            s.pdf_annotations = pd.concat(
                [s.pdf_annotations, pdf_new], ignore_index=True
            )
        self.update_annotations()

    def toggle_flag(self, flag_name):
        """Toggle segment/scoring/review flag on selected annotations."""
        s = self.state
        rng = _get_selected_range(s)
        if not rng:
            self.update_annotations()
            return

        min_idx, max_idx = rng
        mask = _filter_annotations_in_range(
            s.pdf_annotations, s.colsource, min_idx, max_idx,
            s.username, s.fname
        )
        selected = s.pdf_annotations.loc[mask].copy()
        s.pdf_annotations = s.pdf_annotations.loc[~mask]
        selected = selected.assign(
            **{flag_name: (selected[flag_name] != 1).astype(int)}
        )
        s.pdf_annotations = pd.concat(
            [s.pdf_annotations, selected], ignore_index=True
        )
        self.update_annotations()

    def remove_selected_annotations(self):
        s = self.state
        rng = _get_selected_range(s)
        if rng:
            min_idx, max_idx = rng
            mask = _filter_annotations_in_range(
                s.pdf_annotations, s.colsource, min_idx, max_idx,
                s.username, s.fname
            )
            s.pdf_annotations = s.pdf_annotations.loc[~mask]
        self.update_annotations()

    def add_notes(self):
        s = self.state
        rng = _get_selected_range(s)
        if not rng:
            self.update_annotations()
            return

        min_idx, max_idx = rng
        pdf_notes = (
            pd.DataFrame(s.selected_annotations.data)
            .drop(columns=["index"], errors="ignore")
            .reset_index(drop=True)
        )
        mask = _filter_annotations_in_range(
            s.pdf_annotations, s.colsource, min_idx, max_idx,
            s.username, s.fname
        )
        selected = s.pdf_annotations.loc[mask].reset_index(drop=True)
        s.pdf_annotations = s.pdf_annotations.loc[~mask]
        selected = selected.assign(notes=pdf_notes["notes"])
        s.pdf_annotations = pd.concat([s.pdf_annotations, selected])
        self.update_annotations()

    def save(self):
        s = self.state
        s.pdf_annotations = save_annotations(
            s.pdf_annotations, s.username, s.fname
        )
        self.update_annotations()
        self.w["summary"].text = build_summary_html(s)

    def plot_new_file(self, fname_with_user):
        s = self.state
        s.anchor_timestamp = None
        s.fname = os.path.join(
            os.path.dirname(s.fname),
            fname_with_user.split("--")[1],
        )
        self.update_plot()
        self.w["summary"].text = build_summary_html(s)

    def move_next_window(self):
        s = self.state
        s.anchor_timestamp = (
            datetime.strptime(s.anchor_timestamp, TIME_FMT)
            + timedelta(seconds=s.windowsize)
        ).strftime(TIME_FMT)
        self.update_plot()

    def move_prev_window(self):
        s = self.state
        s.anchor_timestamp = (
            datetime.strptime(s.anchor_timestamp, TIME_FMT)
            - timedelta(seconds=s.windowsize)
        ).strftime(TIME_FMT)
        self.update_plot()

    def update_anchor_timestamp(self, value):
        try:
            self.state.anchor_timestamp = (
                datetime.strptime(value, TIME_FMT) + timedelta(seconds=0)
            ).strftime(TIME_FMT)
        except Exception as ex:
            print(f"Invalid time entered: {value} ({ex})")

    def update_windowsize(self, value):
        try:
            self.state.windowsize = float(str(value).strip().replace("s", ""))
        except Exception as ex:
            print(f"Invalid windowsize: {value} ({ex})")

    def update_review_flags(self, new_reviews):
        s = self.state
        basename = os.path.basename(s.fname)
        current = s.pdf_annotations.loc[
            (s.pdf_annotations["user"] == s.username)
            & (s.pdf_annotations["fname"] == basename)
        ].artifact.tolist()

        if set(new_reviews) != set(current):
            s.pdf_annotations = s.pdf_annotations.loc[
                ~(
                    (s.pdf_annotations["user"] == s.username)
                    & (s.pdf_annotations["fname"] == basename)
                    & (s.pdf_annotations["review"] == 1)
                    & (s.pdf_annotations["start_time"].isna())
                )
            ]
            if new_reviews:
                new_rows = pd.DataFrame(
                    [
                        {
                            "fname": basename,
                            "artifact": artifact,
                            "segment": 0,
                            "scoring": 0,
                            "review": 1,
                            "annotated_at": datetime.now(),
                            "user": s.username,
                        }
                        for artifact in new_reviews
                    ]
                )
                s.pdf_annotations = pd.concat(
                    [s.pdf_annotations, new_rows], ignore_index=True
                ).reset_index(drop=True)
            s.get_displayed_annotations()
