#!/usr/bin/env bash
#
# connect.sh — Self-service connection to the shared Panel annotation server.
#
# This script handles everything automatically:
#   1. SSHs into the login node
#   2. Checks if a Panel server job is already running
#   3. If not, submits the Slurm job and waits for it to start
#   4. Retrieves the compute node and port
#   5. Creates an SSH tunnel with automatic local port selection
#   6. Verifies the tunnel and opens the browser
#
# No admin needed — any user can run this.
#
# Usage:
#   bash hpc_utils/connect.sh
#
# Overridable variables (export before running, or edit defaults below):
#   SSH_USER      — Your username on the HPC cluster (default: current user)
#   LOGIN_NODE    — SSH gateway / login node
#   REMOTE_DIR    — Project directory on the HPC cluster
#   JOB_NAME      — Slurm job name to search for (default: py_accel_viewer)
#   LOCAL_PORT    — Preferred local port; auto-increments if busy (default: 7860)

set -euo pipefail

# ---------------------------------------------------------------------------
# Configurable defaults — EDIT THESE for your environment
# ---------------------------------------------------------------------------
SSH_USER="${SSH_USER:-$(whoami)}"
LOGIN_NODE="${LOGIN_NODE:-randi.cri.uchicago.edu}"
REMOTE_DIR="${REMOTE_DIR:-/gpfs/data/nshap-lab/users/mmurugesan/projects/accelerometry/codebase/py_visualize_accelerometry_panel/py_visualize_accelerometry}"
JOB_NAME="${JOB_NAME:-py_accel_viewer}"
LOCAL_PORT="${LOCAL_PORT:-7860}"
STATUS_FILE="hpc_utils/server_info.txt"

# ---------------------------------------------------------------------------
# SSH connection multiplexing — authenticate once, reuse for all SSH calls
# ---------------------------------------------------------------------------
SSH_DEST="${SSH_USER}@${LOGIN_NODE}"
SSH_CONTROL_PATH="/tmp/ssh-accel-$$"
SSH_OPTS=(-o "ControlPath=${SSH_CONTROL_PATH}")

# Open a persistent control connection (user authenticates here — once)
echo "Authenticating to ${SSH_DEST}..."
ssh -fNM -o "ControlMaster=yes" -o "ControlPath=${SSH_CONTROL_PATH}" -o "ControlPersist=12h" "${SSH_DEST}"

# Note: cleanup of the control connection is handled by the main cleanup()
# trap set in Step 4 below.

# ---------------------------------------------------------------------------
# Helper: check if a local port is in use
# ---------------------------------------------------------------------------
is_port_in_use() {
    if command -v lsof &>/dev/null; then
        lsof -i ":$1" &>/dev/null
    elif command -v ss &>/dev/null; then
        ss -tlnp "sport = :$1" 2>/dev/null | grep -q "$1"
    else
        python3 -c "
import socket, sys
s = socket.socket()
try:
    s.bind(('127.0.0.1', $1))
    s.close()
    sys.exit(1)
except OSError:
    sys.exit(0)
"
    fi
}

# ---------------------------------------------------------------------------
# Step 1: SSH to login node and check for / start the server
# ---------------------------------------------------------------------------
echo "Checking for running server on ${SSH_DEST}..."

# Run a remote script that:
#   - Checks if a panel-server job is already running
#   - If not, submits one and waits for it to start
#   - Outputs NODE=... PORT=... JOB_ID=... for us to parse
REMOTE_OUTPUT=$(ssh "${SSH_OPTS[@]}" "${SSH_DEST}" bash -s <<REMOTE_SCRIPT
set -euo pipefail

cd "${REMOTE_DIR}" || { echo "REMOTE_ERROR: Cannot cd to ${REMOTE_DIR}" >&2; exit 1; }

STATUS_FILE="${STATUS_FILE}"

# Check if there's already a running job with our job name
EXISTING_JOB=\$(squeue --me --name="${JOB_NAME}" -h -o "%i %T" 2>/dev/null | head -1)

if [[ -n "\${EXISTING_JOB}" ]]; then
    JOB_ID=\$(echo "\${EXISTING_JOB}" | awk '{print \$1}')
    JOB_STATE=\$(echo "\${EXISTING_JOB}" | awk '{print \$2}')
    echo "FOUND_JOB=\${JOB_ID}" >&2
    echo "JOB_STATE=\${JOB_STATE}" >&2

    if [[ "\${JOB_STATE}" == "RUNNING" && -f "\${STATUS_FILE}" ]]; then
        # Job is running and status file exists — read it
        cat "\${STATUS_FILE}"
        exit 0
    fi

    if [[ "\${JOB_STATE}" == "PENDING" ]]; then
        echo "WAITING: Job \${JOB_ID} is pending..." >&2
    fi
else
    # No existing job — submit one
    echo "NO_EXISTING_JOB: Submitting new server job..." >&2
    JOB_ID=\$(sbatch --parsable hpc_utils/start_server.sh)
    echo "SUBMITTED_JOB=\${JOB_ID}" >&2
fi

# Wait for the job to start and server_info.txt to appear
MAX_WAIT=120
WAITED=0
while [[ \${WAITED} -lt \${MAX_WAIT} ]]; do
    JOB_STATE=\$(squeue -j "\${JOB_ID}" -h -o "%T" 2>/dev/null || echo "UNKNOWN")
    if [[ "\${JOB_STATE}" == "RUNNING" && -f "\${STATUS_FILE}" ]]; then
        # Give the server a moment to write the file
        sleep 2
        cat "\${STATUS_FILE}"
        exit 0
    fi
    if [[ "\${JOB_STATE}" == "UNKNOWN" || "\${JOB_STATE}" == "FAILED" || "\${JOB_STATE}" == "CANCELLED" ]]; then
        echo "REMOTE_ERROR: Job \${JOB_ID} entered state \${JOB_STATE}" >&2
        exit 1
    fi
    echo "WAITING: Job \${JOB_ID} is \${JOB_STATE}... (\${WAITED}s)" >&2
    sleep 5
    WAITED=\$((WAITED + 5))
done

echo "REMOTE_ERROR: Timed out waiting for job \${JOB_ID} to start after \${MAX_WAIT}s" >&2
exit 1
REMOTE_SCRIPT
)

# ---------------------------------------------------------------------------
# Step 2: Parse the server info returned from the remote
# ---------------------------------------------------------------------------
# The remote script outputs the contents of server_info.txt to stdout
# and status/progress messages to stderr (which we see in real-time)
eval "${REMOTE_OUTPUT}"

if [[ -z "${NODE:-}" || -z "${PORT:-}" || -z "${JOB_ID:-}" ]]; then
    echo "ERROR: Failed to get server info from ${SSH_DEST}." >&2
    echo "       Remote output: ${REMOTE_OUTPUT}" >&2
    exit 1
fi

echo ""
echo "Server info:"
echo "  Compute node : ${NODE}"
echo "  Remote port  : ${PORT}"
echo "  Slurm job    : ${JOB_ID}"

# ---------------------------------------------------------------------------
# Step 3: Reclaim local port from stale tunnel or fail if in use by other process
# ---------------------------------------------------------------------------
if is_port_in_use "${LOCAL_PORT}"; then
    echo "  Port ${LOCAL_PORT} is in use. Looking for stale SSH tunnels..."
    # Match our exact tunnel pattern: ssh -N -L PORT:NODE:PORT USER@HOST
    STALE_PIDS=$(pgrep -f "ssh.*-L.*${LOCAL_PORT}.*${SSH_USER}@${LOGIN_NODE}" 2>/dev/null || true)
    if [[ -n "${STALE_PIDS}" ]]; then
        for PID in ${STALE_PIDS}; do
            echo "  Force-killing stale SSH tunnel (PID ${PID})..."
            kill -9 "${PID}" 2>/dev/null || true
        done
        sleep 2
    fi
    # Check again after cleanup — if still busy, try next ports
    if is_port_in_use "${LOCAL_PORT}"; then
        echo "  Port ${LOCAL_PORT} is still in use by another process. Searching for a free port..."
        FOUND_FREE=false
        for OFFSET in $(seq 1 20); do
            CANDIDATE=$((LOCAL_PORT + OFFSET))
            if ! is_port_in_use "${CANDIDATE}"; then
                echo "  Using port ${CANDIDATE} instead."
                LOCAL_PORT="${CANDIDATE}"
                FOUND_FREE=true
                break
            fi
        done
        if [[ "${FOUND_FREE}" != "true" ]]; then
            echo "ERROR: Could not find a free port in range ${LOCAL_PORT}–$((LOCAL_PORT + 20))." >&2
            exit 1
        fi
    else
        echo "  Port ${LOCAL_PORT} reclaimed."
    fi
fi

echo "  Local port   : ${LOCAL_PORT}"

# ---------------------------------------------------------------------------
# Step 4: Graceful cleanup on exit (tunnel + control connection)
# ---------------------------------------------------------------------------
SSH_PID=""
cleanup() {
    if [[ -n "${SSH_PID}" ]]; then
        echo ""
        echo "Closing SSH tunnel (PID ${SSH_PID})..."
        kill "${SSH_PID}" 2>/dev/null || true
        wait "${SSH_PID}" 2>/dev/null || true
    fi
    # Close the ControlMaster connection
    ssh -O exit -o "ControlPath=${SSH_CONTROL_PATH}" "${SSH_DEST}" 2>/dev/null || true
    rm -f "${SSH_CONTROL_PATH}"
    echo "Tunnel closed."
}
trap cleanup EXIT INT TERM

# ---------------------------------------------------------------------------
# Step 5: Create SSH tunnel
# ---------------------------------------------------------------------------
echo ""
echo "Opening SSH tunnel: localhost:${LOCAL_PORT} -> ${NODE}:${PORT} via ${SSH_DEST}..."

# Use the existing ControlMaster for auth (no re-prompt) but keep the tunnel
# alive independently with ServerAliveInterval.
ssh -o "ControlPath=${SSH_CONTROL_PATH}" -o "ControlMaster=no" \
    -o "ServerAliveInterval=60" -o "ExitOnForwardFailure=yes" \
    -N -L "${LOCAL_PORT}:${NODE}:${PORT}" "${SSH_DEST}" &
SSH_PID=$!

# Give it a moment — if the process exits immediately, fall back to keeping
# the script alive as long as the port forwarding is working (the ControlMaster
# may be managing the tunnel even after the slave process exits).
sleep 1
if ! kill -0 "${SSH_PID}" 2>/dev/null; then
    SSH_PID=""
fi

# ---------------------------------------------------------------------------
# Step 6: Verify the tunnel comes up
# ---------------------------------------------------------------------------
echo "Waiting for tunnel to establish..."
TUNNEL_OK=false
for i in $(seq 1 10); do
    sleep 1
    if is_port_in_use "${LOCAL_PORT}"; then
        TUNNEL_OK=true
        break
    fi
done

if [[ "${TUNNEL_OK}" != "true" ]]; then
    echo "ERROR: SSH tunnel did not come up after 10 seconds." >&2
    echo "       Check your SSH config and try manually:" >&2
    echo "         ssh -N -L ${LOCAL_PORT}:${NODE}:${PORT} ${SSH_DEST}" >&2
    exit 1
fi

URL="http://localhost:${LOCAL_PORT}/app"
echo ""
echo "=========================================="
echo "  Tunnel is active!"
echo "  Open: ${URL}"
echo "=========================================="
echo ""
echo "Press Ctrl+C to close the tunnel."

# Open browser
if command -v open &>/dev/null; then
    open "${URL}"
elif command -v xdg-open &>/dev/null; then
    xdg-open "${URL}"
fi

# Keep the script alive until Ctrl+C or the tunnel drops.
# The SSH slave process may exit immediately when multiplexed through the
# ControlMaster, but the port forwarding stays alive through the master.
# Always poll the port so we don't exit prematurely.
while is_port_in_use "${LOCAL_PORT}"; do
    sleep 5
done
echo "Tunnel port ${LOCAL_PORT} is no longer active."
