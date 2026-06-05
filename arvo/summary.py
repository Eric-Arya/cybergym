"""usage:
  python3 summary.py <project.jsonl> [-o <summary.jsonl>] [--source <label>]

  reads project jsonl, counts each crash type against known list,
  appends one line to project_summary.jsonl

examples:
  python3 summary.py binutils.jsonl
  python3 summary.py binutils.jsonl --source arvo -o project_summary.jsonl
  python3 summary.py projects/binutils/cybergym_binutils.jsonl --source cybergym
"""

import json
import sys
import os
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# from crash_type.md
KNOWN_CRASH_TYPES = [
    "Heap-buffer-overflow READ",
    "Use-of-uninitialized-value",
    "Wild-address READ",
    "Heap-buffer-overflow WRITE",
    "Heap-use-after-free READ",
    "Stack-buffer-overflow READ",
    "Stack-buffer-overflow WRITE",
    "Index-out-of-bounds",
    "Global-buffer-overflow READ",
    "Wild-address WRITE",
    "Heap-double-free",
    "Negative-size-param",
    "Bad-cast",
    "Bad-free",
    "Use-after-poison READ",
    "Stack-use-after-return READ",
    "Heap-use-after-free WRITE",
    "Null-dereference READ",
    "Memcpy-param-overlap",
    "Stack-buffer-underflow READ",
    "Global-buffer-overflow WRITE",
    "Stack-use-after-scope READ",
    "Container-overflow READ",
    "Use-after-poison WRITE",
    "Dynamic-stack-buffer-overflow WRITE",
    "Incorrect-function-pointer-type",
    "Container-overflow WRITE",
    "Stack-buffer-underflow WRITE",
    # additional types found in DB
    "Dynamic-stack-buffer-overflow READ",
    "Invalid-free",
    "Segv on unknown address",
    "Stack-use-after-scope WRITE",
    "UNKNOWN READ",
    "UNKNOWN WRITE",
]


def normalize(ct):
    """strip trailing noise: number, {*}, extra READ/WRITE suffix"""
    ct = ct.strip()
    ct = re.sub(r' \{?\*\}?$', '', ct)
    ct = re.sub(r' \d+$', '', ct)
    return ct


def main():
    args = sys.argv[1:]
    if not args or args[0] in ('-h', '--help'):
        print(__doc__)
        sys.exit(1)

    jsonl_path = args[0]
    out_path = None
    source = None
    i = 1
    while i < len(args):
        if args[i] == '-o' and i + 1 < len(args):
            out_path = args[i + 1]
            i += 2
        elif args[i] == '--source' and i + 1 < len(args):
            source = args[i + 1]
            i += 2
        else:
            print(f"unknown flag: {args[i]}")
            sys.exit(1)

    counts = {t: 0 for t in KNOWN_CRASH_TYPES}
    unknown = {}
    project = None

    with open(jsonl_path) as f:
        for line in f:
            row = json.loads(line)
            if project is None:
                project = row.get('project', 'unknown')
            ct = normalize(row.get('crash_type', ''))
            if ct in counts:
                counts[ct] += 1
            else:
                unknown[ct] = unknown.get(ct, 0) + 1

    for ct, n in unknown.items():
        print(f"warning: unknown '{ct}': {n}", file=sys.stderr)

    out = {}
    if source is not None:
        out['source'] = source
    out['project'] = project
    out['total_known'] = sum(counts.values())
    out['total_unknown'] = sum(unknown.values())
    out.update(counts)
    out['_unknown'] = unknown

    if not out_path:
        out_path = os.path.join(SCRIPT_DIR, 'project_summary.jsonl')

    with open(out_path, 'a') as f:
        f.write(json.dumps(out) + '\n')

    print(f"appended {project} → {out_path} (known={out['total_known']}, unknown={out['total_unknown']})", file=sys.stderr)


if __name__ == '__main__':
    main()
