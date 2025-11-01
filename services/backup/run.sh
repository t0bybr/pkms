#!/bin/bash
set -euo pipefail
mkdir -p "$RESTIC_REPO"
export RESTIC_PASSWORD
if ! restic -r "$RESTIC_REPO" snapshots >/dev/null 2>&1; then
  echo "Initializing restic repo at $RESTIC_REPO"
  restic -r "$RESTIC_REPO" init
fi

backup_once(){
  echo "[backup] $(date) starting" >&2
  restic -r "$RESTIC_REPO" backup "$RESTIC_INCLUDE_DATA" "$RESTIC_INCLUDE_INDEX" --tag pkms
  restic -r "$RESTIC_REPO" forget --keep-daily 7 --keep-weekly 5 --keep-monthly 12 --prune
  echo "[backup] $(date) done" >&2
}

backup_once || true
while true; do
  sleep 86400
  backup_once || true
done
