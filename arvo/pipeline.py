"""usage:
  python3 pipeline.py export <project>    export cybergym+arvo data + summary
  python3 pipeline.py summary <project>   summary only (needs existing jsonl)
  python3 pipeline.py list [-p <project>] list project counts in cybergym vs arvo

examples:
  python3 pipeline.py export ffmpeg
  python3 pipeline.py list
  python3 pipeline.py list -p binutils-gdb
"""

import json
import sys
import os
import sqlite3
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
META_DIR = os.path.join(SCRIPT_DIR, 'ARVO-Meta', 'archive_data', 'meta')
DB_PATH = os.path.join(SCRIPT_DIR, 'arvo.db')
MASK_PATH = os.path.join(os.path.dirname(SCRIPT_DIR), 'mask_map.json')
PROJECTS_DIR = os.path.join(SCRIPT_DIR, 'projects')
SUMMARY_PATH = os.path.join(SCRIPT_DIR, 'project_summary.jsonl')

META2JSONL = os.path.join(SCRIPT_DIR, 'meta2jsonl.py')
SQL2JSONL = os.path.join(SCRIPT_DIR, 'sql2jsonl.py')
SUMMARY = os.path.join(SCRIPT_DIR, 'summary.py')


def load_mask_sets():
    with open(MASK_PATH) as f:
        mask = json.load(f)
    arvo_ids, oss_ids = set(), set()
    for k in mask:
        num = k.split(':', 1)[1]
        if not num.isdigit():
            continue
        if k.startswith('arvo:'):
            arvo_ids.add(int(num))
        elif k.startswith('oss-fuzz:'):
            oss_ids.add(int(num))
    return arvo_ids, oss_ids


def count_cybergym(project, arvo_ids, oss_ids):
    """count cybergym instances for a project from both sources"""
    meta_count = 0
    for fid in arvo_ids:
        path = os.path.join(META_DIR, f'{fid}.json')
        if os.path.exists(path):
            row = json.load(open(path))
            if row.get('project') == project:
                meta_count += 1

    db_count = 0
    if oss_ids:
        db = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
        for fid in oss_ids:
            row = db.execute('SELECT project FROM arvo WHERE localId=?', [fid]).fetchone()
            if row and row['project'] == project:
                db_count += 1
        db.close()

    return meta_count, db_count


def _annotate_cybergym(arvo_file, cyb_file):
    """add in_cybergym field to arvo jsonl based on cybergym jsonl"""
    # collect all modern IDs from cybergym
    cyb_ids = set()
    with open(cyb_file) as f:
        for line in f:
            d = json.loads(line)
            mid = d.get('modern_localId') or d.get('localId')
            if mid:
                cyb_ids.add(mid)

    # rewrite arvo file with in_cybergym field
    tmp = arvo_file + '.tmp'
    count = 0
    with open(arvo_file) as fin, open(tmp, 'w') as fout:
        for line in fin:
            d = json.loads(line)
            d['in_cybergym'] = d['localId'] in cyb_ids
            if d['in_cybergym']:
                count += 1
            fout.write(json.dumps(d) + '\n')
    os.replace(tmp, arvo_file)
    return count


def cmd_export(project):
    out_dir = os.path.join(PROJECTS_DIR, project)
    os.makedirs(out_dir, exist_ok=True)

    arvo_file = os.path.join(out_dir, f'{project}.jsonl')
    cyb_file = os.path.join(out_dir, f'cybergym_{project}.jsonl')

    print(f"[1/3] exporting arvo (full) for {project} ...")
    subprocess.run([sys.executable, SQL2JSONL, DB_PATH,
                    f"SELECT * FROM arvo WHERE project='{project}'",
                    '-o', arvo_file], check=True)

    print(f"[2/3] exporting cybergym subset for {project} ...")
    subprocess.run([sys.executable, META2JSONL, META_DIR,
                    '-p', project, '-m', MASK_PATH, '-o', cyb_file], check=True)

    in_cyb = _annotate_cybergym(arvo_file, cyb_file)

    print(f"[3/3] summarizing ...")
    _rebuild_summary_line(project, arvo_file, 'arvo')
    _rebuild_summary_line(project, cyb_file, 'cybergym')

    # show counts
    with open(arvo_file) as f:
        n_arvo = sum(1 for _ in f)
    with open(cyb_file) as f:
        n_cyb = sum(1 for _ in f)
    print(f"done: arvo={n_arvo} (in_cybergym={in_cyb}), cybergym={n_cyb} → {SUMMARY_PATH}")


def _rebuild_summary_line(project, jsonl_path, source):
    """replace existing summary line for this project+source, or append"""
    lines = []
    if os.path.exists(SUMMARY_PATH):
        with open(SUMMARY_PATH) as f:
            for l in f:
                d = json.loads(l)
                if not (d['project'] == project and d.get('source') == source):
                    lines.append(l.strip())

    subprocess.run([sys.executable, SUMMARY, jsonl_path,
                    '--source', source, '-o', SUMMARY_PATH + '.tmp'], check=True)

    # read the new line from tmp
    with open(SUMMARY_PATH + '.tmp') as f:
        new_line = f.read().strip()

    with open(SUMMARY_PATH, 'w') as f:
        for l in lines:
            f.write(l + '\n')
        f.write(new_line + '\n')
    os.remove(SUMMARY_PATH + '.tmp')


def cmd_list(project_filter=None):
    arvo_ids, oss_ids = load_mask_sets()

    # collect all projects from both cybergym sources
    projects = {}

    # from meta
    for fid in arvo_ids:
        path = os.path.join(META_DIR, f'{fid}.json')
        if os.path.exists(path):
            p = json.load(open(path)).get('project', 'unknown')
            if project_filter and p != project_filter:
                continue
            if p not in projects:
                projects[p] = {'cyb_meta': 0, 'cyb_db': 0, 'arvo': 0}
            projects[p]['cyb_meta'] += 1

    # from db
    if oss_ids:
        db = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
        for fid in oss_ids:
            row = db.execute('SELECT project FROM arvo WHERE localId=?', [fid]).fetchone()
            if row:
                p = row['project']
                if project_filter and p != project_filter:
                    continue
                if p not in projects:
                    projects[p] = {'cyb_meta': 0, 'cyb_db': 0, 'arvo': 0}
                projects[p]['cyb_db'] += 1
        db.close()

    # arvo totals
    db = sqlite3.connect(DB_PATH)
    if project_filter:
        rows = db.execute("SELECT project, COUNT(*) c FROM arvo WHERE project=? GROUP BY project",
                          [project_filter]).fetchall()
    else:
        rows = db.execute("SELECT project, COUNT(*) c FROM arvo GROUP BY project ORDER BY c DESC").fetchall()
    for p, c in rows:
        if p not in projects:
            projects[p] = {'cyb_meta': 0, 'cyb_db': 0, 'arvo': 0}
        projects[p]['arvo'] = c
    db.close()

    # sort by cybergym total
    sorted_p = sorted(projects.items(), key=lambda x: -(x[1]['cyb_meta'] + x[1]['cyb_db']))

    if project_filter:
        for p, c in sorted_p:
            cyb = c['cyb_meta'] + c['cyb_db']
            print(f"{p}: cybergym={cyb} (meta={c['cyb_meta']}, db={c['cyb_db']}), arvo={c['arvo']}")
    else:
        print(f"{'project':<30s} {'cybergym':>8s} {'arvo':>8s}")
        print(f"{'-'*30} {'-'*8} {'-'*8}")
        for p, c in sorted_p:
            cyb = c['cyb_meta'] + c['cyb_db']
            if cyb == 0 and c['arvo'] == 0:
                continue
            print(f"{p:<30s} {cyb:>8d} {c['arvo']:>8d}")


def main():
    args = sys.argv[1:]
    if not args or args[0] in ('-h', '--help'):
        print(__doc__)
        sys.exit(1)

    cmd = args[0]

    if cmd == 'export':
        if len(args) < 2:
            print("usage: pipeline.py export <project>")
            sys.exit(1)
        cmd_export(args[1])

    elif cmd == 'summary':
        if len(args) < 2:
            print("usage: pipeline.py summary <project>")
            sys.exit(1)
        project = args[1]
        out_dir = os.path.join(PROJECTS_DIR, project)
        arvo_file = os.path.join(out_dir, f'{project}.jsonl')
        cyb_file = os.path.join(out_dir, f'cybergym_{project}.jsonl')
        _rebuild_summary_line(project, arvo_file, 'arvo')
        _rebuild_summary_line(project, cyb_file, 'cybergym')
        print(f"summarized {project} → {SUMMARY_PATH}")

    elif cmd == 'list':
        project = None
        i = 1
        while i < len(args):
            if args[i] == '-p' and i + 1 < len(args):
                project = args[i + 1]
                i += 2
            else:
                i += 1
        cmd_list(project)

    else:
        print(f"unknown command: {cmd}")
        sys.exit(1)


if __name__ == '__main__':
    main()
