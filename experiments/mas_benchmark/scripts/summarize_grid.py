"""Mean (std) over seeds of results/grid.jsonl per scenario and method -> results/summary.md.

    python scripts/summarize_grid.py [--horizon 120]
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

RES = Path(__file__).resolve().parents[1] / 'results'
COLS = [('cost', 'cost', 3), ('min_dist_team', 'min d team', 2), ('viol_team', 'viol team %', 2),
        ('min_dist_ext', 'min d ext', 2), ('viol_ext', 'viol ext %', 2), ('imbalance', 'imbalance', 2),
        ('imbalance_same_w', 'imb same w', 2), ('imbalance_diff_w', 'imb diff w', 2), ('gap_min', 'gap min', 3),
        ('stop_frac', 'stopped %', 1), ('longest_stop_s', 'longest stop s', 1)]
PCT = {'viol_team', 'viol_ext', 'stop_frac'}

ap = argparse.ArgumentParser()
ap.add_argument('--horizon', type=float, default=120.0)
args = ap.parse_args()

rows = [json.loads(l) for l in (RES / 'grid.jsonl').read_text().splitlines()]
groups = defaultdict(list)
for r in rows:
    if r['horizon'] == args.horizon:
        groups[(r['scenario'], r['solver'])].append(r)


def cell(vals, key, nd):
    v = np.array([x for x in vals if x is not None and not np.isnan(x)], dtype=float)
    if not len(v):
        return '–'
    if key in PCT:
        v = 100 * v
    if key.startswith('min_dist'):        # worst case over seeds is the safety-relevant number
        return f'{v.min():.{nd}f}'
    return f'{v.mean():.{nd}f} ({v.std():.{nd}f})'


out = [f'# Grid summary ({args.horizon:g} s; mean (std) over seeds; min distances are the minimum over seeds)', '']
for sc in sorted({s for s, _ in groups}):
    out += [f'## {sc}', '', '| method | n | ' + ' | '.join(c[1] for c in COLS) + ' |',
            '|---|---|' + '---|' * len(COLS)]
    for (s, m), g in sorted(groups.items()):
        if s == sc:
            out.append(f'| {m} | {len(g)} | ' + ' | '.join(cell([r.get(k) for r in g], k, nd) for k, _, nd in COLS) + ' |')
    out.append('')
(RES / 'summary.md').write_text('\n'.join(out))
print('\n'.join(out))
