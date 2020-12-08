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
from bokeh.layouts import column, grid, row, Spacer
from bokeh.models.callbacks import CustomJS
from bokeh.models import TextInput, Quad, Button, LabelSet, Div, NormalHead, Div, DatePicker, Slider, ColumnDataSource, RangeTool, HoverTool, \
	BoxSelectTool, Select, DatetimeTickFormatter, Span, Label
from bokeh.models.widgets import DataTable, DateFormatter, TableColumn, FileInput
from pybase64 import b64decode
from bokeh.plotting import figure
import bokeh.plotting as bp

import numpy as np
from bokeh.plotting import figure, curdoc
from bokeh.models.widgets import Button, Dropdown
from bokeh.layouts import column, widgetbox

# sys.path.append('../')
from . import config

#### Constants

client = Client() if (config.computation_resources['mode'] == 'local') else Client(
	config.computation_resources['cluster_ip'])
client.restart()
url = 'https://users.rcc.uchicago.edu/~manorathan/wave4/30_min_segments'
lst_colors = ['red', 'blue', 'green', 'yellow', 'violet']
data_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
readings_folder = os.path.join(data_folder, 'readings')
output_folder = os.path.join(data_folder, 'output')
annotations_fname = os.path.join(output_folder, 'annotations.csv')
lst_users = list(sorted(['manu', 'phil', 'megan', 'hannah', 'joscelyn', 'martha', 'kristen']))


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
		# print(df_signal.head())
		df_signal = df_signal.map_partitions(lambda pdf: pdf.assign(**dict([(col, pd.to_numeric(pdf[col],
		                                                                                        errors='coerce'))
		                                                                    for col in pdf.columns]
		                                                                   ))
		                                     ).set_index('timestamp', sorted=True)
		# df_signal['timestamp'] = df_signal['timestamp']
		# print(df_signal.head())
		lst_timestamps = df_signal.index.compute().tolist()
		# print(lst_timestamps[0])
		lst_columns = [df_signal.index.name] + df_signal.columns
	anchor_timestamp = float(lst_timestamps[0])
	time_input.value = datetime.utcfromtimestamp(anchor_timestamp).strftime('%b %d %Y %I:%M %p')
	# print(lst_timestamps[0])
	# print("Anchor timestamp: {0}".format(anchor_timestamp))
	# print("Anchor timestamp (str): {0}".format((datetime.strptime(time_input.value, '%b %d %Y %I:%M %p') - datetime(1970, 1, 1)).total_seconds()))
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
		min_timestamp_index = next(
			x[0] for x in enumerate(lst_timestamps) if float(x[1]) > anchor_timestamp - (windowsize / 2)) + 1
		min_timestamp_index = max(2, min_timestamp_index)
		max_timestamp_index = next(
			x[0] for x in enumerate(lst_timestamps) if float(x[1]) > anchor_timestamp + (windowsize / 2))
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
		df_signal_to_display = df_signal.loc[(df_signal.index >= ((anchor_timestamp - (windowsize / 2)))) &
		                                     (df_signal.index <= (anchor_timestamp + (windowsize / 2)))].compute()
		df_signal_to_display = df_signal_to_display.reset_index(drop=False)
		df_signal_to_display = df_signal_to_display.sort_values(by='timestamp', ascending=True)
	df_signal_to_display = df_signal_to_display.rename(columns={'timestamp': 'epoch'})
	df_signal_to_display = df_signal_to_display.assign(
		timestamp=pd.to_datetime(df_signal_to_display['epoch'], unit='s', errors='coerce'),
		timestamp_string=pd.to_datetime(df_signal_to_display['epoch'], unit='s', errors='coerce').astype(str))
	# print(df_signal_to_display.head())

	# df_signal_to_display = df_signal_to_display.assign(
	#     timestamp=pd.to_datetime(df_signal_to_display['timestamp'], errors='coerce', unit='s'),
	#     timestamp_str=pd.to_datetime(df_signal_to_display['timestamp'], unit='s').astype(str))
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


def make_plot(srs, colsource, data_annot_chairstand, data_annot_3m_walk, data_annot_6min_walk,title):
	tools = "hover,box_select"
	p = figure(plot_height=300, tools=tools, toolbar_location='left',
	           x_axis_type="datetime",
	           x_axis_location="above",
	           background_fill_color="#efefef", x_range=(srs[400], srs[3000]), title=title, width=1520)
	p.xaxis.axis_label = 'Timestamp'

	lst_col = ['x', 'y', 'z']  # + df_signal.columns.difference(['timestamp', 'x', 'y', 'z']).tolist()
	lst_line_plots = []
	for (colr, leg) in zip(lst_colors, lst_col):
		lst_line_plots.append(p.line('timestamp', leg, color=colr, legend_label=leg, source=colsource, name='wave',
		                             nonselection_alpha=0.4, selection_alpha=1))
		p.scatter('timestamp', leg, color=None, legend_label=leg, source=colsource, name='wave')

	p.xaxis.formatter = DatetimeTickFormatter(days=["%m/%d %H:%M"],
	                                          months=["%m/%d %H:%M"],
	                                          hours=["%m/%d %H:%M"],
	                                          minutes=["%m/%d %H:%M"])
	hover = p.select(dict(type=HoverTool))
	hover.tooltips = [("timestamp", "@timestamp_string")]
	hover.renderers = lst_line_plots

	select = figure(title="Drag the middle and edges of the selection box to change the range above",
	                plot_height=130, y_range=p.y_range,
	                x_axis_type="datetime", y_axis_type=None,
	                tools="", toolbar_location=None, background_fill_color="#efefef", width=1520)

	for (colr, leg) in zip(lst_colors, lst_col):
		select.line('timestamp', leg, color=colr, source=colsource, nonselection_alpha=0.4, selection_alpha=1)
	select.ygrid.grid_line_color = None
	select.xaxis.formatter = DatetimeTickFormatter(days=["%m/%d %H:%M"],
	                                               months=["%m/%d %H:%M"],
	                                               hours=["%m/%d %H:%M"],
	                                               minutes=["%m/%d %H:%M"])

	# annot_chairstand = Quad()
	p.quad(left="start_time", right="end_time", top=5, bottom=-5, fill_color="cyan", fill_alpha=0.2,
	       source=data_annot_chairstand, legend_label='chairstand')
	p.quad(left="start_time", right="end_time", top=5, bottom=-5, fill_color="magenta", fill_alpha=0.2,
	       source=data_annot_3m_walk, legend_label='3m_walk')
	p.quad(left="start_time", right="end_time", top=5, bottom=-5, fill_color="yellow", fill_alpha=0.2,
	       source=data_annot_6min_walk, legend_label='6min_walk')
	# annot_3m_walk = Quad(left="start_time", right="end_time", top=5, bottom=-5, fill_color="blue", fill_alpha=0.2)
	# p.add_glyph(data_annot_3m_walk, annot_3m_walk)
	# annot_6min_walk = Quad(left="start_time", right="end_time", top=5, bottom=-5, fill_color="green", fill_alpha=0.2)
	# p.add_glyph(data_annot_6min_walk, annot_6min_walk)
	#
	# annot_chairstand = Arrow(end=NormalHead(), x_start='start_time', y_start=0, x_end='end_time',
	#                          y_end=0, source=data_annot_chairstand, line_color='red')
	# annot_3m_walk = Arrow(end=NormalHead(), x_start='start_time', y_start=0, x_end='end_time',
	#                       y_end=0, source=data_annot_3m_walk, line_color='blue')
	# annot_6min_walk = Arrow(end=NormalHead(), x_start='start_time', y_start=0, x_end='end_time',
	#                         y_end=0, source=data_annot_6min_walk, line_color='green')

	# lblset_chairstand = LabelSet(x='start_time', y=0, y_offset=100, level='glyph', text="chairstand",
	#                              source=data_annot_chairstand)
	# lblset_3m_walk = LabelSet(x='start_time', y=0, y_offset=100, level='glyph',text="3m_walk",
	#                           source=data_annot_3m_walk)
	# lblset_6min_walk = LabelSet(x='start_time', y=200, y_offset=100, level='glyph',text="6min_walk",
	#                             source=data_annot_6min_walk)

	# p.add_layout(annot_chairstand)
	# p.add_layout(annot_3m_walk)
	# p.add_layout(annot_6min_walk)
	# p.add_layout(lblset_chairstand)
	# p.add_layout(lblset_3m_walk)
	# p.add_layout(lblset_6min_walk)

	return p, select


### Util functions

def cleanup_annotations(pdf):
	pdf = pdf.sort_values(by=['user', 'fname', 'artifact', 'annotated_at'], ascending=False)
	# pdf = pdf.drop_duplicates(['user', 'fname', 'artifact'], keep='first')
	if pdf.shape[0] > 0:
		pdf = pdf.assign(start_time=pd.to_datetime(pdf['start_time'], errors='coerce'),
		                 end_time=pd.to_datetime(pdf['end_time'], errors='coerce'))
	return pdf


### Global Variables

df_signal = None
pdf_results = pd.DataFrame(columns=['fname', 'artifact', 'start_epoch', 'end_epoch', 'start_time', 'end_time'])
pdf_annotations = pd.read_csv(annotations_fname) if os.path.exists(annotations_fname) else pd.DataFrame(
	columns=['fname', 'artifact', 'start_epoch', 'end_epoch', 'start_time', 'end_time',
	         'annotated_at', 'user'])
pdf_annotations = cleanup_annotations(pdf_annotations)
pdf_displayed_annotations = pdf_annotations.copy()
anchor_timestamp = 0
windowsize = 3600

selected_data = ColumnDataSource(data=dict(start_time=[], end_time=[]))
selected_annotations = ColumnDataSource(data=dict(fname=[], artifact=[], start_time=[], end_time=[], annotated_at=[], user=[]))
data_annot_chairstand = ColumnDataSource(data=dict(start_epoch=[], end_epoch=[], start_time=[], end_time=[], artifact=[]))
data_annot_3m_walk = ColumnDataSource(data=dict(start_epoch=[], end_epoch=[], start_time=[], end_time=[], artifact=[]))
data_annot_6min_walk = ColumnDataSource(data=dict(start_epoch=[], end_epoch=[], start_time=[], end_time=[], artifact=[]))
data_annotations = ColumnDataSource(data=dict())
lst_fnames = get_filenames()

lst_columns = []
lst_timestamps = []
rowread_start = 0
rowread_end = 2000

### Widgets

time_input = TextInput(value="", title="Enter anchor time in the format Jun 1 2005 1:33 PM")
windowsize_input = TextInput(value="", title="Enter anchor windowsize in seconds")
# file_input = FileInput(accept=".csv")

selected_data_title = Div(text="<b>Selected segment bounds</b>")
selected_annotations_title = Div(text="<b>Selected annotations</b>")
buffer_text = Div(text="&nbsp;")

selected_datatable_columns = [
	TableColumn(field="start_time", title="Start time"),
	TableColumn(field="end_time", title="End time"), ]

selected_annotations_table_columns = [
         TableColumn(field="fname", title="Filename"),
        TableColumn(field="artifact", title="Artifact"),
    TableColumn(field="start_time", title="Start Time"),
    TableColumn(field="end_time", title="End Time"),
TableColumn(field="annotated_at", title="Annoted at"),
    TableColumn(field="user", title="User"),
]

selected_data_table = DataTable(
	source=selected_data,
	columns=selected_datatable_columns,
	height=200,
	sortable=True,
	selectable=True,
	editable=True,
)

selected_annotations_table = DataTable(
  source=selected_annotations,
  columns=selected_annotations_table_columns,
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

btn_6min_walk = Button(
	label="Mark 6 min walk",
	button_type="success",
	width=20
)

btn_remove_annotations = Button(
    label="Remove annotations",
    button_type="success",
    width=20
)

btn_export = Button(
	label="Export annotations",
	button_type="success",
	width=20
)

file_picker = Select(value=lst_fnames[0], title='Select a file', options=sorted(lst_fnames))
user_setter = Select(value=lst_users[0], title='Annotate as', options=sorted(lst_users))

### Dashboard init

fname = os.path.join(readings_folder, lst_fnames[0])
uname = lst_users[0]
get_filedata()
srs, colsource = update_datasources()
p, select = make_plot(srs, colsource, data_annot_chairstand, data_annot_3m_walk, data_annot_6min_walk, file_picker.value)

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
	update_annotations()

def update_selection():
	global pdf_annotations
	global pdf_displayed_annotations
	global fname
	global uname
	pdf_displayed_annotations = pdf_annotations.loc[(pdf_annotations['user'] == uname) &
	                                                (pdf_annotations['fname'] == os.path.basename(fname))]
	selected_indices = colsource.selected.indices
	pdf_selected_data = pd.DataFrame(columns=['start_time',
	                                         'end_time'])
	pdf_selected_annotations = pd.DataFrame(columns=pdf_annotations.columns)
	if bool(selected_indices):
		min_index = min(selected_indices)
		max_index = max(selected_indices)

		pdf_selected_data = pd.DataFrame({'start_time': colsource.data['timestamp_string'][min_index],
		                                 'end_time': colsource.data['timestamp_string'][max_index],
		                                }, index=[0])

		pdf_selected_annotations = pdf_displayed_annotations.loc[
		    pd.to_numeric(pdf_displayed_annotations['start_epoch'], errors='coerce').between(
		        colsource.data['epoch'][min_index], colsource.data['epoch'][max_index], inclusive=True) &
		    pd.to_numeric(pdf_displayed_annotations['end_epoch'], errors='coerce').between(
		        colsource.data['epoch'][min_index], colsource.data['epoch'][max_index], inclusive=True)]

	new_selected = bp.ColumnDataSource(pdf_selected_data)
	new_selected_annotations = bp.ColumnDataSource(pdf_selected_annotations)
	selected_data.data.update(new_selected.data)
	selected_annotations.data.update(new_selected_annotations.data)
	selected_data_table.update()
	selected_annotations_table.update()

def update_annotations():
	global uname
	global pdf_annotations
	global pdf_displayed_annotations
	pdf_annotations = cleanup_annotations(pdf_annotations)
	pdf_displayed_annotations = pdf_annotations.loc[(pdf_annotations['user'] == uname) &
	                                                 (pdf_annotations['fname'] == os.path.basename(fname))]
	data_annot_chairstand.data.update(
		bp.ColumnDataSource(pdf_displayed_annotations.loc[pdf_displayed_annotations['artifact'] == 'chair_stand']
		                    [['start_epoch', 'end_epoch', 'start_time', 'end_time', 'artifact']]).data)
	data_annot_6min_walk.data.update(
		bp.ColumnDataSource(pdf_displayed_annotations.loc[pdf_displayed_annotations['artifact'] == '6min_walk']
		                    [['start_epoch', 'end_epoch', 'start_time', 'end_time', 'artifact']]).data)
	data_annot_3m_walk.data.update(
		bp.ColumnDataSource(pdf_displayed_annotations.loc[pdf_displayed_annotations['artifact'] == '3m_walk']
		                    [['start_epoch', 'end_epoch', 'start_time', 'end_time', 'artifact']]).data)
	data_annotations.data.update(bp.ColumnDataSource(pdf_annotations).data)
	update_selection()

update_annotations()


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
	# btn_chairstand.label = btn_chairstand.label.replace(' (done)', '')
	# btn_3m_walk.label = btn_3m_walk.label.replace(' (done)', '')
	# btn_6min_walk.label = btn_6min_walk.label.replace(' (done)', '')
	update_plot()


def load_user_annotations(attrname, old, new):
	global uname
	uname = user_setter.value
	update_annotations()


def redraw_plots():
	update_plot()


def mark_chairstand():
	global pdf_annotations
	global fname
	global uname
	selected_indices = colsource.selected.indices

	# pdf_results = pdf_results.loc[~((pdf_results['fname'] == file_picker.value) &
	#                                 (pdf_results['artifact'] == 'chair_stand'))]
	if bool(selected_indices):
		min_index = min(selected_indices)
		max_index = max(selected_indices)
		pdf_annotations = pdf_annotations.append(pd.DataFrame({'fname': os.path.basename(fname),
		                                               'artifact': 'chair_stand',
		                                               'start_epoch': colsource.data['epoch'][min_index],
		                                               'end_epoch': colsource.data['epoch'][max_index],
		                                               'start_time': colsource.data['timestamp'][min_index],
		                                               'end_time': colsource.data['timestamp'][max_index],
		                                               'annotated_at': datetime.now(),
		                                               'user': uname
		                                               }, index=[0]))
		# if not btn_chairstand.label.endswith('(done)'):
		# 	btn_chairstand.label = btn_chairstand.label + ' (done)'
	# else:
	# 	btn_chairstand.label = btn_chairstand.label.replace(' (done)', '')
	update_annotations()



def mark_6min_walk():
	global fname
	global pdf_annotations
	global uname
	selected_indices = colsource.selected.indices

	if bool(selected_indices):
		min_index = min(selected_indices)
		max_index = max(selected_indices)
		pdf_annotations = pdf_annotations.append(pd.DataFrame({'fname': os.path.basename(fname),
		                                               'artifact': '6min_walk',
		                                               'start_epoch': colsource.data['epoch'][min_index],
		                                               'end_epoch': colsource.data['epoch'][max_index],
		                                               'start_time': colsource.data['timestamp'][min_index],
		                                               'end_time': colsource.data['timestamp'][max_index],
		                                               'annotated_at': datetime.now(),
		                                              'user': uname
		                                               }, index=[0]))
	# 	if not btn_6min_walk.label.endswith('(done)'):
	# 		btn_6min_walk.label = btn_6min_walk.label + ' (done)'
	# else:
	# 	btn_6min_walk.label = btn_6min_walk.label.replace(' (done)', '')
	update_annotations()


def remove_selected_annotations():
	global pdf_annotations
	global fname
	global uname
	pdf_selected_annotations = pd.DataFrame(columns=pdf_annotations.columns)
	selected_indices = colsource.selected.indices
	if bool(selected_indices):
		min_index = min(selected_indices)
		max_index = max(selected_indices)

		pdf_annotations = pdf_annotations.loc[~(pd.to_numeric(pdf_annotations['start_epoch'], errors='coerce').between(
		        colsource.data['epoch'][min_index], colsource.data['epoch'][max_index], inclusive=True) &
		    pd.to_numeric(pdf_annotations['end_epoch'], errors='coerce').between(
		            colsource.data['epoch'][min_index], colsource.data['epoch'][max_index], inclusive=True) &
		                                      (pdf_annotations['user'] == uname) &
		                                      (pdf_annotations['fname'] == os.path.basename(fname)))]

	new_selected_annotations = bp.ColumnDataSource(pdf_selected_annotations)
	selected_annotations.data.update(new_selected_annotations.data)
	selected_annotations_table.update()
	update_annotations()


def clear_selection():
	colsource.selected.indices = []


def save_annotations():
	global uname
	global fname
	global pdf_annotations
	pdf_old_results = pd.DataFrame(columns=pdf_annotations.columns)
	if os.path.exists(annotations_fname):
		pdf_old_results = pd.read_csv(annotations_fname)
		pdf_old_results = pdf_old_results.assign(annotated_at=pd.to_datetime(pdf_old_results['annotated_at'], errors='coerce'))
	pdf_all_results = pd.concat([pdf_old_results.loc[~((pdf_old_results['user'] == uname) &
	                                                    (pdf_old_results['fname'] == os.path.basename(fname)))],
	                                                 pdf_annotations.loc[((pdf_annotations['user'] == uname) &
	                                                    (pdf_annotations['fname'] == os.path.basename(fname)))]], ignore_index=True).reset_index(drop=True)
	pdf_all_results = cleanup_annotations(pdf_all_results)
	pdf_all_results.to_csv(annotations_fname, index=False)
	pdf_annotations = pdf_all_results
	update_annotations()


def mark_3m_walk():
	global pdf_annotations
	global uname
	global fname
	selected_indices = colsource.selected.indices
	if bool(selected_indices):
		min_index = min(selected_indices)
		max_index = max(selected_indices)

		pdf_annotations = pdf_annotations.append(pd.DataFrame({'fname': os.path.basename(fname),
		                                               'artifact': '3m_walk',
		                                               'start_epoch': colsource.data['epoch'][min_index],
		                                               'end_epoch': colsource.data['epoch'][max_index],
		                                               'start_time': colsource.data['timestamp'][min_index],
		                                               'end_time': colsource.data['timestamp'][max_index],
		                                               'annotated_at': datetime.now(),
		                                               'user': uname
		                                               }, index=[0]))
	# 	if not btn_3m_walk.label.endswith('(done)'):
	# 		btn_3m_walk.label = btn_3m_walk.label + ' (done)'
	# else:
	# 	btn_3m_walk.label = btn_3m_walk.label.replace(' (done)', '')
	update_annotations()


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


def update_selected_tables(attr, old, new):
	update_selection()


### Callback registrations

# file_input.on_change("value", upload_file_data)
windowsize_input.on_change("value", update_windowsize)
time_input.on_change("value", update_anchor_timestamp)
btn_chairstand.on_click(mark_chairstand)
btn_update_plot.on_click(redraw_plots)
btn_3m_walk.on_click(mark_3m_walk)
btn_6min_walk.on_click(mark_6min_walk)
btn_clear_selection.on_click(clear_selection)
btn_remove_annotations.on_click(remove_selected_annotations)
btn_export.on_click(save_annotations)
# btn_export.js_on_click(CustomJS(args=dict(source=annotations),
#                             code=open(os.path.join(os.path.dirname(__file__), 'js', "download.js")).read()))
file_picker.on_change('value', plot_new_file)
user_setter.on_change('value', load_user_annotations)

colsource.selected.on_change("indices", update_selected_tables)

### Layout

layout = grid(column(row(column(row(file_picker, sizing_mode='stretch_width'),
                                row(time_input, windowsize_input, sizing_mode='stretch_width')
                                ),
                         column(row(user_setter, sizing_mode='stretch_width'),
                                # row(Spacer(height=1, sizing_mode='stretch_width')),
                                row(btn_update_plot, btn_clear_selection, sizing_mode='stretch_width'),
                                sizing_mode='stretch_width')),
                     row(column(p, select)),
                     row(column(selected_data_title, selected_data_table, sizing_mode='stretch_both'), sizing_mode='stretch_both'),
                     row(column(selected_annotations_title, selected_annotations_table, sizing_mode='stretch_both'), sizing_mode='stretch_both'),
                     row(btn_chairstand, btn_3m_walk, btn_6min_walk, sizing_mode='stretch_width'),
                     row(btn_remove_annotations,
                         btn_export, sizing_mode='stretch_width'), sizing_mode='stretch_both'
                     )
              #
              )

bokeh_doc = curdoc()
bokeh_doc.add_root(layout)

bokeh_doc.title = "Visualize chair stands & 3M walks"
