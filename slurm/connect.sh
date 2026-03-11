#!/usr/bin/env bash
#
# connect.sh — Open an SSH tunnel to the shared Panel server running on a
#               Slurm compute node.
#
# Usage:
#   bash slurm/connect.sh
#
# The script reads slurm/server_info.txt (written by start_server.sh),
# validates that the Slurm job is still running, picks an available local
# port, creates an SSH tunnel, and opens the browser.
#
# Overridable variables (export before running, or edit defaults below):
#   LOGIN_NODE    — SSH gateway / login node (default: login.example.com)
#   STATUS_FILE   — Path to server info file (default: slurm/server_info.txt)
#   LOCAL_PORT    — Preferred local port; auto-increments if busy (default: same as remote)

set -euo pipefail

# ---------------------------------------------------------------------------
# Configurable defaults
# ---------------------------------------------------------------------------
LOGIN_NODE="${LOGIN_NODE:-login.example.com}"
STATUS_FILE="${STATUS_FILE:-slurm/server_info.txt}"

# ---------------------------------------------------------------------------
# Read server info
# ---------------------------------------------------------------------------
if [[ ! -f "${STATUS_FILE}" ]]; then
    echo "ERROR: ${STATUS_FILE} not found. Is the server running?" >&2
    echo "       Start it first:  sbatch slurm/start_server.sh" >&2
    exit 1
fi

# shellcheck disable=SC1090
source "${STATUS_FILE}"

if [[ -z "${NODE:-}" || -z "${PORT:-}" || -z "${JOB_ID:-}" ]]; then
    echo "ERROR: ${STATUS_FILE} is missing required fields (NODE, PORT, JOB_ID)." >&2
    exit 1
fi

echo "Server info:"
echo "  Compute node : ${NODE}"
echo "  Remote port  : ${PORT}"
echo "  Slurm job    : ${JOB_ID}"

# ---------------------------------------------------------------------------
# Validate the Slurm job is still running
# ---------------------------------------------------------------------------
if ! squeue -j "${JOB_ID}" -h -o "%T" 2>/dev/null | grep -qiE "running|pending"; then
    echo "ERROR: Slurm job ${JOB_ID} is no longer active." >&2
    echo "       The server may have stopped. Check logs or restart with:" >&2
    echo "         sbatch slurm/start_server.sh" >&2
    exit 1
fi

echo "  Job status   : running"

# ---------------------------------------------------------------------------
# Pick an available local port
# ---------------------------------------------------------------------------
LOCAL_PORT="${LOCAL_PORT:-${PORT}}"

is_port_in_use() {
    if command -v lsof &>/dev/null; then
        lsof -i ":$1" &>/dev/null
    elif command -v ss &>/dev/null; then
        ss -tlnp "sport = :$1" 2>/dev/null | grep -q "$1"
    else
        # Fallback: try to bind with Python
        python -c "
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

MAX_ATTEMPTS=100
ATTEMPT=0
while is_port_in_use "${LOCAL_PORT}"; do
    ATTEMPT=$((ATTEMPT + 1))
    if [[ "${ATTEMPT}" -ge "${MAX_ATTEMPTS}" ]]; then
        echo "ERROR: Could not find a free local port after ${MAX_ATTEMPTS} attempts." >&2
        exit 1
    fi
    LOCAL_PORT=$((LOCAL_PORT + 1))
done

echo "  Local port   : ${LOCAL_PORT}"

# ---------------------------------------------------------------------------
# Graceful cleanup on exit
# ---------------------------------------------------------------------------
SSH_PID=""
cleanup() {
    if [[ -n "${SSH_PID}" ]]; then
        echo ""
        echo "Closing SSH tunnel (PID ${SSH_PID})..."
        kill "${SSH_PID}" 2>/dev/null || true
        wait "${SSH_PID}" 2>/dev/null || true
    fi
    echo "Tunnel closed."
}
trap cleanup EXIT INT TERM

# ---------------------------------------------------------------------------
# Create SSH tunnel
# ---------------------------------------------------------------------------
echo ""
echo "Opening SSH tunnel: localhost:${LOCAL_PORT} -> ${NODE}:${PORT} via ${LOGIN_NODE}..."

ssh -N -L "${LOCAL_PORT}:${NODE}:${PORT}" "${LOGIN_NODE}" &
SSH_PID=$!

# ---------------------------------------------------------------------------
# Verify the tunnel comes up
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
    echo "         ssh -N -L ${LOCAL_PORT}:${NODE}:${PORT} ${LOGIN_NODE}" >&2
    exit 1
fi

URL="http://localhost:${LOCAL_PORT}/visualize_accelerometry/app"
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

# Keep the script alive until the user kills it
wait "${SSH_PID}"
