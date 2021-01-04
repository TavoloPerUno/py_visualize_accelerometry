Follow the instructions below to configure python environment, start dask cluster on Gardner to process large accelerometry files & start wave visualization app.

# Download/ set up files

Clone this repository to your user folder within a labshare. 
```
git clone ssh://git@rcg-git.uchicago.edu:443/accelerometry/py_visualize_accelerometry.git
```

Add execute permissions to hpc util files.
```
chmod +x </enter/path/to/projectfolder>/py_visualize_accelerometry/hpc_utils/dask_on_gardner.sh
```


# Configure conda environment 
Skip this section if you have access to the conda environment `/gpfs/data/schumm-lab/software/conda-env/py38`

Use the code below to create your own conda environment with packages required to run this app. I recommend choosing a conda environment location inside a labshare and not in your personal home folder as the allotted memory limits on CRI is typically not enough to host several conda environments.
```
module load gcc/6.2.0 miniconda3/4.7.10
conda create --prefix <enter/path/to/your/env> --file /gpfs/data/schumm-lab/rcg/codebase/py_visualize_accelerometry/environment.yml
conda activate <enter/path/to/your/env>
conda init
```

# Start dask cluster
## Edit dask config file

Open `</enter/path/to/projectfolder>/py_visualize_accelerometry/hpc_utils/dask_on_gardner.sh` and edit as below
* Update dashboard port in line 6. Make sure you discuss this with me to avoid port number conflicts.
* Update extra_arg in line 7. Edit conda env path and your home path.
* Edit conda env path in line 12
* Edit project folder location in line 14
* Edit scratch folder location in line 16

## Start dask cluster
```
cd </enter/path/to/projectfolder>/py_visualize_accelerometry/hpc_utils
nohup ./dask_on_gardner.sh > dask.log 2>&1 &
```

Make sure that the above line doesn't exit with errors. Open dask.log file and note down dask ip and dashboard port (lines 14 & 15).

Open `</enter/path/to/projectfolder>/py_visualize_accelerometry/visualize_accelerometry/config.py` and update dask ip and dashboard port.


# Start the app
## Edit app start up parameters

Open `</enter/path/to/projectfolder>/py_visualize_accelerometry/hpc_utils/bokeh_on_gardner.pbs` and edit as below
* Edit Gardner job output & error file locations (lines 5 & 6)
* Edit app port (line 8). Make sure you discuss this with me to avoid port number conflicts.
* Edit conda env location (line 13)
* Edit project folder location (line 14)

## Submit Gardner job
```
qsub </enter/path/to/projectfolder>/py_visualize_accelerometry/hpc_utils/bokeh_on_gardner.pbs
```
 Check app start-up status using the log file, `</enter/path/to/projectfolder>/py_visualize_accelerometry/logs/bokeh.log`

Note down the compute node hostname using Gardner job output file.

## View bokeh app

In a separate terminal on your local computer, ssh tunnel using the below code
`ssh -L appport:computenodehostname:appport username@gardner.cri.uchicago.edu`. Keep this tab open.

Open an internet browser on your local computer and go to this url: `http://localhost:appport/visualize_accelerometry`

# Clearing your gardner jobs & closing the app

Use qstat to view the job id and use qdel to kill it.  Use the code below to kill all your gardner jobs:

`qselect -u username | xargs qdel`

Kill your dask cluster job to free dask dashboard port. You can find the process id using `ps aux | grep dask`

