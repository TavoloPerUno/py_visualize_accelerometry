#!/usr/bin/env bash
#
# start_server.sh — Launch the Panel annotation app as a shared server via Slurm.
#
# Usage:
#   sbatch slurm/start_server.sh
#
# The script writes connection details (hostname, port, job ID, timestamp) to
# slurm/server_info.txt so that users can find the running instance.
#
# Overridable variables (export before sbatch, or edit defaults below):
#   PORT          — Port the Panel server listens on (default: 7860)
#   CREDENTIALS   — Path to credentials.json (default: credentials.json)
#   APP_PATH      — Path to the Panel app (default: visualize_accelerometry/app.py)
#   STATUS_FILE   — Where to write server info (default: slurm/server_info.txt)

set -euo pipefail

#SBATCH --job-name=panel-server
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=7-00:00:00
#SBATCH --output=slurm/panel-server-%j.log
#SBATCH --error=slurm/panel-server-%j.log

# ---------------------------------------------------------------------------
# Configurable defaults
# ---------------------------------------------------------------------------
PORT="${PORT:-7860}"
CREDENTIALS="${CREDENTIALS:-credentials.json}"
APP_PATH="${APP_PATH:-visualize_accelerometry/app.py}"
STATUS_FILE="${STATUS_FILE:-slurm/server_info.txt}"

# ---------------------------------------------------------------------------
# Write status file so users can discover the server
# ---------------------------------------------------------------------------
NODE="$(hostname)"
cat > "${STATUS_FILE}" <<EOF
NODE=${NODE}
PORT=${PORT}
JOB_ID=${SLURM_JOB_ID}
STARTED=$(date --iso-8601=seconds 2>/dev/null || date +%Y-%m-%dT%H:%M:%S%z)
EOF

echo "Server info written to ${STATUS_FILE}"
echo "  Node : ${NODE}"
echo "  Port : ${PORT}"
echo "  Job  : ${SLURM_JOB_ID}"

# ---------------------------------------------------------------------------
# Start Panel
# ---------------------------------------------------------------------------
exec panel serve "${APP_PATH}" \
    --port "${PORT}" \
    --basic-auth "${CREDENTIALS}" \
    --cookie-secret "$(python -c 'import secrets; print(secrets.token_hex(32))')" \
    --allow-websocket-origin "*" \
    --num-procs 1
