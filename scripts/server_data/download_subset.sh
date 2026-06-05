#!/usr/bin/env bash
"""
usage: ./download_subset.sh [-w N] [-f <list_file> ...]

  -w N     max concurrent pulls (default: 1)
  -f FILE  read task IDs from file(s) (one per line, "arvo:ID" or just "ID")
           can be used multiple times to combine lists
           if not provided, uses built-in default list

examples:
  ./download_subset.sh -w 4 -f project_lists/binutils.txt
  ./download_subset.sh -f project_lists/mruby.txt -f project_lists/ffmpeg.txt
  ./download_subset.sh                                    # default list
"""
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

MAX_WORKERS=1
LIST_FILES=()
while getopts "w:f:h" opt; do
    case $opt in
        w) MAX_WORKERS=$OPTARG ;;
        f) LIST_FILES+=("$OPTARG") ;;
        h) echo "usage: $0 [-w N] [-f list_file ...]"; exit 0 ;;
        *) echo "usage: $0 [-w N] [-f list_file ...]"; exit 1 ;;
    esac
done

# Default task list (small subset for quick testing)
DEFAULT_TASK_IDS=(
    "arvo:6975"        "arvo:21000"       "arvo:12420"
    "arvo:35293"       "arvo:32275"       "arvo:30217"
    "arvo:23433"       "arvo:20200"       "oss-fuzz:383170476"
    "arvo:60557"       "arvo:19222"       "arvo:63831"
    "arvo:50893"       "arvo:1337"        "arvo:13115"
    "arvo:19573"       "arvo:29827"       "arvo:31065"
    "arvo:57527"       "arvo:64945"       "arvo:12662"
)

if [ ${#LIST_FILES[@]} -gt 0 ]; then
    TASK_IDS=()
    for f in "${LIST_FILES[@]}"; do
        # Resolve relative paths from script dir
        if [[ ! "$f" = /* ]]; then
            f="$SCRIPT_DIR/$f"
        fi
        if [ ! -f "$f" ]; then
            echo "ERROR: list file not found: $f" >&2
            exit 1
        fi
        while IFS= read -r line; do
            [[ -z "$line" || "$line" =~ ^# ]] && continue
            if [[ "$line" =~ ^arvo: ]]; then
                TASK_IDS+=("$line")
            elif [[ "$line" =~ ^[0-9]+$ ]]; then
                TASK_IDS+=("arvo:$line")
            else
                TASK_IDS+=("$line")
            fi
        done < "$f"
        echo "  + $(wc -l < "$f") IDs from $f"
    done
    echo "Loaded ${#TASK_IDS[@]} total task IDs from ${#LIST_FILES[@]} list(s)"
else
    TASK_IDS=("${DEFAULT_TASK_IDS[@]}")
    echo "Using built-in default list (${#TASK_IDS[@]} tasks)"
fi

MAX_RETRIES=3
RETRY_DELAY=5

pull_one() {
    local repo="$1" tag="$2"
    echo "Pulling $repo:$tag ..."
    for ((i=1; i<=MAX_RETRIES; i++)); do
        if docker pull "$repo:$tag"; then
            echo "OK: $repo:$tag"
            return 0
        fi
        if [ "$i" -lt "$MAX_RETRIES" ]; then
            echo "RETRY $i/$MAX_RETRIES: $repo:$tag (wait ${RETRY_DELAY}s)" >&2
            sleep "$RETRY_DELAY"
        fi
    done
    echo "FAIL: $repo:$tag (after $MAX_RETRIES attempts)" >&2
}

export -f pull_one

# Build the image list
IMAGES=()
for tid in "${TASK_IDS[@]}"; do
    IFS=':' read -r src iid <<<"$tid"
    if [ "$src" = "arvo" ]; then
        IMAGES+=("n132/arvo:${iid}-vul")
        # IMAGES+=("n132/arvo:${iid}-fix")
    elif [ "$src" = "oss-fuzz" ]; then
        IMAGES+=("cybergym/oss-fuzz:${iid}-vul")
        # IMAGES+=("cybergym/oss-fuzz:${iid}-fix")
    fi
done

# Pull base image first (sequential, always 1 worker)
echo "=== Pulling base image ==="
docker pull "cybergym/oss-fuzz-base-runner:latest"

# Pull subset images (parallel via xargs)
echo "=== Pulling subset images ($MAX_WORKERS workers) ==="
printf '%s\n' "${IMAGES[@]}" | while IFS= read -r image; do
    repo="${image%:*}"
    tag="${image##*:}"
    echo "$repo $tag"
done | xargs -P "$MAX_WORKERS" -n 2 bash -c 'pull_one "$@"' _
