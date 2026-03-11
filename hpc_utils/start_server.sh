#!/usr/bin/env bash
#SBATCH --job-name=py_accel_viewer
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=16
#SBATCH --mem-per-cpu=1500
#SBATCH --time=36:00:00
#SBATCH --output=hpc_utils/logs/panel-server-%j.log
#SBATCH --error=hpc_utils/logs/panel-server-%j.log
#
# start_server.sh — Launch the Panel annotation app as a shared server via Slurm.
#
# Usage:
#   sbatch hpc_utils/start_server.sh
#
# The script writes connection details (hostname, port, job ID, timestamp) to
# hpc_utils/server_info.txt so that users can find the running instance.
#
# Overridable variables (export before sbatch, or edit defaults below):
#   PORT          — Port the Panel server listens on (default: 7860)
#   CREDENTIALS   — Path to credentials.json (default: credentials.json)
#   APP_PATH      — Path to the Panel app (default: visualize_accelerometry/app.py)
#   STATUS_FILE   — Where to write server info (default: hpc_utils/server_info.txt)

# ---------------------------------------------------------------------------
# Environment setup (must match HPC module/conda configuration)
# ---------------------------------------------------------------------------
export PYTHONUNBUFFERED=true
module load gcc/12.1.0
module load miniconda3/23.1.0
source activate /gpfs/data/nshap-lab/users/mmurugesan/venvs/panel_app

# ---------------------------------------------------------------------------
# Configurable defaults
# ---------------------------------------------------------------------------
PORT="${PORT:-7860}"
CREDENTIALS="${CREDENTIALS:-credentials.json}"
APP_PATH="${APP_PATH:-visualize_accelerometry/app.py}"
STATUS_FILE="${STATUS_FILE:-hpc_utils/server_info.txt}"
SLURM_JOB_ID="${SLURM_JOB_ID:-0}"

# ---------------------------------------------------------------------------
# Write status file so users can discover the server
# ---------------------------------------------------------------------------
NODE="$(hostname -s)"
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
# Start Panel (background, kept alive via sleep.py)
# ---------------------------------------------------------------------------
nohup panel serve "${APP_PATH}" \
    --port="${PORT}" \
    --basic-auth "${CREDENTIALS}" \
    --cookie-secret="$(python -c 'import secrets; print(secrets.token_hex(32))')" \
    --allow-websocket-origin="*" \
    --basic-login-template visualize_accelerometry/templates/login.html \
    --unused-session-lifetime 10370000000 \
    --num-procs 8 \
    > hpc_utils/logs/panel-serve.log 2>&1 &

python hpc_utils/sleep.py
