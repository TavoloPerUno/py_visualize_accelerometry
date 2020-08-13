import pandas as pd
import dask.dataframe as dd
from dask.distributed import Client, LocalCluster
import sys
import os
from datetime import datetime, date
import time
import subprocess

from bs4 import BeautifulSoup
import requests
import io

from bokeh.io import show
from bokeh.layouts import column, grid, row
from bokeh.models.callbacks import CustomJS
from bokeh.models import TextInput, Button, Div, DatePicker, Slider, ColumnDataSource, RangeTool, HoverTool,  BoxSelectTool, Select, DatetimeTickFormatter
from bokeh.models.widgets import DataTable, DateFormatter, TableColumn,FileInput
from pybase64 import b64decode
from bokeh.plotting import figure
import bokeh.plotting as bp


import numpy as np
from bokeh.plotting import figure, curdoc
from bokeh.models.widgets import Button,  Dropdown
from bokeh.layouts import column, widgetbox

# sys.path.append('../')
from . import config
#### Constants

client = Client() if (config.computation_resources['mode'] == 'local') else Client(config.computation_resources['cluster_ip'])
client.restart()
url = 'https://users.rcc.uchicago.edu/~manorathan/wave4/30_min_segments'
lst_colors = ['red', 'blue', 'green', 'yellow', 'violet']
data_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
readings_folder = os.path.join(data_folder, 'readings')
output_folder = os.path.join(data_folder, 'output')

#### Intial data loaders

def get_filenames():
    # page = requests.get(url).text
    # soup = BeautifulSoup(page, 'html.parser')
    # lst_files = [node.get('href') for node in soup.find_all('a') if node.get('href').endswith('.csv')]
    lst_files = [f for f in os.listdir(readings_folder) if os.path.splitext(f)[1].lower() == '.csv']
    return lst_files

def get_filedata():
    """This function accepts a filename as input and returns the passed file's timestamp index & ColumnDataSource version of the file data
      :param fname str: signal filename
      :return: numpy.ndarray, bokeh.models.ColumnDataSource
    """
    global df_signal
    global fname
    global anchor_timestamp
    global lst_timestamps
    global lst_columns
    global windowsize
    print("Loading {0}".format(fname))
    if config.computation_resources['mode'] == 'local':
        cmd_timestamp_read = 'cut -d"," -f1 "{0}" | tail -n +2'.format(fname)
        cmd_columnheader_read = 'head -n 1 "{0}"'.format(fname)
        cmd_read_first_timestamp = 'head -n 2 "{0}" | tail -n 1 |'.format(fname) + r"""awk 'BEGIN{FS=","} {print $1}'"""
        process = subprocess.Popen(cmd_columnheader_read, stdout=subprocess.PIPE, shell=True)
        lst_columns = process.communicate()[0]
        lst_columns = lst_columns.decode("utf-8").replace("\n", "").replace('"', '').split(",")
        # process = subprocess.Popen(cmd_read_first_timestamp, stdout=subprocess.PIPE, shell=True)
        # anchor_timestamp = process.communicate()[0]
        # anchor_timestamp = anchor_timestamp.decode("utf-8").replace("\n", "")
        process = subprocess.Popen(cmd_timestamp_read, stdout=subprocess.PIPE, shell=True)
        timestamp_output = process.communicate()[0]
        lst_timestamps = timestamp_output.decode("utf-8").replace('"', '').split("\n")
    else:
        # client.restart()
        df_signal = dd.read_csv(fname, dtype='object')
        print(df_signal.head())
        df_signal = df_signal.map_partitions(lambda pdf: pdf.assign(**dict([(col, pd.to_numeric(pdf[col],
                                                                                                errors='coerce'))
                                                                            for col in pdf.columns]
                                                                           ))
                                             ).set_index('timestamp', sorted=True)
        # df_signal['timestamp'] = df_signal['timestamp']
        print(df_signal.head())
        lst_timestamps = df_signal.index.compute().tolist()
        print(lst_timestamps[0])
        lst_columns = [df_signal.index.name] + df_signal.columns
    anchor_timestamp = float(lst_timestamps[0])
    time_input.value = datetime.utcfromtimestamp(anchor_timestamp).strftime('%b %d %Y %I:%M %p')
    print(lst_timestamps[0])
    print("Anchor timestamp: {0}".format(anchor_timestamp))
    print("Anchor timestamp (str): {0}".format((datetime.strptime(time_input.value, '%b %d %Y %I:%M %p') - datetime(1970, 1, 1)).total_seconds()))
    windowsize = 3600
    windowsize_input.value = str(windowsize)
    # df_signal = dd.read_csv(fname) #, parse_dates=['timestamp']) #.set_index('timestamp', sorted=True)
    # # print("First few rows in the loaded file:")
    # # print(df_signal.head())
    #
    # df_signal = df_signal.map_partitions(lambda pdf: pdf.assign(
    #     timestamp=pd.to_datetime(pdf['timestamp'], errors='coerce'),
    #     timestamp_str=pdf['timestamp'].astype(str)))
    # df_signal = df_signal.map_partitions(lambda pdf:
    #                                      pdf.assign(timestamp_ns=(pdf['timestamp'] -
    #                                                              pd.to_datetime('1970-01-01')).dt.total_seconds().astype(int)))
    # df_signal = df_signal.set_index('timestamp_ns', sorted=True)
    # anchor_timestamp = df_signal.index.min().compute()
    return None

def update_datasources():
    global anchor_timestamp
    global df_signal
    global lst_timestamps
    global fname
    global windowsize
    df_signal_to_display = pd.DataFrame()
    if config.computation_resources['mode'] == 'local':
        min_timestamp_index = next(x[0] for x in enumerate(lst_timestamps) if float(x[1]) > anchor_timestamp - (windowsize/2)) + 1
        min_timestamp_index = max(2, min_timestamp_index)
        max_timestamp_index = next(x[0] for x in enumerate(lst_timestamps) if float(x[1]) > anchor_timestamp + (windowsize/2))
        max_timestamp_index = max(windowsize, max_timestamp_index)
        cmd_read_accelerometry_data = "sed -n {0},{1}p '{2}'".format(min_timestamp_index, max_timestamp_index, fname)
        process = subprocess.Popen(cmd_read_accelerometry_data, stdout=subprocess.PIPE, shell=True)
        df_signal_to_display = io.StringIO(process.communicate()[0].decode('utf-8'))
        df_signal_to_display = pd.read_csv(df_signal_to_display, sep=",", header=None)
        df_signal_to_display.columns = lst_columns
        df_signal_to_display = df_signal_to_display.assign(**dict([(col, pd.to_numeric(df_signal_to_display[col],
                                                                                       errors='coerce'))
                                                            for col in lst_columns]))
    else:
        df_signal_to_display = df_signal.loc[(df_signal.index >= ((anchor_timestamp - (windowsize/2)))) &
                                             (df_signal.index <= (anchor_timestamp + (windowsize/2)))].compute()
        df_signal_to_display = df_signal_to_display.reset_index(drop=False)
        df_signal_to_display = df_signal_to_display.sort_values(by='timestamp', ascending=True)
    df_signal_to_display = df_signal_to_display.assign(
        timestamp=pd.to_datetime(df_signal_to_display['timestamp'], errors='coerce', unit='s'),
        timestamp_str=pd.to_datetime(df_signal_to_display['timestamp'],unit='s').astype(str))
    # timestamp_output = process.communicate()[0]
    # lst_timpstamps = timestamp_output.decode("utf-8").split("\n")

    print("Column datatypes:")
    print(df_signal_to_display.head().dtypes)
    print("Anchor timestamp: {0}".format(anchor_timestamp))
    print("Anchor timestamp (str): {0}".format(
        (datetime.strptime(time_input.value, '%b %d %Y %I:%M %p') - datetime(1970, 1, 1)).total_seconds()))
    print("N rows:{0}".format(df_signal_to_display.shape[0]))
    dates = df_signal_to_display['timestamp'].values
    source = bp.ColumnDataSource(df_signal_to_display)

    return dates, source

def make_plot(srs, colsource, title):
    tools = "hover,box_select"
    p = figure(plot_height=300, tools=tools, toolbar_location='left',
               x_axis_type="datetime",
               x_axis_location="above",
               background_fill_color="#efefef", x_range=(srs[400], srs[3000]), title=title, width=1520)
    p.xaxis.axis_label = 'Timestamp'


    lst_col = ['x', 'y', 'z']  # + df_signal.columns.difference(['timestamp', 'x', 'y', 'z']).tolist()
    lst_line_plots = []
    for (colr, leg) in zip(lst_colors, lst_col):
        lst_line_plots.append(p.line('timestamp', leg, color=colr, legend_label=leg, source=colsource, name='wave'))
        p.scatter('timestamp', leg, color=None, legend_label=leg, source=colsource, name='wave')

    p.xaxis.formatter = DatetimeTickFormatter(days=["%m/%d %H:%M"],
                                              months=["%m/%d %H:%M"],
                                              hours=["%m/%d %H:%M"],
                                              minutes=["%m/%d %H:%M"])
    hover = p.select(dict(type=HoverTool))
    hover.tooltips = [("timestamp", "@timestamp_str")]
    hover.renderers = lst_line_plots

    select = figure(title="Drag the middle and edges of the selection box to change the range above",
                    plot_height=130, y_range=p.y_range,
                    x_axis_type="datetime", y_axis_type=None,
                    tools="", toolbar_location=None, background_fill_color="#efefef",width=1520)



    for (colr, leg) in zip(lst_colors, lst_col):
        select.line('timestamp', leg, color=colr, source=colsource)
    select.ygrid.grid_line_color = None
    select.xaxis.formatter = DatetimeTickFormatter( days=["%m/%d %H:%M"],
                                                    months=["%m/%d %H:%M"],
                                                    hours=["%m/%d %H:%M"],
                                                    minutes=["%m/%d %H:%M"])

    return p, select

### Global Variables

df_signal = None
pdf_results = pd.DataFrame(columns=['fname', 'artifact', 'start_time', 'end_time', 'start_time_str', 'end_time_str'])
anchor_timestamp = 0
windowsize = 3600
selected_data = ColumnDataSource(data=dict(timestamp=[], timestamp_str=[], x=[], y=[], z=[]))
annotations = ColumnDataSource(data=dict())
lst_fnames = get_filenames()

lst_columns = []
lst_timestamps = []
rowread_start = 0
rowread_end = 2000



### Widgets

time_input = TextInput(value="", title="Enter anchor timestamp in the format Jun 1 2005 1:33PM")
windowsize_input = TextInput(value="", title="Enter anchor windowsize in seconds")
file_input = FileInput(accept=".csv")

selected_date_title = Div(text="<b>Selected segment bounds</b>")
buffer_text = Div(text="&nbsp;")

columns = [
         TableColumn(field="timestamp", title="Epoch"),
        TableColumn(field="timestamp_str", title="Timestamp"),
         TableColumn(field="x", title="X"),
         TableColumn(field="y", title="Y"),
         TableColumn(field="z", title="Z"),]

table = DataTable(
  source=selected_data,
  columns=columns,
    height=200,
  sortable=True,
  selectable=True,
  editable=True,
)

btn_update_plot = Button(
    label="Update Plot",
    button_type="success",
    width=20,
)

btn_chairstand = Button(
    label="Mark Chairstand",
    button_type="success",
    width=20
)
btn_clear_selection = Button(
    label="Clear Selection",
    button_type="success",
    width=20
)

btn_3m_walk = Button(
    label="Mark 3 m walk",
    button_type="success",
    width=20
)

btn_timed_walk = Button(
    label="Mark timed walk",
    button_type="success",
    width=20
)

btn_export = Button(
    label="Export annotations",
    button_type="success",
    width=20
)

file_picker = Select(value=lst_fnames[0], title='Select a file', options=sorted(lst_fnames))

### Dashboard init

fname = os.path.join(readings_folder, lst_fnames[0])
get_filedata()
srs, colsource = update_datasources()
p, select = make_plot(srs, colsource, file_picker.value)

range_tool = RangeTool(x_range=p.x_range)
range_tool.overlay.fill_color = "navy"
range_tool.overlay.fill_alpha = 0.2
select.add_tools(range_tool)
select.toolbar.active_multi = range_tool

### Callbacks

def update_plot():
    p.title.text = os.path.basename(fname)
    new_srs, new_colsource = update_datasources()

    colsource.data.update(new_colsource.data)
    p.x_range.update(start=new_srs[400])
    p.x_range.update(end=new_srs[3000])

    colsource.selected.indices = []

def upload_file_data(attr, old, new):
    global fname
    # file_picker.value = None
    print("Uploading new file")
    decoded = b64decode(new)
    fname = io.BytesIO(decoded)
    get_filedata()
    update_plot()

def plot_new_file(attrname, old, new):
    global fname
    fname = os.path.join(readings_folder, file_picker.value)
    get_filedata()
    btn_chairstand.label = btn_chairstand.label.replace(' (done)', '')
    btn_3m_walk.label = btn_3m_walk.label.replace(' (done)', '')
    btn_timed_walk.label = btn_timed_walk.label.replace(' (done)', '')
    update_plot()

def redraw_plots():
    update_plot()

def mark_chairstand():
    global pdf_results
    global fname
    selected_indices = colsource.selected.indices

    pdf_results = pdf_results.loc[~((pdf_results['fname'] == file_picker.value) &
                                    (pdf_results['artifact'] == 'chair_stand'))]
    if bool(selected_indices):
        min_index = min(selected_indices)
        max_index = max(selected_indices)
        pdf_results = pdf_results.append(pd.DataFrame({'fname': os.path.basename(fname),
                                                       'artifact': 'chair_stand',
                                                       'start_time': colsource.data['timestamp'][min_index],
                                                       'end_time': colsource.data['timestamp'][max_index],
                                                       'start_time_str': colsource.data['timestamp_str'][min_index],
                                                       'end_time_str': colsource.data['timestamp_str'][max_index],
                                                       'annotated_at': datetime.now()
                                                       }, index=[0]))
        if not btn_chairstand.label.endswith('(done)'):
            btn_chairstand.label = btn_chairstand.label + ' (done)'
    else:
        btn_chairstand.label = btn_chairstand.label.replace(' (done)', '')

    annotations.data.update(bp.ColumnDataSource(pdf_results).data)


def mark_timed_walk():
    global pdf_results
    global fname
    selected_indices = colsource.selected.indices

    pdf_results = pdf_results.loc[~((pdf_results['fname'] == file_picker.value) &
                                    (pdf_results['artifact'] == 'timed_walk'))]
    if bool(selected_indices):
        min_index = min(selected_indices)
        max_index = max(selected_indices)
        pdf_results = pdf_results.append(pd.DataFrame({'fname': os.path.basename(fname),
                                                       'artifact': 'timed_walk',
                                                       'start_time': colsource.data['timestamp'][min_index],
                                                       'end_time': colsource.data['timestamp'][max_index],
                                                       'start_time_str': colsource.data['timestamp_str'][min_index],
                                                       'end_time_str': colsource.data['timestamp_str'][max_index],
                                                       'annotated_at': datetime.now()
                                                       }, index=[0]))
        if not btn_timed_walk.label.endswith('(done)'):
            btn_timed_walk.label = btn_timed_walk.label + ' (done)'
    else:
        btn_timed_walk.label = btn_timed_walk.label.replace(' (done)', '')

    annotations.data.update(bp.ColumnDataSource(pdf_results).data)


def clear_selection():
    colsource.selected.indices = []

def save_annotations():
    pdf_old_results = pd.DataFrame()
    if os.path.exists(os.path.join(output_folder, 'annotations.csv')):
        pdf_old_results = pd.read_csv(os.path.join(output_folder, 'annotations.csv'))
        pdf_old_results = pdf_old_results.assign(annotated_at=pd.to_datetime(pdf_old_results['annotated_at'], errors='coerce'))
    pdf_all_results = pd.concat([pdf_old_results, pdf_results], ignore_index=True).reset_index(drop=True).sort_values(by=['annotated_at'], ascending=False)
    pdf_all_results.drop_duplicates(['fname', 'artifact'], keep='first').to_csv(os.path.join(output_folder,
                                                                                                       'annotations.csv'),
                                                                                          index=False)

def mark_3m_walk():
    global pdf_results
    global fname
    selected_indices = colsource.selected.indices
    pdf_results = pdf_results.loc[~((pdf_results['fname'] == file_picker.value) &
                                    (pdf_results['artifact'] == '3m_walk'))]

    if bool(selected_indices):
        min_index = min(selected_indices)
        max_index = max(selected_indices)

        pdf_results = pdf_results.append(pd.DataFrame({'fname': os.path.basename(fname),
                                                       'artifact': '3m_walk',
                                                       'start_time': colsource.data['timestamp'][min_index],
                                                       'end_time': colsource.data['timestamp'][max_index],
                                                       'start_time_str': colsource.data['timestamp_str'][min_index],
                                                       'end_time_str': colsource.data['timestamp_str'][max_index],
                                                       'annotated_at': datetime.now()
                                                       }, index=[0]))
        if not btn_3m_walk.label.endswith('(done)'):
            btn_3m_walk.label = btn_3m_walk.label + ' (done)'
    else:
        btn_3m_walk.label = btn_3m_walk.label.replace(' (done)', '')
    annotations.data.update(bp.ColumnDataSource(pdf_results).data)

def update_anchor_timestamp(attr, old, new):
    global anchor_timestamp
    try:
        anchor_timestamp = (datetime.strptime(time_input.value, '%b %d %Y %I:%M %p') - datetime(1970, 1, 1)).total_seconds()
        # update_plot()
    except Exception as ex:
        print(ex)
        print("Invalid time entered {0}".format(str(time_input.value)))

def update_windowsize(attr, old, new):
    global windowsize
    try:
        windowsize = float(str(windowsize_input.value).strip().replace("s", ""))
        # update_plot()
    except Exception as ex:
        print(ex)
        print("Invalid windowsize entered {0}".format(str(windowsize_input.value)))


def update_selection(attr, old, new):
    selected_indices = colsource.selected.indices
    df_selected_data = pd.DataFrame(columns=['timestamp',
                                             'timestamp_str',
                                             'x', 'y', 'z'])
    if bool(selected_indices):
        min_index = min(selected_indices)
        max_index = max(selected_indices)

        df_selected_data = pd.DataFrame({'timestamp': [colsource.data['timestamp'][min_index],
                                                       colsource.data['timestamp'][max_index]],
                                         'timestamp_str': [colsource.data['timestamp_str'][min_index],
                                                            colsource.data['timestamp_str'][max_index]],
                                         'x': [colsource.data['x'][min_index],
                                               colsource.data['x'][max_index]],
                                         'y': [colsource.data['y'][min_index],
                                               colsource.data['y'][max_index]],
                                         'z': [colsource.data['z'][min_index],
                                               colsource.data['z'][max_index]]
                                         })
    new_selected = bp.ColumnDataSource(df_selected_data)
    selected_data.data.update(new_selected.data)


### Callback registrations

file_input.on_change("value", upload_file_data)
windowsize_input.on_change("value", update_windowsize)
time_input.on_change("value", update_anchor_timestamp)
btn_chairstand.on_click(mark_chairstand)
btn_update_plot.on_click(redraw_plots)
btn_3m_walk.on_click(mark_3m_walk)
btn_timed_walk.on_click(mark_timed_walk)
btn_clear_selection.on_click(clear_selection)
btn_export.on_click(save_annotations)
# btn_export.js_on_click(CustomJS(args=dict(source=annotations),
#                             code=open(os.path.join(os.path.dirname(__file__), 'js', "download.js")).read()))
file_picker.on_change('value', plot_new_file)

colsource.selected.on_change("indices", update_selection)


### Layout

layout = grid(column(row(column(row(file_picker, sizing_mode='stretch_width'), row(time_input, windowsize_input, sizing_mode='stretch_width'),
                         ), column(row(btn_update_plot,btn_clear_selection, sizing_mode='stretch_width'),
                                                             row(btn_chairstand,btn_3m_walk,btn_timed_walk, sizing_mode='stretch_width'),
                                                             row(btn_export, sizing_mode='stretch_width'),
                                                            )),
                     row(column(p, select)),
                     row(column(selected_date_title, table, sizing_mode='stretch_both')))
                     #
              )


bokeh_doc = curdoc()
bokeh_doc.add_root(layout)

bokeh_doc.title = "Visualize chair stands & 3M walks"