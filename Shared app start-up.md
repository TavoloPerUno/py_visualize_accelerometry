Follow the instructions below to start a shared annotation server on the HPC cluster via Slurm, connect to it, and stop it after use.

# Preliminary steps

1. Ensure the conda/Python environment with project dependencies is available on the cluster.
2. Ensure `credentials.json` exists in the project root with usernames and passwords for all team members.
3. Update `LOGIN_NODE` in `slurm/connect.sh` (line 23) to your cluster's login/gateway hostname (e.g., `randi.cri.uchicago.edu`).
4. (Optional) Edit `slurm/start_server.sh` to adjust:
   - `PORT` — default `7860`
   - `CREDENTIALS` — path to `credentials.json`
   - Slurm directives (`--time`, `--mem`, `--partition`, etc.)

# Starting the server (admin)

One person starts the shared server. All team members then connect to it.

Submit the Slurm job from the project root:

```
sbatch slurm/start_server.sh
```

The script writes connection details to `slurm/server_info.txt`:

```
NODE=compute-node-01
PORT=7860
JOB_ID=12345678
STARTED=2026-03-11T10:00:00-0500
```

Verify the job is running:

```
squeue -u yourusername
```

# Connecting (all users)

Each user runs the tunnel helper from the project root:

```
bash slurm/connect.sh
```

The script will:

1. Read `slurm/server_info.txt` to find the compute node and port
2. Verify the Slurm job is still running
3. Check if the local port (default: same as remote) is available
4. If the port is in use, automatically pick the next available port
5. Create an SSH tunnel through the login node
6. Verify the tunnel connected successfully
7. Open the app in your browser

You will see output like:

```
Server info:
  Compute node : compute-node-01
  Remote port  : 7860
  Slurm job    : 12345678
  Job status   : running
  Local port   : 7860

Opening SSH tunnel: localhost:7860 -> compute-node-01:7860 via randi.cri.uchicago.edu...
Waiting for tunnel to establish...

==========================================
  Tunnel is active!
  Open: http://localhost:7860/visualize_accelerometry/app
==========================================

Press Ctrl+C to close the tunnel.
```

Log in with the credentials defined in `credentials.json`.

## Manual connection (alternative)

If you prefer to set up the tunnel manually:

```
ssh -N -f -L 7860:compute-node-01:7860 yourusername@randi.cri.uchicago.edu
```

Then open: `http://localhost:7860/visualize_accelerometry/app`

# Stopping the server (admin)

When you are done, stop the server:

```
bash slurm/stop_server.sh
```

This cancels the Slurm job and removes `slurm/server_info.txt`.

Alternatively, cancel the job manually:

```
squeue -u yourusername
scancel jobid
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

- Verify the Slurm job is still running: `squeue -j <job_id>`
- Verify you can SSH to the login node: `ssh yourusername@randi.cri.uchicago.edu`
- Check that the compute node is reachable from the login node: `ssh compute-node-01` (from the login node)

## Blank page or connection refused

- The server may still be starting up. Wait 10–15 seconds and refresh.
- Check the server log: `cat slurm/panel-server-<job_id>.log`
