# Analyze Success

Analyze `_success.jsonl` trajectory files and produce a JSONL summary with:
- `task_id`: task identifier (from directory name)
- `traj_file`: trajectory filename
- `token_length_sft`: estimated SFT token count (input + output, char/4 heuristic)
- `false_success`: true if agent refused or produced no real PoC
- `poc_explanation`: brief summary of the PoC and vulnerability
- `crash_type`: type of crash triggered (segfault, heap-buffer-overflow, etc.)
- `num_turns`: number of assistant message blocks

## Usage

```
/analyze_success [--traj-dir <dir>] [--output <file>] [--use-tiktoken]
```

## Implementation

Run `python3 scripts/analyze_success.py` with appropriate arguments.
