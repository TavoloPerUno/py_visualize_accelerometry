import glob
import pandas as pd
import os
import numpy as np
from datetime import datetime, timedelta

from bokeh.layouts import grid, row
from bokeh.models import (
    TextInput,
    Div,
    ColumnDataSource,
    RangeTool,
    Select,
    DatetimeTickFormatter,
)
from bokeh.models.widgets import DataTable, TableColumn
import bokeh.plotting as bp
from bokeh.plotting import figure, curdoc
from bokeh.models.widgets import Button, MultiSelect
from bokeh.layouts import column

# Constants
lst_colors = ["red", "blue", "green", "yellow", "violet"]
data_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
readings_folder = os.path.join(data_folder, "readings")
output_folder = os.path.join(data_folder, "output")
annotations_fname = os.path.join(output_folder, "annotations_*.xlsx")
lst_users = ['None'] + list(sorted(["megan", "victor", "chahak", "alena"]))


# Intial data loaders
def get_filenames():
    global lst_users
    np.random.seed(2020)
    lst_files = sorted(
        [
            np.random.choice([user for user in lst_users if user != 'None']) + "--" + os.path.splitext(f)[0]
            for f in os.listdir(readings_folder)
            if os.path.splitext(f)[1].lower() == ".h5"
        ]
    )
    return lst_files


def get_filedata():
    """This function accepts a filename as input and returns the passed file's timestamp index & ColumnDataSource
    version of the file data
      :param fname str: signal filename
      :return: numpy.ndarray, bokeh.models.ColumnDataSource
    """
    global pdf_signal_to_display
    global fname
    global anchor_timestamp
    global file_start_timestamp
    global file_end_timestamp
    global lst_columns
    global windowsize
    if anchor_timestamp is None:
        print("Loading {0}".format(fname))
        windowsize = 3600
        windowsize_input.value = str(windowsize)
        anchor_timestamp = (
            pd.read_hdf(fname + ".h5", "readings", start=0, stop=1)["timestamp"]
            .dt.strftime("%b %d %Y %I:%M %p")
            .values[0]
        )
        file_start_timestamp = (
            pd.read_hdf(fname + ".h5", "readings", start=0, stop=1)["timestamp"]
            .dt.strftime("%b %d %Y %I:%M %p")
            .values[0]
        )
        file_end_timestamp = (
            pd.read_hdf(fname + ".h5", "readings", start=-1)["timestamp"]
            .dt.strftime("%b %d %Y %I:%M %p")
            .values[0]
        )
        print(f"File starts at {file_start_timestamp} and ends at {file_end_timestamp}")
        update_summary()

    if datetime.strptime(anchor_timestamp, "%b %d %Y %I:%M %p") >= datetime.strptime(
        file_end_timestamp, "%b %d %Y %I:%M %p"
    ):
        print(
            f"Anchor timestamp {anchor_timestamp} is invalid; file ends at {file_end_timestamp}"
        )
        anchor_timestamp = (
            datetime.strptime(file_end_timestamp, "%b %d %Y %I:%M %p")
            - timedelta(seconds=int(windowsize / 2))
        ).strftime("%b %d %Y %I:%M %p")
    if datetime.strptime(anchor_timestamp, "%b %d %Y %I:%M %p") <= datetime.strptime(
        file_start_timestamp, "%b %d %Y %I:%M %p"
    ):
        print(
            f"Anchor timestamp {anchor_timestamp} is invalid; file starts at {file_start_timestamp}"
        )
        anchor_timestamp = (
            datetime.strptime(file_start_timestamp, "%b %d %Y %I:%M %p")
            + timedelta(seconds=int(windowsize / 2))
        ).strftime("%b %d %Y %I:%M %p")
    time_input.value = anchor_timestamp
    print(
        "Loading a {0} minute window centered around {1} from {2}".format(
            int(windowsize / 60), anchor_timestamp, fname
        )
    )
    start_timestamp = (
        datetime.strptime(anchor_timestamp, "%b %d %Y %I:%M %p")
        - timedelta(seconds=int(windowsize / 2))
    ).strftime("%b %d %Y %I:%M %p")
    end_timestamp = (
        datetime.strptime(anchor_timestamp, "%b %d %Y %I:%M %p")
        + timedelta(seconds=int(windowsize / 2))
    ).strftime("%b %d %Y %I:%M %p")
    pdf_signal_to_display = pd.read_hdf(
        fname + ".h5",
        "readings",
        where="(timestamp >= Timestamp('{0}')) & (timestamp <= Timestamp('{1}'))".format(
            start_timestamp, end_timestamp
        ),
    )
    return None


def update_datasources():
    get_filedata()
    global pdf_signal_to_display

    # print("Column datatypes:")
    # print(pdf_signal_to_display.head().dtypes)
    # print("Anchor timestamp (str): {0}".format(anchor_timestamp))
    # print("Anchor timestamp : {0}".format(
    # 	(datetime.strptime(time_input.value, '%b %d %Y %I:%M %p') - datetime(1970, 1, 1)).total_seconds()))
    # print("N rows:{0}".format(pdf_signal_to_display.shape[0]))
    dates = pdf_signal_to_display["timestamp"].values
    source = bp.ColumnDataSource(pdf_signal_to_display)

    return dates, source


def make_plot(
    srs,
    colsource,
    data_annot_chairstand,
    data_annot_3m_walk,
    data_annot_6min_walk,
    data_annot_tug,
    title,
):
    tools = "box_select"
    p = figure(
        height=300,
        tools=tools,
        toolbar_location="left",
        x_axis_type="datetime",
        x_axis_location="above",
        background_fill_color="#efefef",
        x_range=(srs[400], srs[3000]),
        title=title,
        sizing_mode="stretch_width",
        output_backend="webgl",
    )
    p.xaxis.axis_label = "Timestamp"

    lst_col = ["x", "y", "z"]
    lst_line_plots = []
    for (colr, leg) in zip(lst_colors, lst_col):
        lst_line_plots.append(
            p.line(
                "timestamp",
                leg,
                color=colr,
                legend_label=leg,
                source=colsource,
                name="wave",
                nonselection_alpha=0.2,
                selection_alpha=1,
            )
        )
        p.scatter(
            "timestamp",
            leg,
            color=None,
            legend_label=leg,
            source=colsource,
            name="wave",
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
    p.xaxis.minor_tick_line_color = "black"

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

    for (colr, leg) in zip(lst_colors, lst_col):
        select.line(
            "timestamp",
            leg,
            color=colr,
            source=colsource,
            nonselection_alpha=0.4,
            selection_alpha=1,
        )

    select.xaxis.formatter = DatetimeTickFormatter(
        days=["%m/%d %H:%M"],
        months=["%m/%d %H:%M"],
        hours=["%m/%d %H:%M"],
        minutes=["%m/%d %H:%M"],
        seconds=["%m/%d %H:%M:%S"],
        milliseconds=["%m/%d %H:%M:%Ss:%3Nms"],
    )

    # annot_chairstand = Quad()
    p.quad(
        left="start_time",
        right="end_time",
        top=4,
        bottom=-4,
        fill_color="cyan",
        fill_alpha=0.2,
        source=data_annot_chairstand,
        legend_label="chairstand",
    )
    p.quad(
        left="start_time",
        right="end_time",
        top=4,
        bottom=-4,
        fill_color="magenta",
        fill_alpha=0.2,
        source=data_annot_3m_walk,
        legend_label="3m_walk",
    )
    p.quad(
        left="start_time",
        right="end_time",
        top=4,
        bottom=-4,
        fill_color="green",
        fill_alpha=0.2,
        source=data_annot_6min_walk,
        legend_label="6min_walk",
    )
    p.quad(
        left="start_time",
        right="end_time",
        top=4,
        bottom=-4,
        fill_color="yellow",
        fill_alpha=0.2,
        source=data_annot_tug,
        legend_label="tug",
    )
    p.quad(
        left="start_time",
        right="end_time",
        top=4,
        bottom=-4,
        fill_color=None,
        fill_alpha=0,
        source=data_annot_segment,
        legend_label="segment",
        hatch_pattern="cross",
        hatch_color="black",
        hatch_weight=0.5,
        hatch_alpha=0.1,
    )
    p.quad(
        left="start_time",
        right="end_time",
        top=4,
        bottom=-4,
        fill_color=None,
        fill_alpha=0,
        source=data_annot_scoring,
        legend_label="scoring",
        hatch_pattern="dot",
        hatch_color="black",
        hatch_weight=0.5,
        hatch_alpha=0.1,
    )
    p.quad(
        left="start_time",
        right="end_time",
        top=4,
        bottom=-4,
        fill_color=None,
        fill_alpha=0,
        source=data_annot_review,
        legend_label="review",
        hatch_pattern="spiral",
        hatch_color="black",
        hatch_weight=0.5,
        hatch_alpha=0.1,
    )

    p.legend.background_fill_alpha = 0.0
    p.legend.label_text_font_size = "7pt"
    return p, select


# Util functions
def cleanup_annotations(pdf):
    pdf = pdf.sort_values(
        by=[
            "user",
            "fname",
            "artifact",
            "segment",
            "scoring",
            "review",
            "annotated_at",
        ],
        ascending=False,
    )
    if pdf.shape[0] > 0:
        if "notes" not in pdf.columns:
            pdf = pdf.assign(notes="")
        pdf = pdf.assign(
            start_time=pd.to_datetime(pdf["start_time"], errors="coerce"),
            end_time=pd.to_datetime(pdf["end_time"], errors="coerce"),
            notes=pdf["notes"].fillna(""),
        )
    pdf = pdf.assign(notes=pdf["notes"].astype(str))
    return pdf


def update_summary():
    global pdf_annotations
    global fname
    global uname
    global file_start_timestamp
    global file_end_timestamp
    global summary
    artifacts = ''
    notes = ''
    reviews = ''
    if pdf_annotations.shape[0] > 0:
        pdf_selected = pdf_annotations.loc[
            (pdf_annotations["fname"] == os.path.basename(fname))
        ].reset_index(drop=True)
        if pdf_selected.shape[0] > 0:
            pdf_selected = pdf_selected.assign(
                **{col: pdf_selected[col].dt.strftime("%d-%m %H:%M:%S") for col in ['start_time', 'end_time']})
            pdf_selected = pdf_selected.assign(
                annotations_txt=pdf_selected.apply(
                    lambda x: f"{x['start_time']} - {x['end_time']} ({x['user']})", axis=1),
                notes_txt=pdf_selected.apply(
                    lambda x: f"{x['notes']} ({x['user']})", axis=1)
            )
            pdf_reviews = pdf_selected.loc[pdf_selected['review'] == 1].drop_duplicates(subset=['user', 'artifact'])
            pdf_reviews = pdf_reviews.groupby('artifact')['user'].apply(lambda x: ','.join(x)).reset_index()
            pdf_reviews = pdf_reviews.assign(review_txt=pdf_reviews.apply(lambda x: f"{x['artifact']} : {x['user']}",
                                                                          axis=1),
                                             )
            dct_artifacts = {artifact: "<br/>".join(
                pdf_selected.loc[
                    (pdf_selected['artifact'] == artifact) &
                    (pdf_selected['scoring'] == 0) &
                    (pdf_selected['segment'] == 0) &
                    (~pdf_selected['start_time'].isna())]['annotations_txt'].tolist())
                for artifact in ['chair_stand', '6min_walk', '3m_walk', 'tug']}
            dct_artifacts = {artifact: dct_artifacts[artifact] for artifact in dct_artifacts
                             if bool(dct_artifacts[artifact])}
            artifacts = ("<table cellpadding='2' >" +
                         '<tr>' + ''.join([f'<td><b>{artifact}</b></td>' for artifact in dct_artifacts]) + '</tr>' +
                         '<tr>' + ''.join([f'<td>{dct_artifacts[artifact]}</td>' for artifact in dct_artifacts]) + '</tr>' +
                         '</table>')
            notes = "<br/>".join(
                pdf_selected.loc[
                    (pdf_selected['notes'].fillna("").str.strip() != '')]['notes_txt'].tolist())
            reviews = "<br/>".join(
                pdf_reviews['review_txt'].tolist())
    summary = f"""
    <br/>
    <table cellpadding='2' >
    <tr>
    <td><b>Start Time<b/></td>
    <td><b>End Time<b/></td>
    <td><b>Annotations<b/></td>
    <td><b>Notes<b/></td>
    <td><b>Reviews<b/></td>
    </tr>
    <tr>
    <td>{pd.to_datetime(file_start_timestamp).strftime('%d-%m-%Y %H:%M:%S')}</td>
    <td>{pd.to_datetime(file_end_timestamp).strftime('%d-%m-%Y %H:%M:%S')}</td>
    <td>{artifacts}</td>
    <td>{notes}</td>
    <td>{reviews}</td>
    </tr>
    """
    summary_box.text = summary
    print(summary)


def capture_new_annotation(colsource, selected_indices, artifact, fname, uname):
    min_index = min(selected_indices)
    max_index = max(selected_indices)
    pdf_new_annotations = pd.DataFrame(
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
    pdf_new_annotations = pdf_new_annotations.assign(
        **dict(
            [
                (
                    col,
                    (
                        pdf_new_annotations[col] - datetime(1970, 1, 1)
                    ).dt.total_seconds(),
                )
                for col in ["start_epoch", "end_epoch"]
            ]
            + [
                (col, pdf_new_annotations[col].astype(str))
                for col in ["start_time", "end_time", "annotated_at"]
            ]
        )
    )
    return pdf_new_annotations


def get_annotations_from_user_files(annotations_fname):
    return (pd.concat(
        [pd.read_excel(n, engine="openpyxl")
         for n in glob.glob(annotations_fname) if os.path.isfile(n)])
                       if bool(
        [n for n in glob.glob(annotations_fname) if os.path.isfile(n)])
                       else pd.DataFrame(
        columns=[
            "fname",
            "artifact",
            "segment",
            "scoring",
            "review",
            "start_epoch",
            "end_epoch",
            "start_time",
            "end_time",
            "annotated_at",
            "user",
            "notes",
        ]
    )
                       )


# Global Variables
lst_columns = ["timestamp", "x", "y", "z", "light", "button", "temperature"]
lst_displayed_annotations_table_columns = [
    "artifact",
    "segment",
    "scoring",
    "review",
    "start_time",
    "end_time",
    "annotated_at",
    "user",
    "notes",
]
pdf_signal_to_display = None
# pdf_results = pd.DataFrame(columns=['fname', 'artifact', 'start_epoch', 'end_epoch', 'start_time', 'end_time'])
pdf_annotations = get_annotations_from_user_files(annotations_fname)
pdf_annotations = cleanup_annotations(pdf_annotations)
pdf_displayed_annotations = pdf_annotations.copy()
anchor_timestamp = None
file_start_timestamp = None
file_end_timestamp = None
windowsize = 3600

selected_data = ColumnDataSource(data=dict(start_time=[], end_time=[]))
selected_annotations = ColumnDataSource(
    pdf_annotations[lst_displayed_annotations_table_columns]
)
# selected_annotations = ColumnDataSource(data=dict(artifact=[], segment=[], scoring=[], review=[], start_time=[], end_time=[], annotated_at=[],
#                                                   user=[], notes=[]))
data_annot_chairstand = ColumnDataSource(
    data=dict(start_epoch=[], end_epoch=[], start_time=[], end_time=[])
)
data_annot_3m_walk = ColumnDataSource(
    data=dict(start_epoch=[], end_epoch=[], start_time=[], end_time=[])
)
data_annot_tug = ColumnDataSource(
    data=dict(start_epoch=[], end_epoch=[], start_time=[], end_time=[])
)
data_annot_6min_walk = ColumnDataSource(
    data=dict(start_epoch=[], end_epoch=[], start_time=[], end_time=[])
)
data_annot_segment = ColumnDataSource(
    data=dict(start_epoch=[], end_epoch=[], start_time=[], end_time=[], artifact=[])
)
data_annot_scoring = ColumnDataSource(
    data=dict(start_epoch=[], end_epoch=[], start_time=[], end_time=[], artifact=[])
)
data_annot_review = ColumnDataSource(
    data=dict(start_epoch=[], end_epoch=[], start_time=[], end_time=[], artifact=[])
)
# data_annotations = ColumnDataSource(data=dict())
lst_fnames = get_filenames()


lst_timestamps = []
rowread_start = 0
rowread_end = 2000

# Widgets
time_input = TextInput(
    value="", title="Enter anchor time in the format Jun 1 2005 1:33 PM"
)
windowsize_input = TextInput(value="", title="Enter anchor windowsize in seconds")

selected_data_title = Div(text="<b>Selected segment bounds</b>")
selected_annotations_title = Div(text="<b>Selected annotations</b>")
buffer_text = Div(text="&nbsp;")

selected_datatable_columns = [
    TableColumn(field="start_time", title="Start time"),
    TableColumn(field="end_time", title="End time"),
]

selected_annotations_table_columns = [
    TableColumn(field="artifact", title="Artifact"),
    TableColumn(field="segment", title="Segment"),
    TableColumn(field="scoring", title="Scoring"),
    TableColumn(field="review", title="Review"),
    TableColumn(field="start_time", title="Start Time"),
    TableColumn(field="end_time", title="End Time"),
    TableColumn(field="annotated_at", title="Annotated at"),
    TableColumn(field="user", title="User"),
    TableColumn(field="notes", title="Notes"),
]

selected_data_table = DataTable(
    source=selected_data,
    columns=selected_datatable_columns,
    height=200,
    height_policy="auto",
    sortable=True,
    selectable=True,
    editable=True,
)

selected_annotations_table = DataTable(
    source=selected_annotations,
    columns=selected_annotations_table_columns,
    height=200,
    height_policy="auto",
    sortable=True,
    selectable=True,
    editable=True,
)

btn_next_window = Button(
    label="Next window",
    width=5,
    button_type="success",
    # background=None,
    # text_font_size='xx-large',
)

btn_prev_window = Button(
    label="Previous window",
    width=5,
    button_type="success",
    # background=None,
    # text_font_size='xx-large',
)


btn_update_plot = Button(
    label="Update Plot",
    button_type="success",
    width=20,
)

btn_chairstand = Button(
    label="Mark Chairstand",
    button_type="success",
    width=20,
)
btn_chairstand.disabled = True
btn_clear_selection = Button(label="Clear Selection", button_type="success", width=20)
btn_clear_selection.disabled = True

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
btn_remove_annotations = Button(
    label="Remove annotations", button_type="success", width=20
)
btn_remove_annotations.disabled = True
btn_export = Button(label="Export annotations", button_type="success", width=20)

btn_notes = Button(label="Add notes", button_type="success", width=15)
btn_notes.disabled = True

file_picker = Select(
    value=lst_fnames[0], title="Select a file", options=sorted(lst_fnames)
)
user_setter = Select(value=lst_users[0], title="Annotate as", options=sorted(lst_users))
review_multi_select = MultiSelect(title="Mark for review", value=[],
                           options=[("chair_stand", "Chairstand"),
                                    ("tug", "TUG"), ("3m_walk", "3MW"), ("6min_walk", "6MW")])

# Dashboard init
fname = os.path.join(readings_folder, lst_fnames[0].split("--")[1])
uname = lst_users[0]
summary = ""
summary_box = Div(text=summary)
srs, colsource = update_datasources()
p, select = make_plot(
    srs,
    colsource,
    data_annot_chairstand,
    data_annot_3m_walk,
    data_annot_6min_walk,
    data_annot_tug,
    file_picker.value,
)

range_tool = RangeTool(x_range=p.x_range)
range_tool.overlay.fill_color = "navy"
range_tool.overlay.fill_alpha = 0.2
select.add_tools(range_tool)
select.toolbar.active_multi = 'auto'


# Callbacks
def update_plot():
    p.title.text = os.path.basename(fname)
    new_srs, new_colsource = update_datasources()

    colsource.data.update(new_colsource.data)
    p.x_range.update(start=new_srs[400])
    p.x_range.update(end=new_srs[3000])

    colsource.selected.indices = []
    update_annotations()


def update_selection():
    global pdf_annotations
    global pdf_displayed_annotations
    global fname
    global uname
    global lst_displayed_annotations_table_columns
    pdf_displayed_annotations = pdf_annotations.loc[
        (pdf_annotations["user"] == uname)
        & (pdf_annotations["fname"] == os.path.basename(fname))
    ]
    selected_indices = colsource.selected.indices
    pdf_selected_data = pd.DataFrame(columns=["start_time", "end_time"])
    pdf_selected_annotations = pd.DataFrame(
        columns=[
            "fname",
            "artifact",
            "segment",
            "scoring",
            "review",
            "start_epoch",
            "end_epoch",
            "start_time",
            "end_time",
            "annotated_at",
            "user",
            "notes",
        ]
    )
    if bool(selected_indices) and (uname != 'None'):
        btn_clear_selection.disabled = False
        btn_tug.disabled = False
        btn_3m_walk.disabled = False
        btn_6min_walk.disabled = False
        btn_chairstand.disabled = False

        min_index = min(selected_indices)
        max_index = max(selected_indices)

        selected_bound_start = pd.to_datetime(
            str(colsource.data["timestamp"][min_index])
        )
        selected_bound_end = pd.to_datetime(str(colsource.data["timestamp"][max_index]))

        pdf_selected_data = pd.DataFrame(
            {
                "start_time": selected_bound_start,
                "end_time": selected_bound_end,
            },
            index=[0],
        )
        pdf_selected_data = pdf_selected_data.assign(
            **dict(
                [
                    (col, pdf_selected_data[col].astype(str))
                    for col in ["start_time", "end_time"]
                ]
            )
        )
        pdf_selected_annotations = pdf_displayed_annotations.loc[
            pd.to_datetime(
                pd.to_numeric(pdf_displayed_annotations["start_time"], errors="coerce"),
                errors="coerce",
            ).between(selected_bound_start, selected_bound_end, inclusive="both")
            & pd.to_datetime(
                pd.to_numeric(pdf_displayed_annotations["end_time"], errors="coerce"),
                errors="coerce",
            ).between(selected_bound_start, selected_bound_end, inclusive="both")
        ]

        pdf_selected_annotations = pdf_selected_annotations.assign(
            **dict(
                [
                    (col, pdf_selected_annotations[col].astype(str))
                    for col in ["start_time", "end_time"]
                ]
            )
        )
        if pdf_selected_annotations.shape[0] > 0:
            btn_remove_annotations.disabled = False
            btn_segment.disabled = False
            btn_scoring.disabled = False
            btn_review.disabled = False
            btn_notes.disabled = False
        else:
            btn_remove_annotations.disabled = True
            btn_segment.disabled = True
            btn_scoring.disabled = True
            btn_review.disabled = True
            btn_notes.disabled = True
    else:
        btn_clear_selection.disabled = True
        btn_tug.disabled = True
        btn_3m_walk.disabled = True
        btn_6min_walk.disabled = True
        btn_remove_annotations.disabled = True
        btn_chairstand.disabled = True
        btn_segment.disabled = True
        btn_scoring.disabled = True
        btn_review.disabled = True
        btn_notes.disabled = True

    new_selected = bp.ColumnDataSource(pdf_selected_data)
    # print(pdf_selected_annotations[['fname', 'artifact', 'segment', 'scoring', 'start_time', 'end_time',
    #          'annotated_at', 'user']])
    new_selected_annotations = bp.ColumnDataSource(
        pdf_selected_annotations[lst_displayed_annotations_table_columns]
    )
    selected_data.data.update(new_selected.data)
    selected_annotations.data.update(new_selected_annotations.data)
    selected_data_table.update()
    selected_annotations_table.update()


def add_notes():
    global pdf_annotations
    global fname
    global uname

    selected_indices = colsource.selected.indices

    if bool(selected_indices) and (uname != 'None'):
        btn_clear_selection.disabled = False
        btn_tug.disabled = False
        btn_3m_walk.disabled = False
        btn_6min_walk.disabled = False
        btn_chairstand.disabled = False
        btn_notes.disabled = False

        min_index = min(selected_indices)
        max_index = max(selected_indices)
        pdf_notes = (
            pd.DataFrame(selected_annotations.data)
            .drop(columns=["index"])
            .reset_index(drop=True)
        )
        print(pdf_notes)

        pdf_selected = pdf_annotations.loc[
            (
                pd.to_datetime(
                    pd.to_numeric(pdf_annotations["start_epoch"], errors="coerce"),
                    unit="s",
                    errors="coerce",
                ).between(
                    colsource.data["timestamp"][min_index],
                    colsource.data["timestamp"][max_index],
                    inclusive="both",
                )
                & pd.to_datetime(
                    pd.to_numeric(pdf_annotations["end_epoch"], errors="coerce"),
                    unit="s",
                    errors="coerce",
                ).between(
                    colsource.data["timestamp"][min_index],
                    colsource.data["timestamp"][max_index],
                    inclusive="both",
                )
                & (pdf_annotations["user"] == uname)
                & (pdf_annotations["fname"] == os.path.basename(fname))
            )
        ].reset_index(drop=True)
        pdf_selected = pdf_selected.assign(notes=pdf_notes["notes"])
        pdf_annotations = pd.concat(
            [
                pdf_annotations.loc[
                    ~(
                        pd.to_datetime(
                            pd.to_numeric(
                                pdf_annotations["start_epoch"], errors="coerce"
                            ),
                            unit="s",
                            errors="coerce",
                        ).between(
                            colsource.data["timestamp"][min_index],
                            colsource.data["timestamp"][max_index],
                            inclusive="both",
                        )
                        & pd.to_datetime(
                            pd.to_numeric(
                                pdf_annotations["end_epoch"], errors="coerce"
                            ),
                            unit="s",
                            errors="coerce",
                        ).between(
                            colsource.data["timestamp"][min_index],
                            colsource.data["timestamp"][max_index],
                            inclusive="both",
                        )
                        & (pdf_annotations["user"] == uname)
                        & (pdf_annotations["fname"] == os.path.basename(fname))
                    )
                ],
                pdf_selected,
            ]
        )
        print(pdf_selected)

    update_annotations()


def update_annotations():
    global uname
    global pdf_annotations
    global pdf_displayed_annotations
    pdf_annotations = cleanup_annotations(pdf_annotations)
    pdf_displayed_annotations = pdf_annotations.loc[
        (pdf_annotations["user"] == uname)
        & (pdf_annotations["fname"] == os.path.basename(fname))
    ]
    data_annot_chairstand.data.update(
        bp.ColumnDataSource(
            pdf_displayed_annotations.loc[
                pdf_displayed_annotations["artifact"] == "chair_stand"
            ][["start_epoch", "end_epoch", "start_time", "end_time"]]
        ).data
    )
    data_annot_6min_walk.data.update(
        bp.ColumnDataSource(
            pdf_displayed_annotations.loc[
                pdf_displayed_annotations["artifact"] == "6min_walk"
            ][["start_epoch", "end_epoch", "start_time", "end_time"]]
        ).data
    )
    data_annot_3m_walk.data.update(
        bp.ColumnDataSource(
            pdf_displayed_annotations.loc[
                pdf_displayed_annotations["artifact"] == "3m_walk"
            ][["start_epoch", "end_epoch", "start_time", "end_time"]]
        ).data
    )
    data_annot_tug.data.update(
        bp.ColumnDataSource(
            pdf_displayed_annotations.loc[
                pdf_displayed_annotations["artifact"] == "tug"
            ][["start_epoch", "end_epoch", "start_time", "end_time"]]
        ).data
    )
    data_annot_segment.data.update(
        bp.ColumnDataSource(
            pdf_displayed_annotations.loc[pdf_displayed_annotations["segment"] == 1][
                ["start_epoch", "end_epoch", "start_time", "end_time", "artifact"]
            ]
        ).data
    )
    data_annot_scoring.data.update(
        bp.ColumnDataSource(
            pdf_displayed_annotations.loc[pdf_displayed_annotations["scoring"] == 1][
                ["start_epoch", "end_epoch", "start_time", "end_time", "artifact"]
            ]
        ).data
    )
    data_annot_review.data.update(
        bp.ColumnDataSource(
            pdf_displayed_annotations.loc[pdf_displayed_annotations["review"] == 1][
                ["start_epoch", "end_epoch", "start_time", "end_time", "artifact"]
            ]
        ).data
    )
    # data_annotations.data.update(bp.ColumnDataSource(pdf_annotations).data)
    update_selection()


update_annotations()


def plot_new_file(attrname, old, new):
    global fname
    global anchor_timestamp
    anchor_timestamp = None
    fname = os.path.join(readings_folder, file_picker.value.split("--")[1])
    update_plot()


def load_user_annotations(attrname, old, new):
    global uname
    global pdf_annotations
    global annotations_fname
    uname = user_setter.value
    pdf_annotations = get_annotations_from_user_files(annotations_fname)
    update_annotations()
    global pdf_displayed_annotations
    pdf_review_flags = pdf_displayed_annotations.loc[
        (pdf_displayed_annotations["review"] == 1)
        & (pdf_displayed_annotations["start_time"].isna())
        ]
    review_multi_select.value = pdf_review_flags.artifact.unique().tolist()


def redraw_plots():
    update_plot()


def mark_chairstand():
    global pdf_annotations
    global fname
    global uname
    selected_indices = colsource.selected.indices

    if bool(selected_indices):
        pdf_new_annotations = capture_new_annotation(
            colsource, selected_indices, "chair_stand", fname, uname
        )
        pdf_annotations = pd.concat([pdf_annotations,
                                     pdf_new_annotations], ignore_index=True)
        # print(pdf_annotations)

    update_annotations()


def mark_6min_walk():
    global fname
    global pdf_annotations
    global uname
    selected_indices = colsource.selected.indices

    if bool(selected_indices):
        pdf_new_annotations = capture_new_annotation(
            colsource, selected_indices, "6min_walk", fname, uname
        )
        pdf_annotations = pd.concat([
            pdf_annotations,
            pdf_new_annotations], ignore_index=True)
    update_annotations()


def toggle_annotation_segment():
    global pdf_annotations
    global fname
    global uname
    global lst_displayed_annotations_table_columns
    pdf_selected_annotations = pd.DataFrame(
        columns=[
            "fname",
            "artifact",
            "segment",
            "scoring",
            "review",
            "start_time",
            "end_time",
            "annotated_at",
            "user",
            "notes",
        ]
    )
    selected_indices = colsource.selected.indices
    if bool(selected_indices):
        min_index = min(selected_indices)
        max_index = max(selected_indices)

        pdf_selected_annotations = pdf_annotations.loc[
            (
                pd.to_datetime(
                    pd.to_numeric(pdf_annotations["start_epoch"], errors="coerce"),
                    unit="s",
                    errors="coerce",
                ).between(
                    colsource.data["timestamp"][min_index],
                    colsource.data["timestamp"][max_index],
                    inclusive="both",
                )
                & pd.to_datetime(
                    pd.to_numeric(pdf_annotations["end_epoch"], errors="coerce"),
                    unit="s",
                    errors="coerce",
                ).between(
                    colsource.data["timestamp"][min_index],
                    colsource.data["timestamp"][max_index],
                    inclusive="both",
                )
                & (pdf_annotations["user"] == uname)
                & (pdf_annotations["fname"] == os.path.basename(fname))
            )
        ]
        pdf_annotations = pdf_annotations.loc[
            ~(
                pd.to_datetime(
                    pd.to_numeric(pdf_annotations["start_epoch"], errors="coerce"),
                    unit="s",
                    errors="coerce",
                ).between(
                    colsource.data["timestamp"][min_index],
                    colsource.data["timestamp"][max_index],
                    inclusive="both",
                )
                & pd.to_datetime(
                    pd.to_numeric(pdf_annotations["end_epoch"], errors="coerce"),
                    unit="s",
                    errors="coerce",
                ).between(
                    colsource.data["timestamp"][min_index],
                    colsource.data["timestamp"][max_index],
                    inclusive="both",
                )
                & (pdf_annotations["user"] == uname)
                & (pdf_annotations["fname"] == os.path.basename(fname))
            )
        ]
        pdf_selected_annotations = pdf_selected_annotations.assign(
            segment=(pdf_selected_annotations["segment"] != 1).astype(int)
        )
        pdf_annotations = pd.concat(
            [pdf_annotations, pdf_selected_annotations], ignore_index=True
        )

    new_selected_annotations = bp.ColumnDataSource(
        pdf_selected_annotations[lst_displayed_annotations_table_columns]
    )
    selected_annotations.data.update(new_selected_annotations.data)
    selected_annotations_table.update()
    update_annotations()


def toggle_annotation_scoring():
    global pdf_annotations
    global fname
    global uname
    global lst_displayed_annotations_table_columns
    pdf_selected_annotations = pd.DataFrame(
        columns=[
            "fname",
            "artifact",
            "segment",
            "scoring",
            "review",
            "start_time",
            "end_time",
            "annotated_at",
            "user",
            "notes",
        ]
    )
    selected_indices = colsource.selected.indices
    if bool(selected_indices):
        min_index = min(selected_indices)
        max_index = max(selected_indices)

        pdf_selected_annotations = pdf_annotations.loc[
            (
                pd.to_datetime(
                    pd.to_numeric(pdf_annotations["start_epoch"], errors="coerce"),
                    unit="s",
                    errors="coerce",
                ).between(
                    colsource.data["timestamp"][min_index],
                    colsource.data["timestamp"][max_index],
                    inclusive="both",
                )
                & pd.to_datetime(
                    pd.to_numeric(pdf_annotations["end_epoch"], errors="coerce"),
                    unit="s",
                    errors="coerce",
                ).between(
                    colsource.data["timestamp"][min_index],
                    colsource.data["timestamp"][max_index],
                    inclusive="both",
                )
                & (pdf_annotations["user"] == uname)
                & (pdf_annotations["fname"] == os.path.basename(fname))
            )
        ]
        pdf_annotations = pdf_annotations.loc[
            ~(
                pd.to_datetime(
                    pd.to_numeric(pdf_annotations["start_epoch"], errors="coerce"),
                    unit="s",
                    errors="coerce",
                ).between(
                    colsource.data["timestamp"][min_index],
                    colsource.data["timestamp"][max_index],
                    inclusive="both",
                )
                & pd.to_datetime(
                    pd.to_numeric(pdf_annotations["end_epoch"], errors="coerce"),
                    unit="s",
                    errors="coerce",
                ).between(
                    colsource.data["timestamp"][min_index],
                    colsource.data["timestamp"][max_index],
                    inclusive="both",
                )
                & (pdf_annotations["user"] == uname)
                & (pdf_annotations["fname"] == os.path.basename(fname))
            )
        ]
        pdf_selected_annotations = pdf_selected_annotations.assign(
            scoring=(pdf_selected_annotations["scoring"] != 1).astype(int)
        )
        pdf_annotations = pd.concat(
            [pdf_annotations, pdf_selected_annotations], ignore_index=True
        )

    new_selected_annotations = bp.ColumnDataSource(
        pdf_selected_annotations[lst_displayed_annotations_table_columns]
    )
    selected_annotations.data.update(new_selected_annotations.data)
    selected_annotations_table.update()
    update_annotations()


def toggle_review_flag():
    global pdf_annotations
    global fname
    global uname
    global lst_displayed_annotations_table_columns
    pdf_selected_annotations = pd.DataFrame(
        columns=[
            "fname",
            "artifact",
            "segment",
            "scoring",
            "review",
            "start_time",
            "end_time",
            "annotated_at",
            "user",
            "notes",
        ]
    )
    selected_indices = colsource.selected.indices
    if bool(selected_indices):
        min_index = min(selected_indices)
        max_index = max(selected_indices)

        pdf_selected_annotations = pdf_annotations.loc[
            (
                pd.to_datetime(
                    pd.to_numeric(pdf_annotations["start_epoch"], errors="coerce"),
                    unit="s",
                    errors="coerce",
                ).between(
                    colsource.data["timestamp"][min_index],
                    colsource.data["timestamp"][max_index],
                    inclusive="both",
                )
                & pd.to_datetime(
                    pd.to_numeric(pdf_annotations["end_epoch"], errors="coerce"),
                    unit="s",
                    errors="coerce",
                ).between(
                    colsource.data["timestamp"][min_index],
                    colsource.data["timestamp"][max_index],
                    inclusive="both",
                )
                & (pdf_annotations["user"] == uname)
                & (pdf_annotations["fname"] == os.path.basename(fname))
            )
        ]
        pdf_annotations = pdf_annotations.loc[
            ~(
                pd.to_datetime(
                    pd.to_numeric(pdf_annotations["start_epoch"], errors="coerce"),
                    unit="s",
                    errors="coerce",
                ).between(
                    colsource.data["timestamp"][min_index],
                    colsource.data["timestamp"][max_index],
                    inclusive="both",
                )
                & pd.to_datetime(
                    pd.to_numeric(pdf_annotations["end_epoch"], errors="coerce"),
                    unit="s",
                    errors="coerce",
                ).between(
                    colsource.data["timestamp"][min_index],
                    colsource.data["timestamp"][max_index],
                    inclusive="both",
                )
                & (pdf_annotations["user"] == uname)
                & (pdf_annotations["fname"] == os.path.basename(fname))
            )
        ]
        pdf_selected_annotations = pdf_selected_annotations.assign(
            review=(pdf_selected_annotations["review"] != 1).astype(int)
        )
        pdf_annotations = pd.concat(
            [pdf_annotations, pdf_selected_annotations], ignore_index=True
        )

    new_selected_annotations = bp.ColumnDataSource(
        pdf_selected_annotations[lst_displayed_annotations_table_columns]
    )
    selected_annotations.data.update(new_selected_annotations.data)
    selected_annotations_table.update()
    update_annotations()


def remove_selected_annotations():
    global pdf_annotations
    global fname
    global uname
    global lst_displayed_annotations_table_columns
    pdf_selected_annotations = pd.DataFrame(
        columns=[
            "fname",
            "artifact",
            "segment",
            "scoring",
            "review",
            "start_time",
            "end_time",
            "annotated_at",
            "user",
            "notes",
        ]
    )
    selected_indices = colsource.selected.indices
    if bool(selected_indices):
        min_index = min(selected_indices)
        max_index = max(selected_indices)
        pdf_annotations = pdf_annotations.loc[
            ~(
                pd.to_datetime(
                    pd.to_numeric(pdf_annotations["start_epoch"], errors="coerce"),
                    unit="s",
                    errors="coerce",
                ).between(
                    colsource.data["timestamp"][min_index],
                    colsource.data["timestamp"][max_index],
                    inclusive="both",
                )
                & pd.to_datetime(
                    pd.to_numeric(pdf_annotations["end_epoch"], errors="coerce"),
                    unit="s",
                    errors="coerce",
                ).between(
                    colsource.data["timestamp"][min_index],
                    colsource.data["timestamp"][max_index],
                    inclusive="both",
                )
                & (pdf_annotations["user"] == uname)
                & (pdf_annotations["fname"] == os.path.basename(fname))
            )
        ]

    new_selected_annotations = bp.ColumnDataSource(
        pdf_selected_annotations[lst_displayed_annotations_table_columns]
    )
    selected_annotations.data.update(new_selected_annotations.data)
    selected_annotations_table.update()
    update_annotations()


def clear_selection():
    colsource.selected.indices = []


def save_annotations():
    global uname
    global fname
    global pdf_annotations
    global annotations_fname
    pdf_old_results = pd.DataFrame(columns=pdf_annotations.columns)
    if os.path.exists(annotations_fname):
        pdf_old_results = pd.read_excel(annotations_fname, engine="openpyxl")
        pdf_old_results = pdf_old_results.assign(
            annotated_at=pd.to_datetime(
                pdf_old_results["annotated_at"], errors="coerce"
            )
        )
    pdf_all_results = pd.concat(
        [
            pdf_old_results.loc[
                ~(
                    (pdf_old_results["user"] == uname)
                    & (pdf_old_results["fname"] == os.path.basename(fname))
                )
            ],
            pdf_annotations.loc[
                (
                    (pdf_annotations["user"] == uname)
                    & (pdf_annotations["fname"] == os.path.basename(fname))
                )
            ],
        ],
        ignore_index=True,
    ).reset_index(drop=True)
    pdf_all_results = cleanup_annotations(pdf_all_results)
    pdf_all_results.to_excel(annotations_fname.replace("*", uname),
                             index=False)
    # pdf_annotations = pdf_all_results
    pdf_annotations = get_annotations_from_user_files(annotations_fname)
    update_annotations()
    update_summary()


def mark_3m_walk():
    global pdf_annotations
    global uname
    global fname
    selected_indices = colsource.selected.indices
    if bool(selected_indices):
        pdf_new_annotations = capture_new_annotation(
            colsource, selected_indices, "3m_walk", fname, uname
        )
        pdf_annotations = pd.concat([pdf_annotations,
            pdf_new_annotations], ignore_index=True)
    update_annotations()


def mark_tug():
    global pdf_annotations
    global uname
    global fname
    selected_indices = colsource.selected.indices
    if bool(selected_indices):
        pdf_new_annotations = capture_new_annotation(
            colsource, selected_indices, "tug", fname, uname
        )
        pdf_annotations = pd.concat([pdf_annotations,
            pdf_new_annotations], ignore_index=True)
    update_annotations()


def update_anchor_timestamp(attr, old, new):
    global anchor_timestamp
    try:
        anchor_timestamp = (
            datetime.strptime(time_input.value, "%b %d %Y %I:%M %p")
            + timedelta(seconds=0)
        ).strftime("%b %d %Y %I:%M %p")
    except Exception as ex:
        print(ex)
        print("Invalid time entered {0}".format(str(time_input.value)))


def move_to_next_window():
    global anchor_timestamp
    global windowsize
    anchor_timestamp = (
        datetime.strptime(anchor_timestamp, "%b %d %Y %I:%M %p")
        + timedelta(seconds=windowsize)
    ).strftime("%b %d %Y %I:%M %p")
    print(f"Anchor timestamp is set to {anchor_timestamp}")
    update_plot()


def move_to_prev_window():
    global anchor_timestamp
    global windowsize
    anchor_timestamp = (
        datetime.strptime(anchor_timestamp, "%b %d %Y %I:%M %p")
        - timedelta(seconds=windowsize)
    ).strftime("%b %d %Y %I:%M %p")
    update_plot()


def update_windowsize(attr, old, new):
    global windowsize
    try:
        windowsize = float(str(windowsize_input.value).strip().replace("s", ""))
    except Exception as ex:
        print(ex)
        print("Invalid windowsize entered {0}".format(str(windowsize_input.value)))


def update_selected_tables(attr, old, new):
    update_selection()


def update_review_flags(attr, old, new):
    lst_new_reviews = review_multi_select.value
    global uname
    global pdf_annotations
    global pdf_displayed_annotations
    global fname
    if set(lst_new_reviews) != set(pdf_annotations.loc[
                                       (pdf_annotations["user"] == uname)
                                       & (pdf_annotations["fname"] == os.path.basename(fname))
                                   ].artifact.tolist()):
        pdf_annotations = pdf_annotations.loc[
            ~((pdf_annotations["user"] == uname)
              & (pdf_annotations["fname"] == os.path.basename(fname))
              & (pdf_annotations["review"] == 1)
              & (pdf_annotations["start_time"].isna()))
        ]
        pdf_annotations = pd.concat([pdf_annotations,
                                     pd.DataFrame([{'fname': os.path.basename(fname),
                                                    'artifact': artifact,
                                                    'segment': 0,
                                                    'scoring': 0,
                                                    'review': 1,
                                                    'annotated_at': datetime.now(),
                                                    'user': uname
                                                    } for artifact in lst_new_reviews],
                                                  index=list(range(len(lst_new_reviews))))],
                                    ignore_index=True).reset_index(drop=True)
        pdf_displayed_annotations = pdf_annotations.loc[
            (pdf_annotations["user"] == uname)
            & (pdf_annotations["fname"] == os.path.basename(fname))
            ]


# Callback registrations
windowsize_input.on_change("value", update_windowsize)
btn_next_window.on_click(move_to_next_window)
btn_prev_window.on_click(move_to_prev_window)
time_input.on_change("value", update_anchor_timestamp)
btn_chairstand.on_click(mark_chairstand)
btn_update_plot.on_click(redraw_plots)
btn_3m_walk.on_click(mark_3m_walk)
btn_tug.on_click(mark_tug)
btn_6min_walk.on_click(mark_6min_walk)
btn_segment.on_click(toggle_annotation_segment)
btn_scoring.on_click(toggle_annotation_scoring)
btn_review.on_click(toggle_review_flag)
btn_clear_selection.on_click(clear_selection)
btn_remove_annotations.on_click(remove_selected_annotations)
btn_export.on_click(save_annotations)
btn_notes.on_click(add_notes)
file_picker.on_change("value", plot_new_file)
user_setter.on_change("value", load_user_annotations)
review_multi_select.on_change("value", update_review_flags)
colsource.selected.on_change("indices", update_selected_tables)

# Layout

layout = grid(
    column(
        row(
            column(
                row(file_picker, user_setter, time_input, windowsize_input, sizing_mode="stretch_width"),
                row(column(review_multi_select),
                    column(
                        row(btn_update_plot,
                            btn_prev_window,
                            btn_next_window,
                            btn_clear_selection,
                            btn_review,
                            btn_remove_annotations,
                            btn_export,
                            sizing_mode="stretch_width",
                            ),
                        row(btn_chairstand,
                            btn_tug,
                            btn_3m_walk,
                            btn_6min_walk,
                            btn_segment,
                            btn_scoring,
                            btn_notes,
                            sizing_mode="stretch_width",
                            ),
                        sizing_mode="stretch_width"
                    )
                    ),
                sizing_mode="stretch_width"
            ), sizing_mode="stretch_width"),
        row(
            column(summary_box, sizing_mode="stretch_width"), sizing_mode="stretch_width"
        ),
        row(
            column(p, select, sizing_mode="stretch_width"), sizing_mode="stretch_width"
        ),
        row(
            column(selected_data_title, selected_data_table, sizing_mode="scale_both"),
            column(
                selected_annotations_title,
                selected_annotations_table,
                sizing_mode="scale_both",
            ),
            sizing_mode="stretch_both",
        ),
        sizing_mode="stretch_both",
    )
)

bokeh_doc = curdoc()
bokeh_doc.add_root(layout)

bokeh_doc.title = "Visualize chair stands & 3M walks"
