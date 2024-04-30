Follow the instructions below to submit a job on Randi to start the visualization app and terminate it after use.

# Preliminary steps
Copy `hpc_utils/start_app_on_randi.pbs` to your user folder. Update the output and error file locations (lines 3 and 4).

# Starting and viewing the app

We will use Slurm job to run the app.

To start the app, go to the folder where you copied `start_app_on_randi.pbs` file and execute the command below.

`sbatch start_app_on_randi.pbs`

Get information on the node your job is running on using the below command (node will be displayed in nodelist column in the output:

`squeue -u yourusername`

Open a new new terminal and SSH tunnel into the above node via port 5601, with the below command:

ssh -L 5601:nodename:5601 yourusername@randi.cri.uchicago.edu

Open an internet browser on your local computer and go to this url: `http://localhost:5601/visualize_accelerometry`

To kill the app, find the SLURM job id of the app and use `scancel jobid`.

# Troubleshooting SSH tunnelling

If the port is unavailable for tunneling, clear it using the below sequence of steps:

```
ps aux | grep 5601
```

Get the id of the process from the above command's output and kill it with the below command:

```
kill -9 processid
```



