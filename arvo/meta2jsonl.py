"""usage:
  python3 meta2jsonl.py <meta_dir> [-o <out>] [-n <limit>] [-m <mask>] [-p <project>] [-d <db>]

  reads ARVO-Meta JSON files and optionally arvo.db, outputs JSONL.
  -p filter by project name
  -m filter to only entries in mask_map.json (covers both arvo:* and oss-fuzz:* keys)
  -d arvo.db path for oss-fuzz:* entries (default: ../arvo/arvo.db relative to meta_dir)

examples:
  python3 meta2jsonl.py ARVO-Meta/archive_data/meta -p ffmpeg -m mask_map.json
  python3 meta2jsonl.py ARVO-Meta/archive_data/meta -p binutils-gdb -m mask_map.json -o projects/binutils/cybergym_binutils.jsonl
"""

import json
import sys
import os
import sqlite3

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB = os.path.join(REPO_ROOT, 'arvo', 'arvo.db')


def resolve_path(path):
    if not os.path.isabs(path) and not os.path.exists(path):
        return os.path.join(REPO_ROOT, path)
    return path


def load_mask_sets(mask_path):
    """return (arvo_ids, oss_ids) from mask_map.json"""
    with open(resolve_path(mask_path)) as f:
        mask = json.load(f)
    arvo_ids = set()
    oss_ids = set()
    for k in mask:
        num = k.split(':', 1)[1]
        if not num.isdigit():
            continue
        if k.startswith('arvo:'):
            arvo_ids.add(int(num))
        elif k.startswith('oss-fuzz:'):
            oss_ids.add(int(num))
    return arvo_ids, oss_ids


def read_meta(meta_dir, arvo_ids, project, limit, out_f, fc_map=None):
    """yield rows from ARVO-Meta files filtered by arvo_ids + project.
    if fc_map is provided, add modern_localId via fix_commit lookup."""
    count = 0
    remaining = limit
    for fname in sorted(os.listdir(meta_dir)):
        if not fname.endswith('.json'):
            continue
        try:
            local_id = int(fname.replace('.json', ''))
        except ValueError:
            continue
        if arvo_ids is not None and local_id not in arvo_ids:
            continue
        with open(os.path.join(meta_dir, fname)) as mf:
            row = json.load(mf)
        if project is not None and row.get('project') != project:
            continue
        report = row.pop('report', None)
        row['report_comments'] = len(report['comments']) if report and 'comments' in report else 0
        if fc_map:
            fc = row.get('fix_commit', '')
            if fc and fc in fc_map:
                row['modern_localId'] = fc_map[fc]
        out_f.write(json.dumps(row) + '\n')
        count += 1
        if limit:
            remaining -= 1
            if remaining <= 0:
                break
    return count


def build_fc_map(db_path):
    """return {fix_commit: modern_localId} from arvo.db"""
    if not db_path or not os.path.exists(db_path):
        return {}
    db = sqlite3.connect(db_path)
    cur = db.cursor()
    fc_map = {}
    for row in cur.execute('SELECT localId, fix_commit FROM arvo WHERE fix_commit IS NOT NULL AND fix_commit != ""'):
        fc_map[row[1]] = row[0]
    db.close()
    return fc_map


def read_db(db_path, oss_ids, project, limit, out_f):
    """yield rows from arvo.db filtered by oss_ids + project"""
    if oss_ids is None or not oss_ids:
        return 0
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    cur = db.cursor()
    count = 0
    remaining = limit
    for lid in sorted(oss_ids):
        cur.execute('SELECT * FROM arvo WHERE localId=?', [lid])
        row = cur.fetchone()
        if row is None:
            continue
        row = dict(row)
        if project is not None and row.get('project') != project:
            continue
        out_f.write(json.dumps(row) + '\n')
        count += 1
        if limit:
            remaining -= 1
            if remaining <= 0:
                break
    db.close()
    return count


def main():
    args = sys.argv[1:]
    if not args or args[0] in ('-h', '--help'):
        print(__doc__)
        sys.exit(1)

    meta_dir = args[0]
    out_path = None
    limit = None
    mask_path = None
    project = None
    db_path = None

    i = 1
    while i < len(args):
        if args[i] == '-o' and i + 1 < len(args):
            out_path = args[i + 1]
            i += 2
        elif args[i] == '-n' and i + 1 < len(args):
            limit = int(args[i + 1])
            i += 2
        elif args[i] == '-m' and i + 1 < len(args):
            mask_path = args[i + 1]
            i += 2
        elif args[i] == '-p' and i + 1 < len(args):
            project = args[i + 1]
            i += 2
        elif args[i] == '-d' and i + 1 < len(args):
            db_path = args[i + 1]
            i += 2
        else:
            print(f"unknown flag: {args[i]}")
            sys.exit(1)

    arvo_ids = None
    oss_ids = None
    if mask_path:
        arvo_ids, oss_ids = load_mask_sets(mask_path)

    if db_path is None and mask_path:
        db_path = DEFAULT_DB
    if db_path:
        db_path = resolve_path(db_path)

    fc_map = build_fc_map(db_path) if mask_path else None

    if out_path:
        out_dir = os.path.dirname(out_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        f = open(out_path, 'w')
    else:
        f = sys.stdout

    count_meta = read_meta(meta_dir, arvo_ids, project, limit, f, fc_map)
    limit_remaining = limit - count_meta if limit else None
    count_db = read_db(db_path, oss_ids, project, limit_remaining, f)
    total = count_meta + count_db

    if out_path:
        f.close()
        src = []
        if count_meta: src.append(f'meta={count_meta}')
        if count_db: src.append(f'db={count_db}')
        print(f"wrote {total} rows ({', '.join(src)}) → {out_path}", file=sys.stderr)
    else:
        print(f"\n-- {total} rows (meta={count_meta}, db={count_db})", file=sys.stderr)


if __name__ == '__main__':
    main()
