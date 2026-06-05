#!/bin/bash
"""
usage: ./remove_patch_images.sh [-f]

Remove all docker images with repository matching hwiwonlee/secb.eval* and tag=patch.

Options:
  -f    Force removal (docker rmi -f)
  -h    Show this help
"""
set -euo pipefail

FORCE=""
while getopts "fh" opt; do
    case "$opt" in
        f) FORCE="-f" ;;
        h) head -10 "$0"; exit 0 ;;
        *) head -10 "$0"; exit 1 ;;
    esac
done

IMAGES=$(docker images --format "{{.Repository}}:{{.Tag}}" | grep "^hwiwonlee/secb.eval" | grep ":patch$" || true)

if [ -z "$IMAGES" ]; then
    echo "No matching images found."
    exit 0
fi

COUNT=$(echo "$IMAGES" | wc -l)
echo "Found $COUNT images to remove:"
echo "$IMAGES" | head -20
[ "$COUNT" -gt 20 ] && echo "... and $((COUNT - 20)) more"
echo
echo "Removing..."

echo "$IMAGES" | xargs docker rmi $FORCE

echo "Done. Removed $COUNT images."
