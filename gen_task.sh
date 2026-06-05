#!/bin/bash
# usage: gen_task.sh <task_id> [task_id ...] <difficulty>
#        gen_task.sh tasks.txt [difficulty]
#
# Single:  gen_task.sh arvo:10400 level1
# Batch:   gen_task.sh arvo:10400 arvo:1065 level1
# From file: gen_task.sh runs/lists/list1.txt level1
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

    # Copy files missing from gen_task output
    if [[ "$DIFFICULTY" == level2 || "$DIFFICULTY" == level3 ]]; then
        type_prefix="${task_id%%:*}"
        raw_id="${task_id##*:}"
        data_task_dir="${DATA_DIR}/${type_prefix}/${raw_id}"
        extra_files=(error.txt)
        [[ "$DIFFICULTY" == level3 ]] && extra_files+=(repo-fix.tar.gz)
        for fname in "${extra_files[@]}"; do
            src="${data_task_dir}/${fname}"
            if [[ -f "$src" && ! -f "${out_dir}/${fname}" ]]; then
                cp "$src" "${out_dir}/${fname}"
            fi
        done
    fi
done
