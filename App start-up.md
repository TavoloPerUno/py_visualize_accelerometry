Follow the instructions below to download the app files, configure python environment, & start wave visualization app.

<<<<<<< HEAD
# Preliminary steps
Set aside folders in your computer to store app code files, for example, `/Documents/pyWorkspace/` and python/conda environment, for example, `/Documents/venvs/`.
=======
# Download/ set up files
>>>>>>> dccc478204c55aeef888b35652591ee63545fa51

## Download/ set up files
Move into your code folder (`/Documents/pyWorkspace/`), and clone the project repository using the below command.
```
git clone --single-branch --branch desktop ssh://git@rcg-git.uchicago.edu:443/accelerometry/py_visualize_accelerometry.git
```
The above command will download the code files to a folder named `py_visualize_accelerometry`.

## Configure conda environment

If you do not have anaconda, use the steps below to download and install anaconda.

```
wget https://repo.anaconda.com/archive/Anaconda3-2020.11-MacOSX-x86_64.sh
bash Anaconda3-2020.11-MacOSX-x86_64.sh
```

Use the code below to create your own conda environment with packages required to run this app.
```
<<<<<<< HEAD
conda env create -f {your_app_code_parent_folder}/py_visualize_accelerometry/environment.yml -p {your_preferred_python_env_folder_path}/{any_env_name}
conda activate {your_preferred_python_env_folder_path}/{your_env_name}
conda init
```

# Adding accelerometry readings files
=======
module load gcc/6.2.0 miniconda3/4.7.10
conda create --prefix <enter/path/to/your/env> --file /gpfs/data/schumm-lab/rcg/codebase/py_visualize_accelerometry/environment.yml
conda activate <enter/path/to/your/env>
conda init
```

# Start dask cluster
## Edit dask config file
>>>>>>> dccc478204c55aeef888b35652591ee63545fa51

Put the files that you want to view into this folder: `{your_app_code_parent_folder}/py_visualize_accelerometry/visualize_accelerometry/data/readings`

Make sure that the files are in csv format and have the following columns: `"timestamp","x","y","z","light","button","temperature"`

Bin files can be converted to csv files using GENEARead package in R. Example R code for bin - csv conversion:

```
install.packages('GENEARead')
library(GENEAread)
file_data <- read.bin(inputfname,
                      verbose = TRUE, do.temp = TRUE, do.volt = TRUE)
write.table(file_data$data.out, outputfname, sep=",", row.names = FALSE)
```

App generated annotations will be saved to: `{your_app_code_parent_folder}/py_visualize_accelerometry/visualize_accelerometry/data/output/annotations.csv`

# Starting and viewing the app

Activate your conda environment:

```
conda activate {your_preferred_python_env_folder_path}/{your_env_name}
```

Set aside a port for the app, example, 5601. Move into py_visualize_accelerometry and execute the below commands.
```
export PYTHONUNBUFFERED=true
bokeh serve --show visualize_accelerometry --unused-session-lifetime 10370000000 --port={your_app_port}
```

Open an internet browser on your local computer and go to this url: `http://localhost:appport/visualize_accelerometry`

<<<<<<< HEAD
To kill the app, press Ctrl+C in the terminal you started the app. Then, find the process using your app_port with the below command:
=======
In a separate terminal on your local computer, ssh tunnel using the below code
`ssh -L appport:computenodehostname:appport username@gardner.cri.uchicago.edu`. Keep this tab open.
>>>>>>> dccc478204c55aeef888b35652591ee63545fa51

```
ps aux | grep {appport}
```

Get the id of the process from the above command's output and kill it with the below command:

```
kill -9 processid
```



