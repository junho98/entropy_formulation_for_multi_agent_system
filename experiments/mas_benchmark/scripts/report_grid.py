"""Questions of v40 Sec. 12.1 from results/grid.jsonl.

Q1 (S2, S3) and Q2 (S4): same-seed comparison with the oracle -> results/q12.md
Q4 (S3, S4): cost vs. time in violation toward externals over eps and w0, with baselines -> results/figures/q4_tradeoff.png

    python scripts/report_grid.py
"""
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

RES = Path(__file__).resolve().parents[1] / 'results'
rows = [json.loads(l) for l in (RES / 'grid.jsonl').read_text().splitlines()]
by = {(r['scenario'], r['solver'], r['seed']): r for r in rows if r['horizon'] == 120.0}
solvers = sorted({k[1] for k in by})
seeds = sorted({k[2] for k in by})

# ---- Q1/Q2: per seed, oracle violation vs method violation (externals and team) ----
out = ['# Q1/Q2: same-seed comparison with the oracle (time in violation, %, toward externals | among agents)', '']
for sc in ['S2', 'S3', 'S4']:
    out += [f'## {sc}', '', '| method | ' + ' | '.join(f'seed {s}' for s in seeds) +
            ' | seeds where oracle has 0 ext. violation and method has 0 | mean extra viol. vs oracle (pp) |',
            '|---|' + '---|' * (len(seeds) + 2)]
    for m in solvers:
        cells, ok, tot, extra = [], 0, 0, []
        for s in seeds:
            r, o = by.get((sc, m, s)), by.get((sc, 'oracle', s))
            if r is None or o is None:
                cells.append('–'); continue
            ve, vt = 100 * r['viol_ext'], 100 * r['viol_team']
            cells.append(f'{ve:.2f} \\| {vt:.2f}')
            extra.append(ve - 100 * o['viol_ext'])
            if o['viol_ext'] == 0:
                tot += 1; ok += (r['viol_ext'] == 0 and r['viol_team'] == 0)
        out.append(f'| {m} | ' + ' | '.join(cells) + f' | {ok}/{tot} | {np.mean(extra):+.2f} |' if extra else f'| {m} | ' + ' | '.join(cells) + ' | – | – |')
    out.append('')
(RES / 'q12.md').write_text('\n'.join(out))
print('\n'.join(out))

# ---- Q4: trade-off figure ----
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

agg = defaultdict(list)
for (sc, m, s), r in by.items():
    agg[(sc, m)].append(r)
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
for ax, sc in zip(axes, ['S3', 'S4']):
    for w0, mk in [('', 'o'), ('_w1', 's'), ('_w0.99', '^'), ('_w0.9', 'v')]:
        pts = []
        for eps in ('0.1', '0.2', '0.3'):
            g = agg.get((sc, f'ours_eps{eps}{w0}'))
            if g:
                pts.append((np.mean([r['cost'] for r in g]), 100 * np.mean([r['viol_ext'] for r in g]), eps))
        if pts:
            x, y, e = zip(*pts)
            ax.plot(x, y, marker=mk, label=f"ours w0={w0[2:] or '0.97'}")
            for xi, yi, ei in pts:
                ax.annotate(f'ε={ei}', (xi, yi), fontsize=7, xytext=(3, 3), textcoords='offset points')
    for m in ['oracle', 'tan', 'pcca', 'risk_ratio', 'reciprocal']:
        g = agg.get((sc, m))
        if g:
            ax.scatter(np.mean([r['cost'] for r in g]), 100 * np.mean([r['viol_ext'] for r in g]), marker='x', s=50, color='k')
            ax.annotate(m, (np.mean([r['cost'] for r in g]), 100 * np.mean([r['viol_ext'] for r in g])), fontsize=7,
                        xytext=(3, -9), textcoords='offset points')
    ax.set_yscale('symlog', linthresh=0.1)
    ax.set_xlabel('cost (mean over seeds)')
    ax.set_ylabel('time in violation toward externals [%]')
    ax.set_title(sc)
    ax.legend(fontsize=7)
fig.tight_layout()
(RES / 'figures').mkdir(exist_ok=True)
fig.savefig(RES / 'figures' / 'q4_tradeoff.png', dpi=150)
