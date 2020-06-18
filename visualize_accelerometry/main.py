import pandas as pd
import dask.dataframe as dd
import sys
import os

from bs4 import BeautifulSoup
import requests

from bokeh.io import show
from bokeh.layouts import column, grid, row
from bokeh.models.callbacks import CustomJS
from bokeh.models import Button, Div, ColumnDataSource, RangeTool, HoverTool,  BoxSelectTool, Select, DatetimeTickFormatter
from bokeh.models.widgets import DataTable, DateFormatter, TableColumn
from bokeh.plotting import figure
import bokeh.plotting as bp

import numpy as np
from bokeh.plotting import figure, curdoc
from bokeh.models.widgets import Button,  Dropdown
from bokeh.layouts import column, widgetbox


#### Constants

url = 'https://users.rcc.uchicago.edu/~manorathan/wave4/30_min_segments'
lst_colors = ['red', 'blue', 'green', 'yellow', 'violet']


#### Intial data loaders

def get_filenames():
    page = requests.get(url).text
    soup = BeautifulSoup(page, 'html.parser')
    lst_files = [node.get('href') for node in soup.find_all('a') if node.get('href').endswith('.csv')]
    return lst_files

def get_filedata(fname):
    """This function accepts a filename as input and returns the passed file's timestamp index & ColumnDataSource version of the file data
      :param fname str: signal filename
      :return: numpy.ndarray, bokeh.models.ColumnDataSource
    """
    df_signal = pd.read_csv(url + '/' + fname)
    # print("First few rows in the loaded file:")
    # print(df_signal.head())

    df_signal = df_signal.assign(timestamp=pd.to_datetime(df_signal['timestamp']),
                               timestamp_str=pd.to_datetime(df_signal['timestamp']).astype(str))
    print("Column datatypes:")
    print(df_signal.head().dtypes)

    dates = df_signal['timestamp'].values
    source = bp.ColumnDataSource(df_signal)

    return dates, source

def make_plot(srs, colsource, title):
    tools = "hover,box_select"
    p = figure(plot_height=300, tools=tools, toolbar_location='left',
               x_axis_type="datetime",
               x_axis_location="above",
               background_fill_color="#efefef", x_range=(srs[400], srs[3000]),
               output_backend="webgl", title=title)
    p.xaxis.axis_label = 'Timestamp'


    lst_col = ['x', 'y', 'z']  # + df_signal.columns.difference(['timestamp', 'x', 'y', 'z']).tolist()

    for (colr, leg) in zip(lst_colors, lst_col):
        p.line('timestamp', leg, color=colr, legend_label=leg, source=colsource, name='wave')
        p.scatter('timestamp', leg, color=None, legend_label=leg, source=colsource, name='wave')

    p.xaxis.formatter = DatetimeTickFormatter(days=["%m/%d %H:%M"],
                                              months=["%m/%d %H:%M"],
                                              hours=["%m/%d %H:%M"],
                                              minutes=["%m/%d %H:%M"])
    hover = p.select(dict(type=HoverTool))
    hover.tooltips = [("timestamp", "@timestamp_str")]

    select = figure(title="Drag the middle and edges of the selection box to change the range above",
                    plot_height=130, y_range=p.y_range,
                    x_axis_type="datetime", y_axis_type=None,
                    tools="", toolbar_location=None, background_fill_color="#efefef",
                    output_backend="webgl")



    for (colr, leg) in zip(lst_colors, lst_col):
        select.line('timestamp', leg, color=colr, source=colsource)
    select.ygrid.grid_line_color = None
    select.xaxis.formatter = DatetimeTickFormatter(days=["%m/%d %H:%M"],
                                              months=["%m/%d %H:%M"],
                                              hours=["%m/%d %H:%M"],
                                              minutes=["%m/%d %H:%M"])

    return p, select

### Widgets



### Global Variables

pdf_results = pd.DataFrame(columns=['fname', 'artifact', 'start_time', 'end_time', 'start_time_str', 'end_time_str'])

selected_data = ColumnDataSource(data=dict(timestamp=[], x=[], y=[], z=[]))
annotations = ColumnDataSource(data=dict())

lst_fnames = get_filenames()


### Widgets

selected_date_title = Div(text="<b>Selected segment bounds</b>")


columns = [
         TableColumn(field="timestamp", title="Timestamp"),
        TableColumn(field="timestamp_str", title="Timestamp (pretty)"),
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

btn_chairstand = Button(
    label="Mark Chairstand",
    button_type="success",
    width=50
)
btn_clear_selection = Button(
    label="Clear Selection",
    button_type="success",
    width=50
)

btn_3m_walk = Button(
    label="Mark 3 m walk",
    button_type="success",
    width=50
)

btn_export = Button(
    label="Export annotations",
    button_type="success",
    width=50
)

file_picker = Select(value=lst_fnames[0], title='Select a file', options=sorted(lst_fnames))

### Dashboard init

srs, colsource = get_filedata(lst_fnames[0])
p, select = make_plot(srs, colsource, file_picker.value)

range_tool = RangeTool(x_range=p.x_range)
range_tool.overlay.fill_color = "navy"
range_tool.overlay.fill_alpha = 0.2
select.add_tools(range_tool)
select.toolbar.active_multi = range_tool

### Callbacks

def update_plot(attrname, old, new):

    new_fname = file_picker.value
    p.title.text = new_fname

    new_srs, new_colsource = get_filedata(new_fname)

    colsource.data.update(new_colsource.data)
    p.x_range.update(start=new_srs[400])
    p.x_range.update(end=new_srs[3000])

    btn_chairstand.label = btn_chairstand.label.replace(' (done)', '')
    btn_3m_walk.label = btn_3m_walk.label.replace(' (done)', '')


def mark_chairstand():
    global pdf_results
    selected_indices = colsource.selected.indices
    pdf_results = pdf_results.loc[~((pdf_results['fname'] == file_picker.value) &
                                    (pdf_results['artifact'] == 'chair_stand'))]
    pdf_results = pdf_results.append(pd.DataFrame({'fname': file_picker.value,
                                                   'artifact': 'chair_stand',
                                                   'start_time': colsource.data['timestamp'][selected_indices[0]],
                                                   'end_time': colsource.data['timestamp'][selected_indices[-1]],
                                                   'start_time_str': colsource.data['timestamp_str'][selected_indices[0]],
                                                   'end_time_str': colsource.data['timestamp_str'][selected_indices[-1]],
                                                   }, index=[0]))
    annotations.data.update(bp.ColumnDataSource(pdf_results).data)
    if not btn_chairstand.label.endswith('(done)'):
        btn_chairstand.label = btn_chairstand.label + ' (done)'

def clear_selection():
    colsource.selected.indices = []

def mark_3m_walk():
    global pdf_results
    selected_indices = colsource.selected.indices
    pdf_results = pdf_results.loc[~((pdf_results['fname'] == file_picker.value) &
                                    (pdf_results['artifact'] == '3m_walk'))]
    pdf_results = pdf_results.append(pd.DataFrame({'fname': file_picker.value,
                                                   'artifact': '3m_walk',
                                                   'start_time': colsource.data['timestamp'][selected_indices[0]],
                                                   'end_time': colsource.data['timestamp'][selected_indices[-1]],
                                                   'start_time_str': colsource.data['timestamp_str'][
                                                       selected_indices[0]],
                                                   'end_time_str': colsource.data['timestamp_str'][
                                                       selected_indices[-1]],
                                                   }, index=[0]))
    annotations.data.update(bp.ColumnDataSource(pdf_results).data)
    if not btn_3m_walk.label.endswith('(done)'):
        btn_3m_walk.label = btn_3m_walk.label + ' (done)'

def update_selection(attr, old, new):
    selected_indices = colsource.selected.indices
    print("Selected indices are")
    print(selected_indices)
    min_index = min(selected_indices)
    max_index = max(selected_indices)

    df_selected_data = pd.DataFrame({'timestamp': [colsource.data['timestamp'][min_index],
                                                   colsource.data['timestamp'][max_index]],
                                     'timestamp_str': [colsource.data['timestamp_str'][min_index],
                                                   colsource.data['timestamp_str'][max_index]],
                                     'X': [colsource.data['x'][min_index],
                                                       colsource.data['x'][max_index]],
                                     'Y': [colsource.data['y'][min_index],
                                                       colsource.data['y'][max_index]],
                                     'Z': [colsource.data['z'][min_index],
                                                       colsource.data['z'][max_index]]
                                     })
    new_selected = bp.ColumnDataSource(df_selected_data)
    selected_data.data.update(new_selected.data)
    selected_data.change.emit()
    table.change.emit()


### Callback registrations

btn_chairstand.on_click(mark_chairstand)
btn_3m_walk.on_click(mark_3m_walk)
btn_clear_selection.on_click(clear_selection)
btn_export.js_on_click(CustomJS(args=dict(source=annotations),
                            code=open(os.path.join(os.path.dirname(__file__), 'js', "download.js")).read()))
file_picker.on_change('value', update_plot)

colsource.selected.on_change("indices", update_selection)
# colsource.selected.js_on_change(
#     "indices",
#     CustomJS(
#         args=dict(s1=colsource, s2=selected_data, table=table),
#         code="""
#         var inds = cb_obj.indices;
#         var d1 = s1.data;
#         var d2 = s2.data;
#         d2['timestamp'] = []
#         d2['x'] = []
#         d2['y'] = []
#         d2['z'] = []
#         d2['timestamp_str'] = []
#         d2['timestamp'].push(d1['timestamp'][inds[0]])
#         d2['timestamp_str'].push(d1['timestamp_str'][inds[0]])
#         d2['x'].push(d1['x'][inds[0]])
#         d2['y'].push(d1['y'][inds[0]])
#         d2['z'].push(d1['z'][inds[0]])
#         d2['timestamp'].push(d1['timestamp'][inds[inds.length-1]])
#         d2['x'].push(d1['x'][inds[inds.length-1]])
#         d2['y'].push(d1['y'][inds[inds.length-1]])
#         d2['z'].push(d1['z'][inds[inds.length-1]])
#         d2['timestamp_str'].push(d1['timestamp_str'][inds[inds.length-1]])
#         s2.change.emit();
#         table.change.emit();
#     """,
#     ),
# )

### Layout

layout = grid(column(row(column(file_picker, p, select)),
                     row(column(selected_date_title, table)),
                     row(btn_chairstand, btn_3m_walk),
                     row(btn_clear_selection, btn_export)),
                     sizing_mode='stretch_width')


bokeh_doc = curdoc()
bokeh_doc.add_root(layout)

bokeh_doc.title = "Visualize chair stands & 3M walks"