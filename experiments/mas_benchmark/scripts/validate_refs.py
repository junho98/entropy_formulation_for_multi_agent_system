"""Reproduce the reference papers' claims for the baselines; writes results/validation.md.

    python scripts/validate_refs.py
"""
from pathlib import Path

from mas_benchmark.validation import all_checks

rows = all_checks()
lines = ['# Baseline validation against the reference papers', '',
         '| method | claim | source | measured | result |', '|---|---|---|---|---|']
for r in rows:
    res = 'pass' if r['passed'] else 'FAIL'
    if r['note']:
        res += f" ({r['note']})"
    lines.append(f"| {r['method']} | {r['claim']} | {r['source']} | {r['measured']} | {res} |")
out = Path(__file__).resolve().parents[1] / 'results' / 'validation.md'
out.parent.mkdir(exist_ok=True)
out.write_text('\n'.join(lines) + '\n')
print('\n'.join(lines))
