> **Note:** This documents the legacy per-user PBS workflow. For the recommended shared server approach, see [Shared app start-up.md](Shared%20app%20start-up.md) — just run `bash hpc_utils/connect.sh`.

Follow the instructions below to submit a job on Randi to start the visualization app and terminate it after use.

# Preliminary steps

1. Copy `hpc_utils/start_app_on_randi.pbs` to your user folder.
2. Update the output and error file locations (lines 3 and 4) to point to your own log directory.
3. Update the conda environment path on line 18 if your environment is in a different location.
4. Update the project directory path on line 20 to match your codebase location.

# Starting and viewing the app

We use a SLURM job to run the app on a compute node.

To start the app, go to the folder where you copied `start_app_on_randi.pbs` and execute:

```
sbatch start_app_on_randi.pbs
```

Get information on the node your job is running on (the node will be shown in the NODELIST column):

```
squeue -u yourusername
```

Open a new terminal and create an SSH tunnel to the compute node on port 5601:

```
ssh -N -f -L 5601:nodename:5601 yourusername@randi.cri.uchicago.edu
```

Open an internet browser on your local computer and go to: `http://localhost:5601/visualize_accelerometry/app`

You will be prompted to log in. Use the credentials defined in `credentials.json` in the project root.

To stop the app, find the SLURM job id and cancel it:

```
squeue -u yourusername
scancel jobid
```

# Troubleshooting SSH tunnelling

If the port is unavailable for tunneling, find and kill the process holding it:

```
ps aux | grep 5601
```

Get the process id from the output and kill it:

```
kill -9 processid
```
