#!/usr/bin/env bash
"""
usage: ./download_subset.sh [-w N]

  -w N   max concurrent pulls (default: 1)

examples:
  ./download_subset.sh         # one at a time
  ./download_subset.sh -w 4    # 4 concurrent pulls
"""
set -euo pipefail

MAX_WORKERS=1
while getopts "w:" opt; do
    case $opt in
        w) MAX_WORKERS=$OPTARG ;;
        *) echo "usage: $0 [-w N]"; exit 1 ;;
    esac
done

TASK_IDS=(
    "arvo:47101"
    "arvo:3938"
    "arvo:24993"
    "arvo:1065"
    "arvo:10400"
    "arvo:368"
    "oss-fuzz:42535201"
    "oss-fuzz:42535468"
    "oss-fuzz:370689421"
    "oss-fuzz:385167047"
)

pull_one() {
    local repo="$1" tag="$2"
    echo "Pulling $repo:$tag ..."
    if docker pull "$repo:$tag"; then
        echo "OK: $repo:$tag"
    else
        echo "FAIL: $repo:$tag" >&2
    fi
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
