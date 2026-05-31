#!/usr/bin/env bash
# usage: ./download_data_subset.sh -o <out_dir> [-w N]
#   -o DIR  output directory (required)
#   -w N    concurrent workers (default: 4)
#
# Downloads level1 data (repo-vul.tar.gz + description.txt) for the 10-task subset.
set -euo pipefail

OUT_DIR=""
MAX_WORKERS=4

while getopts "o:w:" opt; do
    case $opt in
        o) OUT_DIR=$OPTARG ;;
        w) MAX_WORKERS=$OPTARG ;;
        *) echo "usage: $0 -o <out_dir> [-w N]"; exit 1 ;;
    esac
done

[ -n "$OUT_DIR" ] || { echo "error: -o is required"; exit 1; }

BASE="https://huggingface.co/datasets/sunblaze-ucb/cybergym/resolve/main"

TASK_IDS=(
    "arvo:47101"       "arvo:3938"        "arvo:24993"
    "arvo:1065"        "arvo:10400"       "arvo:368"
    "oss-fuzz:42535201"   "oss-fuzz:42535468"
    "oss-fuzz:370689421"  "oss-fuzz:385167047"
)

URL_FILE=$(mktemp)
for tid in "${TASK_IDS[@]}"; do
    IFS=':' read -r type iid <<<"$tid"
    echo "$BASE/data/$type/$iid/repo-vul.tar.gz" >> "$URL_FILE"
    echo "$BASE/data/$type/$iid/description.txt" >> "$URL_FILE"
done

echo "Downloading $(wc -l < "$URL_FILE") files ($MAX_WORKERS workers)..."

download_one() {
    local url="$1" out="$2"
    local rel="${url#$BASE/}"
    rel="${rel#data/}"  # strip leading data/ so files go to out_dir/arvo/... not out_dir/data/arvo/...
    local dest="$out/$rel"
    mkdir -p "$(dirname "$dest")"
    [ -f "$dest" ] && { echo "SKIP: $rel"; return; }
    echo "GET: $rel"
    wget -q --show-progress -O "$dest" "$url" || { echo "FAIL: $rel" >&2; rm -f "$dest"; }
}

export -f download_one
export BASE OUT_DIR

xargs -P "$MAX_WORKERS" -I {} bash -c 'download_one "$@"' _ {} "$OUT_DIR" < "$URL_FILE"
rm -f "$URL_FILE"
echo "Done: $OUT_DIR"
