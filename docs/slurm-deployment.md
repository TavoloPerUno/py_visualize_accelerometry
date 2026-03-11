# Shared Server Deployment (HPC / Slurm)

## Overview

The application supports a **shared server** deployment model on HPC clusters
managed by Slurm. Any team member can run the connect script — it automatically
checks for an existing server, starts one if needed, and creates an SSH tunnel.
No dedicated admin is required.

This replaces the earlier model where every annotator launched a separate Slurm
job, which was wasteful of cluster resources and harder to coordinate.

## System Architecture

```{mermaid}
flowchart LR
    subgraph Local Machine
        B[Browser<br/>localhost:7860]
        CS[connect.sh]
    end

    subgraph Login Node
        SSH[SSH Gateway]
    end

    subgraph Compute Node
        P[Panel Server<br/>port 7860]
        CR[credentials.json]
        D[(Accelerometry<br/>Data Files)]
    end

    CS -- "1. SSH in &<br/>check/submit job" --> SSH
    SSH -- "2. sbatch<br/>(if no job running)" --> P
    CS -- "3. SSH tunnel<br/>localhost:7860 → node:7860" --> SSH
    SSH -- "internal network" --> P
    B -- "4. HTTP over tunnel" --> SSH
    P --> CR
    P --> D
```

## Connection Flow

The `connect.sh` script handles everything automatically:

```{mermaid}
flowchart TD
    A[User runs<br/>bash hpc_utils/connect.sh] --> B[SSH into login node]
    B --> C{Panel server<br/>job running?}
    C -- Yes --> E[Read server_info.txt<br/>get NODE & PORT]
    C -- No --> D[Submit sbatch job]
    D --> F{Wait for job<br/>to start}
    F -- "Pending<br/>(poll every 5s)" --> F
    F -- Running --> E
    F -- "Failed / Timeout<br/>(120s)" --> ERR[Exit with error]
    E --> G[Return to<br/>local machine]
    G --> H{Local port<br/>available?}
    H -- Yes --> J[Create SSH tunnel]
    H -- "No (stale tunnel)" --> I[Kill stale SSH tunnel<br/>and reclaim port]
    I --> H
    J --> K{Tunnel<br/>connected?}
    K -- Yes --> L["Open browser at<br/>localhost:PORT/app"]
    K -- "No (10s timeout)" --> ERR2[Exit with error<br/>& show manual command]
    L --> M[Wait for Ctrl+C]
    M --> N[Close tunnel<br/>& exit]
```

## Prerequisites

| Requirement | Details |
|---|---|
| HPC cluster with Slurm | The compute nodes must be reachable from a login/gateway node. |
| SSH access | Every user needs SSH access to the cluster login node. |
| Python environment | A Python environment with the project dependencies must be available on the cluster (see `requirements.txt`). |
| `credentials.json` | A JSON file mapping usernames to passwords, used by Panel's `--basic-auth` flag. |

## Connecting

### 1. One-time setup

Each user edits the variables at the top of `hpc_utils/connect.sh`:

| Variable | Default | Description |
|---|---|---|
| `SSH_USER` | Current local username | Your username on the HPC cluster. |
| `LOGIN_NODE` | `randi.cri.uchicago.edu` | SSH gateway / login node hostname. |
| `REMOTE_DIR` | *(project path on cluster)* | Path to the project directory on the cluster. |
| `LOCAL_PORT` | `7860` | Preferred local port; auto-increments if busy. |

### 2. Run

```bash
bash hpc_utils/connect.sh
```

The script will:

1. SSH into the login node
2. Check if a `panel-server` job is already running
3. If not, submit one via `sbatch` and wait for it to start
4. Retrieve the compute node and port from `server_info.txt`
5. Find a free local port
6. Create an SSH tunnel
7. Verify the tunnel and open the browser
8. Keep running until you press **Ctrl+C**

### Manual alternative

If the automated script does not work in your environment, first find the
server info:

```bash
ssh youruser@randi.cri.uchicago.edu "cat /path/to/project/hpc_utils/server_info.txt"
```

Then create the tunnel:

```bash
ssh -N -L 7860:<compute_node>:7860 youruser@randi.cri.uchicago.edu
```

Open <http://localhost:7860/app> in your browser.

## Server Configuration

The Slurm job is configured in `hpc_utils/start_server.sh`:

| Variable | Default | Description |
|---|---|---|
| `PORT` | `7860` | Port the Panel server listens on. |
| `CREDENTIALS` | `credentials.json` | Path to the credentials JSON file. |
| `APP_PATH` | `visualize_accelerometry/app.py` | Path to the Panel application. |
| `STATUS_FILE` | `hpc_utils/server_info.txt` | Where connection details are written. |

Slurm resource directives (editable in the script):

- **Time limit** — `--time=7-00:00:00` (7 days)
- **Memory** — `--mem=4G`
- **CPUs** — `--cpus-per-task=1`
- **Partition** — not set by default (uses cluster default)

## Stopping the Server

```bash
bash hpc_utils/stop_server.sh
```

Reads `hpc_utils/server_info.txt`, cancels the Slurm job with `scancel`, and
removes the status file.

## Troubleshooting

| Problem | Solution |
|---|---|
| Job times out waiting to start | The cluster may be busy. Check queue status or adjust the partition in `start_server.sh`. |
| Local port already in use | The script auto-increments. To force a specific port: `LOCAL_PORT=8080 bash hpc_utils/connect.sh` |
| SSH tunnel did not come up | Verify you can SSH to the login node manually. The script prints the manual `ssh -N -L ...` command to try. |
| Connection refused in browser | The tunnel may have dropped. Re-run `connect.sh`. Confirm the Slurm job is still running. |
| Blank page after login | Server may be starting up — wait 10–15 seconds. Check `hpc_utils/panel-server-<job_id>.log`. |
