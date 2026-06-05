#!/usr/bin/env bash
# usage: ./pull_from_local_registry.sh -r <registry_ip:port>
# Pull cybergym images from a local registry onto the server.
#   -r ADDR  registry address, e.g. "192.168.1.5:5000"
set -euo pipefail

REGISTRY=""
while getopts "r:" opt; do
    case $opt in r) REGISTRY=$OPTARG ;; esac
done
[ -n "$REGISTRY" ] || { echo "usage: $0 -r <registry_ip:port>"; exit 1; }

# List all cybergym repos hosted at the registry
echo "=== Listing images from $REGISTRY ==="
CATALOG=$(curl -s "http://${REGISTRY}/v2/_catalog" | python3 -c "
import json,sys
data = json.load(sys.stdin)
for r in data.get('repositories', []):
    if 'cybergym' in r:
        print(r)
")

for repo in $CATALOG; do
    TAGS=$(curl -s "http://${REGISTRY}/v2/${repo}/tags/list" | python3 -c "
import json,sys
data = json.load(sys.stdin)
print('\n'.join(data.get('tags', [])))")

    for tag in $TAGS; do
        img="${REGISTRY}/${repo}:${tag}"
        echo "PULL: $img"
        docker pull "$img" || echo "FAIL: $img"
    done
done

echo "=== Done ==="
echo "To use these images under their original names, re-tag them:"
echo "  docker tag ${REGISTRY}/cybergym/cybergym_oss-fuzz_42535201_vul cybergym/oss-fuzz:42535201-vul"
