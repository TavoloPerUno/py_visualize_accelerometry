# Shared Server Deployment (HPC / Slurm)

## Overview

The application supports a **shared server** deployment model on HPC clusters
managed by Slurm.  A single administrator submits a Slurm batch job that starts
the Panel server on a compute node.  All team members then connect to that
server through SSH tunnels — there is no need for each user to request their own
Slurm allocation or install the application themselves.

This replaces the earlier model where every annotator launched a separate Slurm
job, which was wasteful of cluster resources and harder to coordinate.

## Prerequisites

| Requirement | Details |
|---|---|
| HPC cluster with Slurm | The compute nodes must be reachable from a login/gateway node. |
| SSH access | Every user needs SSH access to the cluster login node. |
| Python environment | The admin who starts the server needs a Python environment with the project dependencies installed (see `requirements.txt`). |
| `credentials.json` | A JSON file mapping usernames to passwords, used by Panel's `--basic-auth` flag for user authentication. |

## Starting the Server (Admin)

### 1. Configure

Open `slurm/start_server.sh` and review the configurable variables at the top.
You can either edit the defaults in the script or export the variables before
running `sbatch`:

| Variable | Default | Description |
|---|---|---|
| `PORT` | `7860` | Port the Panel server listens on. |
| `CREDENTIALS` | `credentials.json` | Path to the credentials JSON file. |
| `APP_PATH` | `visualize_accelerometry/app.py` | Path to the Panel application. |
| `STATUS_FILE` | `slurm/server_info.txt` | Where connection details are written for users. |

The Slurm resource directives are also editable near the top of the script:

- **Partition** — set via `#SBATCH --partition=...` (not set by default; uses cluster default).
- **Time limit** — `--time=7-00:00:00` (7 days).
- **Memory** — `--mem=4G`.
- **CPUs** — `--cpus-per-task=1`.

### 2. Submit the job

```bash
sbatch slurm/start_server.sh
```

Or override variables inline:

```bash
PORT=8080 sbatch slurm/start_server.sh
```

### 3. What happens

1. Slurm allocates a compute node and runs the script.
2. The script writes `slurm/server_info.txt` containing the compute node
   hostname, port, Slurm job ID, and start timestamp.
3. Panel starts serving the app with basic authentication and a random cookie
   secret.

### 4. Verify

```bash
# Check that the job is running
squeue -j <job_id>

# Or inspect the server info file
cat slurm/server_info.txt
```

The Slurm log is written to `slurm/panel-server-<job_id>.log`.

## Connecting (Users)

### Automated (recommended)

#### 1. Configure

Set the `LOGIN_NODE` variable in `slurm/connect.sh` to your cluster's login
node hostname (or export it before running):

```bash
export LOGIN_NODE=login.myuniversity.edu
```

Other overridable variables:

| Variable | Default | Description |
|---|---|---|
| `LOGIN_NODE` | `login.example.com` | SSH gateway / login node. |
| `STATUS_FILE` | `slurm/server_info.txt` | Path to the server info file written by `start_server.sh`. |
| `LOCAL_PORT` | Same as remote `PORT` | Preferred local port; the script auto-increments if it is busy. |

#### 2. Run

```bash
bash slurm/connect.sh
```

#### 3. What the script does

1. Reads `slurm/server_info.txt` to discover the compute node, port, and job
   ID.
2. Validates that the Slurm job is still running via `squeue`.
3. Picks a free local port (starting from the remote port, incrementing up to
   100 times if needed).
4. Opens an SSH tunnel in the background:
   `ssh -N -L <local_port>:<compute_node>:<remote_port> <login_node>`
5. Waits up to 10 seconds for the tunnel to come up, verifying the local port
   is listening.
6. Opens the browser at `http://localhost:<local_port>/visualize_accelerometry/app`.
7. Keeps running until you press **Ctrl+C**, then cleans up the SSH tunnel.

### Manual alternative

If the automated script does not work in your environment, create the tunnel
yourself:

```bash
ssh -N -L 7860:<compute_node>:7860 login.myuniversity.edu
```

Then open <http://localhost:7860/visualize_accelerometry/app> in your browser.

Replace `<compute_node>` with the `NODE` value from `slurm/server_info.txt` and
adjust ports as needed.

### Troubleshooting

| Problem | Solution |
|---|---|
| `server_info.txt not found` | The server has not been started yet. Ask an admin to run `sbatch slurm/start_server.sh`. |
| `Slurm job is no longer active` | The server job ended (time limit, crash, or manual cancel). Check `slurm/panel-server-<job_id>.log` for errors and restart. |
| Local port already in use | The script automatically tries the next port. If you still hit issues, export `LOCAL_PORT=<free_port>` before running. |
| SSH tunnel did not come up | Verify you can SSH to the login node manually (`ssh <login_node>`). Check your SSH config and key setup. The script prints the manual `ssh -N -L ...` command to try directly. |
| Browser shows "connection refused" | The tunnel may have dropped. Re-run `connect.sh`. Also confirm the Slurm job is still running with `squeue -j <job_id>`. |

## Stopping the Server (Admin)

```bash
bash slurm/stop_server.sh
```

The script reads `slurm/server_info.txt`, cancels the Slurm job with `scancel`,
and removes the status file.  If `server_info.txt` does not exist, the script
exits with an error (there is nothing to stop).

## Architecture

```
┌─────────┐      SSH tunnel       ┌────────────┐               ┌──────────────┐
│ Browser  │◄────────────────────►│ Login Node │◄─────────────►│ Compute Node │
│ :7860    │  localhost:7860 ───► │ (gateway)  │  internal net │ Panel :7860   │
└─────────┘                       └────────────┘               └──────────────┘
```

All traffic between the user's machine and the login node travels through the
encrypted SSH tunnel.  The login node forwards packets over the cluster's
internal network to the compute node where Panel is running.
