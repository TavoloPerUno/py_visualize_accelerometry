import pandas as pd
import os
from datetime import datetime, timedelta
import subprocess

import io

from bokeh.layouts import grid, row
from bokeh.models import TextInput, Div, ColumnDataSource, RangeTool, Select, DatetimeTickFormatter
from bokeh.models.widgets import DataTable, TableColumn
import bokeh.plotting as bp
from bokeh.plotting import figure, curdoc
from bokeh.models.widgets import Button
from bokeh.layouts import column

#### Constants

url = 'https://users.rcc.uchicago.edu/~manorathan/wave4/30_min_segments'
lst_colors = ['red', 'blue', 'green', 'yellow', 'violet']
data_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
readings_folder = os.path.join(data_folder, 'readings')
output_folder = os.path.join(data_folder, 'output')
annotations_fname = os.path.join(output_folder, 'annotations.csv')
lst_users = list(sorted(['manu', 'phil', 'megan', 'hannah', 'joscelyn', 'martha', 'kristen']))


#### Intial data loaders

def get_filenames():
	lst_files = [f for f in os.listdir(readings_folder) if os.path.splitext(f)[1].lower() == '.h5']
	return lst_files


def get_filedata():
	"""This function accepts a filename as input and returns the passed file's timestamp index & ColumnDataSource version of the file data
	  :param fname str: signal filename
	  :return: numpy.ndarray, bokeh.models.ColumnDataSource
	"""
	global pdf_signal_to_display
	global fname
	global anchor_timestamp
	global lst_columns
	global windowsize
	if anchor_timestamp is None:
		print("Loading {0}".format(fname))
		windowsize = 3600
		windowsize_input.value = str(windowsize)
		anchor_timestamp = pd.read_hdf(fname, "readings", start=0,
		                               stop=1)['timestamp'].dt.strftime('%b %d %Y %I:%M %p').values[0]
		# cmd_read_first_timestamp = 'head -n 2 "{0}" | tail -n 1 |'.format(fname) + r"""awk 'BEGIN{FS=","} {print $1}'"""
		# process = subprocess.Popen(cmd_read_first_timestamp, stdout=subprocess.PIPE, shell=True)
		# anchor_timestamp = process.communicate()[0]
		# anchor_timestamp = float(anchor_timestamp.decode("utf-8").replace("\n", ""))

	time_input.value = anchor_timestamp #datetime.utcfromtimestamp(anchor_timestamp).strftime('%b %d %Y %I:%M %p')
	print("Loading a {0} minute window centered around {1} from {2}".format(int(windowsize/60),
	                                                                        anchor_timestamp,
	                                                                        fname))
	start_timestamp = (datetime.strptime(anchor_timestamp, '%b %d %Y %I:%M %p') -
	              timedelta(seconds=int(windowsize/2))).strftime('%b %d %Y %I:%M %p')
	end_timestamp = (datetime.strptime(anchor_timestamp, '%b %d %Y %I:%M %p') +
	              timedelta(seconds=int(windowsize / 2))).strftime('%b %d %Y %I:%M %p')
	pdf_signal_to_display = pd.read_hdf(fname, 'readings',
	                where="(timestamp >= Timestamp('{0}')) & (timestamp <= Timestamp('{1}'))".format(start_timestamp,
	                                                                                                 end_timestamp))
	# cmd_fetch_readings = """awk -F, -v from=""" + str(anchor_timestamp - (windowsize / 2)) + """ -v to=""" + str(anchor_timestamp + (windowsize / 2)) + """ '$1 <= from { next } $1 >= to { exit } 1' '""" + fname + """'"""
	# process = subprocess.Popen(cmd_fetch_readings, stdout=subprocess.PIPE, shell=True)
	# pdf_signal_to_display = io.StringIO(process.communicate()[0].decode('utf-8'))
	# pdf_signal_to_display = pd.read_csv(pdf_signal_to_display, sep=",", header=None,
	#                                     dtype=dict([("timestamp", "float64"),
	#                                                 ("x", "float32"),
	#                                                 ("y", "float32"),
	#                                                 ("z", "float32"),
	#                                                 ("light", "float32"),
	#                                                 ("button", "int8"),
	#                                                 ("temperature", "float32")]), names=lst_columns)
	return None


def update_datasources():
	get_filedata()
	global pdf_signal_to_display
	# pdf_signal_to_display = pdf_signal_to_display.rename(columns={'timestamp': 'epoch'})
	# pdf_signal_to_display = pdf_signal_to_display.assign(
	# 	timestamp=pd.to_datetime(pdf_signal_to_display['epoch'], unit='s', errors='coerce')
	# )


	print("Column datatypes:")
	print(pdf_signal_to_display.head().dtypes)
	print("Anchor timestamp (str): {0}".format(anchor_timestamp))
	print("Anchor timestamp : {0}".format(
		(datetime.strptime(time_input.value, '%b %d %Y %I:%M %p') - datetime(1970, 1, 1)).total_seconds()))
	print("N rows:{0}".format(pdf_signal_to_display.shape[0]))
	dates = pdf_signal_to_display['timestamp'].values
	source = bp.ColumnDataSource(pdf_signal_to_display)

	return dates, source


def make_plot(srs, colsource, data_annot_chairstand, data_annot_3m_walk, data_annot_6min_walk,title):
	tools = "box_select"
	p = figure(plot_height=300, tools=tools, toolbar_location='left',
	           x_axis_type="datetime",
	           x_axis_location="above",
	           background_fill_color="#efefef", x_range=(srs[400], srs[3000]), title=title, sizing_mode='stretch_width')
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

	select = figure(title="Drag the middle and edges of the selection box to change the range above",
	                plot_height=130, y_range=p.y_range,
	                x_axis_type="datetime", y_axis_type=None,
	                tools="", toolbar_location=None, background_fill_color="#efefef", sizing_mode='stretch_width')

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

	p.legend.background_fill_alpha = 0.0
	p.legend.label_text_font_size = "7pt"
	return p, select


### Util functions

def cleanup_annotations(pdf):
	pdf = pdf.sort_values(by=['user', 'fname', 'artifact', 'annotated_at'], ascending=False)
	if pdf.shape[0] > 0:
		pdf = pdf.assign(start_time=pd.to_datetime(pdf['start_time'], errors='coerce'),
		                 end_time=pd.to_datetime(pdf['end_time'], errors='coerce'))
	return pdf


### Global Variables

pdf_signal_to_display = None
pdf_results = pd.DataFrame(columns=['fname', 'artifact', 'start_epoch', 'end_epoch', 'start_time', 'end_time'])
pdf_annotations = pd.read_csv(annotations_fname) if os.path.exists(annotations_fname) else pd.DataFrame(
	columns=['fname', 'artifact', 'start_epoch', 'end_epoch', 'start_time', 'end_time',
	         'annotated_at', 'user'])
pdf_annotations = cleanup_annotations(pdf_annotations)
pdf_displayed_annotations = pdf_annotations.copy()
anchor_timestamp = None
windowsize = 3600

selected_data = ColumnDataSource(data=dict(start_time=[], end_time=[]))
selected_annotations = ColumnDataSource(data=dict(fname=[], artifact=[], start_time=[], end_time=[], annotated_at=[], user=[]))
data_annot_chairstand = ColumnDataSource(data=dict(start_epoch=[], end_epoch=[], start_time=[], end_time=[], artifact=[]))
data_annot_3m_walk = ColumnDataSource(data=dict(start_epoch=[], end_epoch=[], start_time=[], end_time=[], artifact=[]))
data_annot_6min_walk = ColumnDataSource(data=dict(start_epoch=[], end_epoch=[], start_time=[], end_time=[], artifact=[]))
data_annotations = ColumnDataSource(data=dict())
lst_fnames = get_filenames()

lst_columns = ["timestamp","x","y","z","light","button","temperature"]
lst_timestamps = []
rowread_start = 0
rowread_end = 2000

### Widgets

time_input = TextInput(value="", title="Enter anchor time in the format Jun 1 2005 1:33 PM")
windowsize_input = TextInput(value="", title="Enter anchor windowsize in seconds")

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
	height=200, height_policy='auto',
	sortable=True,
	selectable=True,
	editable=True,
)

selected_annotations_table = DataTable(
  source=selected_annotations,
  columns=selected_annotations_table_columns,
    height=200, height_policy='auto',
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
	pdf_selected_annotations = pd.DataFrame(columns=['fname', 'artifact', 'start_epoch', 'end_epoch', 'start_time', 'end_time',
	         'annotated_at', 'user'])
	if bool(selected_indices):
		min_index = min(selected_indices)
		max_index = max(selected_indices)

		pdf_selected_data = pd.DataFrame({'start_time': colsource.data['timestamp'][min_index],
		                                 'end_time': colsource.data['timestamp'][max_index],
		                                }, index=[0])
		pdf_selected_data = pdf_selected_data.assign(**dict([(col, pdf_selected_data[col].astype(str))
		                                                                   for col in ['start_time', 'end_time']]))

		pdf_selected_annotations = pdf_displayed_annotations.loc[
		    pd.to_datetime(pd.to_numeric(pdf_displayed_annotations['start_epoch'], errors='coerce'), unit='s', errors='coerce').between(
		        colsource.data['timestamp'][min_index], colsource.data['timestamp'][max_index], inclusive=True) &
		    pd.to_datetime(pd.to_numeric(pdf_displayed_annotations['end_epoch'], errors='coerce'), unit='s', errors='coerce').between(
		        colsource.data['timestamp'][min_index], colsource.data['timestamp'][max_index], inclusive=True)]
		pdf_selected_annotations = pdf_selected_annotations.assign(**dict([(col, pdf_selected_annotations[col].astype(str))
		                                                                   for col in ['start_time', 'end_time']]))

	new_selected = bp.ColumnDataSource(pdf_selected_data)
	print(pdf_selected_annotations[['fname', 'artifact', 'start_time', 'end_time',
	         'annotated_at', 'user']])
	new_selected_annotations = bp.ColumnDataSource(pdf_selected_annotations[['fname', 'artifact', 'start_time', 'end_time',
	         'annotated_at', 'user']])
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


def plot_new_file(attrname, old, new):
	global fname
	global anchor_timestamp
	anchor_timestamp = None
	fname = os.path.join(readings_folder, file_picker.value)
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

	if bool(selected_indices):
		min_index = min(selected_indices)
		max_index = max(selected_indices)
		pdf_new_annotations = pd.DataFrame({'fname': os.path.basename(fname),
		                                               'artifact': 'chair_stand',
		                                               'start_epoch': colsource.data['timestamp'][min_index],
		                                               'end_epoch': colsource.data['timestamp'][max_index],
		                                               'start_time': colsource.data['timestamp'][min_index],
		                                               'end_time': colsource.data['timestamp'][max_index],
		                                               'annotated_at': datetime.now(),
		                                               'user': uname
		                                               }, index=[0])
		pdf_new_annotations = pdf_new_annotations.assign(
			**dict([(col, (pdf_new_annotations[col] - datetime(1970, 1, 1)).dt.total_seconds())
			        for col in ['start_epoch', 'end_epoch']] +
			       [(col,
			         pdf_new_annotations[col].astype(str))
			        for col in ['start_time', 'end_time', 'annotated_at']]
			       ))
		pdf_annotations = pdf_annotations.append(pdf_new_annotations)
		print(pdf_annotations)

	update_annotations()



def mark_6min_walk():
	global fname
	global pdf_annotations
	global uname
	selected_indices = colsource.selected.indices

	if bool(selected_indices):
		min_index = min(selected_indices)
		max_index = max(selected_indices)
		pdf_new_annotations = pd.DataFrame({'fname': os.path.basename(fname),
		                                    'artifact': '6min_walk',
		                                    'start_epoch': colsource.data['timestamp'][min_index],
		                                    'end_epoch': colsource.data['timestamp'][max_index],
		                                    'start_time': colsource.data['timestamp'][min_index],
		                                    'end_time': colsource.data['timestamp'][max_index],
		                                    'annotated_at': datetime.now(),
		                                    'user': uname
		                                    }, index=[0])
		pdf_new_annotations = pdf_new_annotations.assign(
			**dict([(col, (pdf_new_annotations[col] - datetime(1970, 1, 1)).dt.total_seconds())
			        for col in ['start_epoch', 'end_epoch']] +
			       [(col,
			         pdf_new_annotations[col].astype(str))
			        for col in ['start_time', 'end_time', 'annotated_at']]
			       ))
		pdf_annotations = pdf_annotations.append(pdf_new_annotations)
	update_annotations()


def remove_selected_annotations():
	global pdf_annotations
	global fname
	global uname
	pdf_selected_annotations = pd.DataFrame(columns=['fname', 'artifact', 'start_time', 'end_time',
	         'annotated_at', 'user'])
	selected_indices = colsource.selected.indices
	if bool(selected_indices):
		min_index = min(selected_indices)
		max_index = max(selected_indices)

		pdf_annotations = pdf_annotations.loc[~(pd.to_datetime(pd.to_numeric(pdf_annotations['start_epoch'], errors='coerce'), unit='s', errors='coerce').between(
		        colsource.data['timestamp'][min_index], colsource.data['timestamp'][max_index], inclusive=True) &
		    pd.to_datetime(pd.to_numeric(pdf_annotations['end_epoch'], errors='coerce'), unit='s', errors='coerce').between(
		            colsource.data['timestamp'][min_index], colsource.data['timestamp'][max_index], inclusive=True) &
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

		pdf_new_annotations = pd.DataFrame({'fname': os.path.basename(fname),
		                                    'artifact': '3m_walk',
		                                    'start_epoch': colsource.data['timestamp'][min_index],
		                                    'end_epoch': colsource.data['timestamp'][max_index],
		                                    'start_time': colsource.data['timestamp'][min_index],
		                                    'end_time': colsource.data['timestamp'][max_index],
		                                    'annotated_at': datetime.now(),
		                                    'user': uname
		                                    }, index=[0])
		pdf_new_annotations = pdf_new_annotations.assign(
			**dict([(col, (pdf_new_annotations[col] - datetime(1970, 1, 1)).dt.total_seconds())
			        for col in ['start_epoch', 'end_epoch']] +
			       [(col,
			         pdf_new_annotations[col].astype(str))
			        for col in ['start_time', 'end_time', 'annotated_at']]
			       ))
		pdf_annotations = pdf_annotations.append(pdf_new_annotations)
	update_annotations()


def update_anchor_timestamp(attr, old, new):
	global anchor_timestamp
	try:
		anchor_timestamp =  (datetime.strptime(time_input.value, '%b %d %Y %I:%M %p') +
		                     timedelta(seconds=0)).strftime('%b %d %Y %I:%M %p')
		# anchor_timestamp = (datetime.strptime(time_input.value, '%b %d %Y %I:%M %p') - datetime(1970, 1, 1)).total_seconds()
	except Exception as ex:
		print(ex)
		print("Invalid time entered {0}".format(str(time_input.value)))


def update_windowsize(attr, old, new):
	global windowsize
	try:
		windowsize = float(str(windowsize_input.value).strip().replace("s", ""))
	except Exception as ex:
		print(ex)
		print("Invalid windowsize entered {0}".format(str(windowsize_input.value)))


def update_selected_tables(attr, old, new):
	update_selection()


### Callback registrations

windowsize_input.on_change("value", update_windowsize)
time_input.on_change("value", update_anchor_timestamp)
btn_chairstand.on_click(mark_chairstand)
btn_update_plot.on_click(redraw_plots)
btn_3m_walk.on_click(mark_3m_walk)
btn_6min_walk.on_click(mark_6min_walk)
btn_clear_selection.on_click(clear_selection)
btn_remove_annotations.on_click(remove_selected_annotations)
btn_export.on_click(save_annotations)
file_picker.on_change('value', plot_new_file)
user_setter.on_change('value', load_user_annotations)

colsource.selected.on_change("indices", update_selected_tables)

### Layout

layout = grid(column(row(column(row(file_picker, sizing_mode='stretch_width'),
                                row(time_input, sizing_mode='stretch_width')
                                ),
                         column(row(user_setter, sizing_mode='stretch_width'),
                                row(windowsize_input, sizing_mode='stretch_width')
                                ),
                         column(row(btn_update_plot, btn_clear_selection, sizing_mode='stretch_width'),
                                row(btn_chairstand, btn_3m_walk, btn_6min_walk, sizing_mode='stretch_width'),
                                row(btn_remove_annotations, btn_export, sizing_mode='stretch_width'),
                                sizing_mode='stretch_width')),
                     row(column(p, select, sizing_mode='stretch_width'), sizing_mode='stretch_width'),
                     row(column(selected_data_title, selected_data_table, sizing_mode='scale_both'),
                         column(selected_annotations_title, selected_annotations_table, sizing_mode='scale_both'),
                         sizing_mode='stretch_both'), sizing_mode='stretch_both'
                     )
              #
              )

bokeh_doc = curdoc()
bokeh_doc.add_root(layout)

bokeh_doc.title = "Visualize chair stands & 3M walks"
