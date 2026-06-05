#!/usr/bin/env bash
# usage: ./rename_registry_tags.sh
# Rename old-format registry tags (localhost:5000/cybergym/...)
# back to original image names, then delete the registry tags.
# Layers are shared, so no extra disk space.
set -euo pipefail

for img in $(docker images --format '{{.Repository}}:{{.Tag}}' | grep '/cybergym/'); do
    flat_name=$(echo "$img" | sed 's|.*/cybergym/||; s|:.*||')   # e.g. n132_arvo_10400-vul
    case "$flat_name" in
        n132_arvo_*)
            dst="n132/arvo:${flat_name#n132_arvo_}" ;;
        cybergym_oss-fuzz-base-runner_*)
            dst="cybergym/oss-fuzz-base-runner:${flat_name#cybergym_oss-fuzz-base-runner_}" ;;
        cybergym_oss-fuzz_*)
            dst="cybergym/oss-fuzz:${flat_name#cybergym_oss-fuzz_}" ;;
        *) echo "SKIP: $img"; continue ;;
    esac
    echo "$img -> $dst"
    docker tag "$img" "$dst"
    docker rmi "$img"
done

echo "Done"
