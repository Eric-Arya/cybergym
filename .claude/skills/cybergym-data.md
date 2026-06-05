---
name: cybergym-data
description: Export and compare CyberGym vs ARVO project data. Use when asked about project counts, crash types, cybergym subsets, or mapping mask_map.json to ARVO-Meta/arvo.db.
---

# CyberGym Data Pipeline Skill

Invoke this skill when the user asks about CyberGym data, project counts, crash types, or wants to export/compare ARVO vs CyberGym subsets.

## Data sources

```
mask_map.json (1,507 entries)
├── arvo:* (1,368) → ARVO-Meta/archive_data/meta/{id}.json
└── oss-fuzz:* (139) → arvo.db WHERE localId={id}
```

## Pipeline script

Use `arvo/pipeline.py` for all operations:

```bash
# export one project (both cybergym + arvo)
python3 arvo/pipeline.py export ffmpeg

# show project list with counts
python3 arvo/pipeline.py list

# summary only (no file export)
python3 arvo/pipeline.py summary ffmpeg
```

## How mapping works

1. mask_map.json key `arvo:20147` → read `ARVO-Meta/archive_data/meta/20147.json` → get project/crash_type
2. mask_map.json key `oss-fuzz:42534949` → query `arvo.db WHERE localId=42534949` → get project/crash_type
3. Neither mask_map.json nor the meta files contain project names directly — always join via numeric ID
