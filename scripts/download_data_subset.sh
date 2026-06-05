#!/usr/bin/env bash
# usage: ./download_data_subset.sh -o <out_dir> [-d level1] [-w N]
#   -o DIR        output directory (required)
#   -d DIFFICULTY  difficulty level: level0|level1|level2|level3 (default: level1)
#   -w N          concurrent workers (default: 4)
#
# Downloads files matching the difficulty level for the 10-task subset.
#   level0: repo-vul.tar.gz
#   level1: + description.txt
#   level2: + error.txt
#   level3: + repo-fix.tar.gz, patch.diff
set -euo pipefail

OUT_DIR=""
MAX_WORKERS=4
DIFFICULTY="level1"

while getopts "o:w:d:" opt; do
    case $opt in
        o) OUT_DIR=$OPTARG ;;
        w) MAX_WORKERS=$OPTARG ;;
        d) DIFFICULTY=$OPTARG ;;
        *) echo "usage: $0 -o <out_dir> [-d level1] [-w N]"; exit 1 ;;
    esac
done

[ -n "$OUT_DIR" ] || { echo "error: -o is required"; exit 1; }

case "$DIFFICULTY" in
    level0) FILES=("repo-vul.tar.gz") ;;
    level1) FILES=("repo-vul.tar.gz" "description.txt") ;;
    level2) FILES=("repo-vul.tar.gz" "description.txt" "error.txt") ;;
    level3) FILES=("repo-vul.tar.gz" "description.txt" "error.txt" "repo-fix.tar.gz" "patch.diff") ;;
    *) echo "error: invalid difficulty '$DIFFICULTY' (use level0-3)"; exit 1 ;;
esac

BASE="https://huggingface.co/datasets/sunblaze-ucb/cybergym/resolve/main"

TASK_IDS=(
    "oss-fuzz:42535468" "arvo:20200" "arvo:23433"

)

URL_FILE=$(mktemp)
for tid in "${TASK_IDS[@]}"; do
    IFS=':' read -r type iid <<<"$tid"
    for f in "${FILES[@]}"; do
        echo "$BASE/data/$type/$iid/$f" >> "$URL_FILE"
    done
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
