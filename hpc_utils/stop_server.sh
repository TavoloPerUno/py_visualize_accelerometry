#!/usr/bin/env bash
#
# stop_server.sh — Cancel the shared Panel server Slurm job and clean up.
#
# Usage:
#   bash hpc_utils/stop_server.sh
#
# Overridable variables:
#   STATUS_FILE   — Path to server info file (default: hpc_utils/server_info.txt)

set -euo pipefail

STATUS_FILE="${STATUS_FILE:-hpc_utils/server_info.txt}"

if [[ ! -f "${STATUS_FILE}" ]]; then
    echo "ERROR: ${STATUS_FILE} not found. Nothing to stop." >&2
    exit 1
fi

# shellcheck disable=SC1090
source "${STATUS_FILE}"

if [[ -z "${JOB_ID:-}" ]]; then
    echo "ERROR: ${STATUS_FILE} does not contain a JOB_ID." >&2
    exit 1
fi

echo "Cancelling Slurm job ${JOB_ID}..."
scancel "${JOB_ID}"

rm -f "${STATUS_FILE}"
echo "Job cancelled and ${STATUS_FILE} removed."
