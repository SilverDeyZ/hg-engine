# bak/

Backup files created before pipeline write phases.

## Planned backups

| File | Source | Created by |
|------|--------|------------|
| `trainers.s.bak` | `armips/data/trainers/trainers.s` | Phase 6 write step |

## Procedure

The write phase (`python scripts-custom/smart_random_trainers.py write`) will:
1. Copy `armips/data/trainers/trainers.s` → `bak/trainers.s.bak` before making any changes.
2. Abort if the backup cannot be created.
3. Rewrite species and move fields in `trainers.s` using `final_replacements.csv` and `final_movesets.csv`.

To restore: `cp bak/trainers.s.bak armips/data/trainers/trainers.s`
