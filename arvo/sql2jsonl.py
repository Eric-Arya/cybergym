"""usage:
  python3 sql2jsonl.py <db_path> <query> [-o <out>] [-n <limit>] [-s <col>] [-d] [-m <mask>]

examples:
  python3 sql2jsonl.py arvo/arvo.db "SELECT * FROM arvo" -n 5
  python3 sql2jsonl.py arvo/arvo.db "SELECT * FROM arvo WHERE project='skia'" -o /tmp/skia.jsonl
  python3 sql2jsonl.py arvo/arvo.db "SELECT * FROM arvo" -s crash_type
  python3 sql2jsonl.py arvo/arvo.db "SELECT * FROM arvo" -s crash_type -d
  python3 sql2jsonl.py arvo/arvo.db "SELECT * FROM arvo" -m mask_map.json
"""

import sqlite3
import json
import sys
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def main():
    args = sys.argv[1:]
    if not args or '-h' in args or '--help' in args:
        print(__doc__)
        sys.exit(1)

    db_path = args[0]
    query = args[1]
    out = None
    limit = None
    sort = None
    desc = False
    mask_ids = None

    i = 2
    while i < len(args):
        if args[i] == '-o' and i + 1 < len(args):
            out = args[i + 1]
            i += 2
        elif args[i] == '-n' and i + 1 < len(args):
            limit = int(args[i + 1])
            i += 2
        elif args[i] == '-s' and i + 1 < len(args):
            sort = args[i + 1]
            i += 2
        elif args[i] == '-d':
            desc = True
            i += 1
        elif args[i] == '-m' and i + 1 < len(args):
            mask_path = args[i + 1]
            if not os.path.isabs(mask_path) and not os.path.exists(mask_path):
                mask_path = os.path.join(REPO_ROOT, mask_path)
            with open(mask_path) as mf:
                mask_map = json.load(mf)
            mask_ids = set()
            for k in mask_map:
                # extract numeric ID from keys like oss-fuzz:42534949
                if k.startswith('oss-fuzz:'):
                    num = k.split(':', 1)[1]
                    if num.isdigit():
                        mask_ids.add(int(num))
            i += 2
        else:
            print(f"unknown flag: {args[i]}")
            sys.exit(1)

    if sort:
        query = f"{query.rstrip(';')} ORDER BY {sort} {'DESC' if desc else 'ASC'}"

    if limit:
        query = f"{query.rstrip(';')} LIMIT {limit}"

    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    cur = db.cursor()
    cur.execute(query)

    if out:
        out_dir = os.path.dirname(out)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        f = open(out, 'w')
    else:
        f = sys.stdout

    count = 0
    for row in cur:
        if mask_ids is not None and row['localId'] not in mask_ids:
            continue
        f.write(json.dumps(dict(row)) + '\n')
        count += 1

    if out:
        f.close()
        print(f"wrote {count} rows → {out}", file=sys.stderr)
    else:
        print(f"\n-- {count} rows", file=sys.stderr)

    db.close()

if __name__ == '__main__':
    main()
