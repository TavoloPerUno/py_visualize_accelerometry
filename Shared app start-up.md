Follow the instructions below to connect to the shared annotation server on the HPC cluster. The script handles everything automatically — it checks for a running server, starts one if needed, and creates the SSH tunnel.

# Preliminary steps (one-time setup)

1. Ensure the conda/Python environment with project dependencies is available on the cluster.
2. Ensure `credentials.json` exists in the project root on the cluster with usernames and passwords for all team members.
3. Each user should edit `slurm/connect.sh` to set their login info:
   - `SSH_USER` — your username on the HPC cluster (default: your local username)
   - `LOGIN_NODE` — your cluster's login/gateway hostname (default: `randi.cri.uchicago.edu`)
   - `REMOTE_DIR` — path to the project directory on the cluster
4. (Optional) Edit `slurm/start_server.sh` to adjust:
   - `PORT` — default `7860`
   - `CREDENTIALS` — path to `credentials.json`
   - Slurm directives (`--time`, `--mem`, `--partition`, etc.)

# Connecting

Run the connect script from your local machine:

```
bash slurm/connect.sh
```

The script will:

1. SSH into the login node
2. Check if a Panel server job is already running on the cluster
3. If no server is running, submit a new Slurm job automatically
4. Wait for the job to start and the server to become ready
5. Retrieve the compute node hostname and port
6. Find an available local port (auto-increments if the default is busy)
7. Create an SSH tunnel through the login node
8. Verify the tunnel is working
9. Open the app in your browser

You will see output like:

```
Connecting to randi.cri.uchicago.edu...
NO_EXISTING_JOB: Submitting new server job...
SUBMITTED_JOB=12345678
WAITING: Job 12345678 is PENDING... (0s)
WAITING: Job 12345678 is PENDING... (5s)

Server info:
  Compute node : compute-node-01
  Remote port  : 7860
  Slurm job    : 12345678
  Local port   : 7860

Opening SSH tunnel: localhost:7860 -> compute-node-01:7860 via randi.cri.uchicago.edu...
Waiting for tunnel to establish...

==========================================
  Tunnel is active!
  Open: http://localhost:7860/visualize_accelerometry/app
==========================================

Press Ctrl+C to close the tunnel.
```

If a server is already running, the script skips the submission step and connects directly.

Log in with the credentials defined in `credentials.json`.

## Manual connection (alternative)

If you prefer to set up the tunnel manually, first find the running job:

```
ssh yourusername@randi.cri.uchicago.edu "cat /path/to/project/slurm/server_info.txt"
```

Then create the tunnel:

```
ssh -N -f -L 7860:compute-node-01:7860 yourusername@randi.cri.uchicago.edu
```

Then open: `http://localhost:7860/visualize_accelerometry/app`

# Stopping the server

When the team is done for the day, stop the server:

```
bash slurm/stop_server.sh
```

This cancels the Slurm job and removes `slurm/server_info.txt`.

Alternatively, cancel the job manually:

```
ssh yourusername@randi.cri.uchicago.edu "scancel jobid"
```

# Troubleshooting

## Port already in use

The `connect.sh` script handles this automatically by trying the next port. If you are connecting manually and the port is unavailable:

```
lsof -i :7860
```

Kill the process holding it:

```
kill -9 processid
```

Then retry the SSH tunnel.

## Tunnel fails to connect

- Verify the Slurm job is still running: `ssh yourusername@randi.cri.uchicago.edu "squeue -j <job_id>"`
- Verify you can SSH to the login node: `ssh yourusername@randi.cri.uchicago.edu`
- Check that the compute node is reachable from the login node

## Blank page or connection refused

- The server may still be starting up. Wait 10–15 seconds and refresh.
- Check the server log: `ssh yourusername@randi.cri.uchicago.edu "cat /path/to/project/slurm/panel-server-<job_id>.log"`

## Job times out waiting to start

- The cluster may be busy. Check queue status: `ssh yourusername@randi.cri.uchicago.edu "squeue --me"`
- Consider adjusting the partition or resource requests in `slurm/start_server.sh`
