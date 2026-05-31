# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CyberGym evaluates AI agents on real-world vulnerability analysis. It provides:
- **Task generation** (`cybergym.task`) — creates vulnerability-finding tasks from ARVO and OSS-Fuzz datasets
- **PoC submission server** (`cybergym.server`) — FastAPI server that receives PoCs, runs them in Docker containers against vul/fix binaries, and records results in SQLite
- **Firewall** (`cybergym.firewall`) — Squid-based domain-allowlist proxy that isolates agent containers from direct internet access

## Install & Run

```bash
pip3 install -e '.[dev,server]'
```

Data: clone from HF (~240GB benchmark data, ~10TB full server data):
```bash
git lfs install && git clone https://huggingface.co/datasets/sunblaze-ucb/cybergym cybergym_data
```

## Key Commands

**Lint:** `ruff check src/`

**Start server:**
```bash
python3 -m cybergym.server --host 0.0.0.0 --port 8666 --mask_map_path mask_map.json --log_dir ./server_poc --db_path ./server_poc/poc.db
```

**Generate a task:**
```bash
python3 -m cybergym.task.gen_task --task-id arvo:10400 --out-dir ./out --data-dir ./cybergym_data/data --server http://SERVER_IP:8666 --mask-map mask_map.json --difficulty level1
```

**Task submit.sh** (generated in out-dir) posts PoC via curl to `/submit-vul`.

**Verify agent results:**
```bash
CYBERGYM_API_KEY=cybergym-030a0cd7-5908-4862-8ab9-91f2bfc7b56d python3 scripts/verify_agent_result.py --server http://SERVER_IP:8666 --pocdb_path ./server_poc/poc.db --agent_id <id>
```

**Firewall:**
```bash
python3 -m cybergym.firewall start|stop|stop-all|status
```

## Architecture

### Task pipeline
`gen_task.py` dispatches by `TaskType` (arvo/oss-fuzz/oss-fuzz-latest). Each generator:
1. Computes an agent-facing masked ID via `mask.py` (so agents never see real task IDs)
2. Derives `agent_id` + SHA256 `checksum(task_id, agent_id, salt)` for submission auth
3. Copies data files based on `TaskDifficulty` level, renders `submit.sh` and `README.md` from templates

### Server
FastAPI app with two routers:
- **Public** (`/submit-vul`) — no auth; validates checksum, rate-limits per agent, runs PoC in Docker
- **Private** (`/submit-fix`, `/query-poc`, `/verify-agent-pocs`) — requires `X-API-Key` header

`server_utils.py` resolves `task_id → Docker image`, runs container with `network_mode=none`, captures exit code. Two modes: full (per-task Docker images) and binary-only (shared runner image with mounted binaries via `--binary_dir`).

### PoC storage
`pocdb.py` — SQLAlchemy ORM with SQLite. `PoCRecord` has unique constraint on `(agent_id, task_id, poc_hash)`. Stored at `log_dir/XX/YY/<poc_id>/poc.bin`.

### Mask system
`mask.py` holds module-level `_forward_map` (real→masked) and `_reverse_map` (masked→real). `load_mask_map()` mutates both dicts in-place so all importers share state. Agents receive masked IDs; server unmasks internally.

### Firewall
`FirewallProxyManager` creates a Docker network (`cybergym-internal`) with `internal=True` (no internet route). Runs a Squid container bridged to both internal and default networks, filtering by domain allowlist. Agent containers must be on `cybergym-internal` with `HTTP_PROXY`/`HTTPS_PROXY` set via `proxy.env_vars()`.
