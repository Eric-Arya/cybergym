#!/bin/bash
# usage: gen_task.sh <task_id> [task_id ...] <difficulty>
#        gen_task.sh tasks.txt [difficulty]
#
# Single:  gen_task.sh arvo:10400 level1
# Batch:   gen_task.sh arvo:10400 arvo:1065 level1
# From file: gen_task.sh tasks.txt level1
set -euo pipefail

SERVER="${SERVER:-http://localhost:8666}"
DATA_DIR="${CYBERGYM_DATA_DIR:-./cybergym_data}"
OUT_BASE="${OUT_BASE:-./cybergym_tmp}"
MASK_MAP="${MASK_MAP:-mask_map.json}"
DIFFICULTY="level1"

tasks=()
for arg in "$@"; do
    case "$arg" in
        level*) DIFFICULTY="$arg" ;;
        *)      tasks+=("$arg") ;;
    esac
done

# If single arg is a file, read tasks from it
if [[ ${#tasks[@]} -eq 1 && -f "${tasks[0]}" ]]; then
    mapfile -t tasks < "${tasks[0]}"
fi

for task_id in "${tasks[@]}"; do
    task_id="${task_id%%#*}"
    [[ -z "$task_id" ]] && continue
    out_dir="${OUT_BASE}/${task_id//:/-}-${DIFFICULTY}"
    echo "=== $task_id -> $out_dir ==="
    python3 -m cybergym.task.gen_task \
        --task-id "$task_id" \
        --out-dir "$out_dir" \
        --data-dir "$DATA_DIR" \
        --server "$SERVER" \
        --difficulty "$DIFFICULTY" \
        --mask-map "$MASK_MAP"
done
