# gen_task

CLI: `python3 -m cybergym.task.gen_task`

Generates a task workspace for an AI agent — copies vulnerability source and metadata from `data_dir`, writes a README with instructions, and creates a `submit.sh` for PoC verification.

## Workflow

```
data_dir/arvo/10400/            out_dir/
  repo-vul.tar.gz    ──copy──►   repo-vul.tar.gz
  description.txt    ──copy──►   description.txt
  (template)         ──gen───►   README.md
  (template)         ──gen───►   submit.sh
```

## Difficulty levels

| Level | Files given to agent |
|-------|---------------------|
| level0 | `repo-vul.tar.gz` only |
| level1 | + `description.txt` |
| level2 | + `error.txt` |
| level3 | + `repo-fix.tar.gz`, `patch.diff`, `error.txt` |

## Task ID masking

If `--mask-map mask_map.json` is provided, the real task ID (e.g., `arvo:10400`) is replaced with a 12-char opaque UUID in `submit.sh`. The agent never sees the real CVE ID.

## Key flags

```
--task-id arvo:10400     # which vulnerability
--data_dir ./cybergym_data  # canonical source data
--out_dir ./workspace    # where to write the task
--server http://x:8666   # PoC verification server
--difficulty level1      # how much info to reveal
--agent-id <id>          # optional, auto-generated if omitted
--mask-map mask_map.json # enable task ID masking
--with-flag              # return flag on successful crash
```

## Output

```
out_dir/
├── repo-vul.tar.gz      # vulnerable source code
├── description.txt       # human-readable bug description
├── README.md            # agent instructions
└── submit.sh            # curl wrapper to submit PoC to server
```
