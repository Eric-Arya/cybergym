"""usage:
  python3 docker_sizes.py [-p <project>] [-n <limit>]

  queries Docker Hub API for n132/arvo tag sizes,
  maps IDs to projects via mask_map + arvo.db + ARVO-Meta,
  outputs per-project total compressed size.

examples:
  python3 docker_sizes.py                    # all projects
  python3 docker_sizes.py -p binutils-gdb    # one project
  python3 docker_sizes.py -n 10              # top 10
"""

import json
import sys
import os
import sqlite3
import urllib.request
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
META_DIR = os.path.join(SCRIPT_DIR, 'ARVO-Meta', 'archive_data', 'meta')
DB_PATH = os.path.join(SCRIPT_DIR, 'arvo.db')
MASK_PATH = os.path.join(os.path.dirname(SCRIPT_DIR), 'mask_map.json')
CACHE_PATH = os.path.join(SCRIPT_DIR, '.docker_tag_cache.json')


def fetch_all_tags():
    """fetch all n132/arvo tags from Docker Hub, cache to disk"""
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH) as f:
            cache = json.load(f)
        age = time.time() - os.path.getmtime(CACHE_PATH)
        if age < 86400:  # 24h cache
            print(f"Using cached tag data ({len(cache)} tags, {age/3600:.1f}h old)", file=sys.stderr)
            return cache

    print("Fetching tags from Docker Hub...", file=sys.stderr)
    tags = {}
    url = "https://hub.docker.com/v2/repositories/n132/arvo/tags/?page_size=100"
    page = 0
    while url:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'curl/7.0')
        try:
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.loads(resp.read())
        except Exception as e:
            print(f"  error at {url}: {e}", file=sys.stderr)
            break
        for t in data.get('results', []):
            tags[t['name']] = t.get('full_size', 0) or 0
        url = data.get('next')
        page += 1
        if page % 20 == 0:
            print(f"  page {page}, {len(tags)} tags so far...", file=sys.stderr)

    with open(CACHE_PATH, 'w') as f:
        json.dump(tags, f)
    print(f"Fetched {len(tags)} tags", file=sys.stderr)
    return tags


def build_id_to_project():
    """map numeric ID -> project from all sources"""
    id2proj = {}

    # from mask_map arvo:* -> ARVO-Meta
    with open(MASK_PATH) as f:
        mask = json.load(f)
    for k in mask:
        if k.startswith('arvo:'):
            num = k.split(':')[1]
            meta_path = os.path.join(META_DIR, f'{num}.json')
            if os.path.exists(meta_path):
                proj = json.load(open(meta_path)).get('project', 'unknown')
                id2proj[num] = proj

    # from mask_map oss-fuzz:* -> arvo.db
    db = sqlite3.connect(DB_PATH)
    for k in mask:
        if k.startswith('oss-fuzz:'):
            num = k.split(':')[1]
            row = db.execute('SELECT project FROM arvo WHERE localId=?', [int(num)]).fetchone()
            if row:
                id2proj[num] = row[0]

    # also add all arvo.db entries (for non-mask entries)
    for row in db.execute('SELECT localId, project FROM arvo'):
        id2proj[str(row[0])] = row[1]

    db.close()
    return id2proj


def main():
    args = sys.argv[1:]
    if not args or args[0] in ('-h', '--help'):
        print(__doc__)
        sys.exit(1)

    project_filter = None
    top_n = None
    i = 0
    while i < len(args):
        if args[i] == '-p' and i + 1 < len(args):
            project_filter = args[i + 1]
            i += 2
        elif args[i] == '-n' and i + 1 < len(args):
            top_n = int(args[i + 1])
            i += 2
        else:
            print(f"unknown: {args[i]}")
            sys.exit(1)

    tags = fetch_all_tags()
    id2proj = build_id_to_project()

    # Aggregate: per project, sum max(vul_size, fix_size) per instance
    # Group by numeric ID
    from collections import defaultdict
    inst_sizes = defaultdict(lambda: {'vul': 0, 'fix': 0})
    for tag_name, size in tags.items():
        # extract numeric ID and suffix
        if tag_name.endswith('-vul'):
            iid = tag_name[:-4]
            inst_sizes[iid]['vul'] = max(inst_sizes[iid]['vul'], size)
        elif tag_name.endswith('-fix'):
            iid = tag_name[:-4]
            inst_sizes[iid]['fix'] = max(inst_sizes[iid]['fix'], size)

    # Sum per project
    proj_size = defaultdict(int)
    proj_count = defaultdict(int)
    for iid, sz in inst_sizes.items():
        proj = id2proj.get(iid, '_unmapped')
        # per-instance size = max of vul/fix (they're nearly identical)
        inst_gb = max(sz['vul'], sz['fix']) / 1e9
        proj_size[proj] += inst_gb
        proj_count[proj] += 1

    # Output
    if project_filter:
        print(f"{project_filter}: {proj_size.get(project_filter, 0):.1f} GB ({proj_count.get(project_filter, 0)} instances)")
    else:
        sorted_proj = sorted(proj_size.items(), key=lambda x: -x[1])
        limit = top_n or len(sorted_proj)
        print(f"{'project':<25s} {'instances':>10s} {'size (GB)':>12s}")
        print("-" * 49)
        for proj, gb in sorted_proj[:limit]:
            print(f"{proj:<25s} {proj_count[proj]:>10d} {gb:>12.1f}")


if __name__ == '__main__':
    main()
