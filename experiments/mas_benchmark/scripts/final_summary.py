"""Paper tables and figure from results/final_mutual/grid.jsonl (+ load_transfer.md).

    python scripts/final_summary.py  -> results/final_mutual/summary.md, results/final_mutual/tradeoff_S3_S4.pdf
"""
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parents[1] / 'results' / 'final_mutual'
rows = [json.loads(l) for l in (OUT / 'grid.jsonl').read_text().splitlines()]
g = defaultdict(list)
for r in rows:
    g[(r['scenario'], r['solver'])].append(r)
BASE = [('oracle', 'Oracle'), ('tan', 'Tan'), ('pcca', 'PCCA'), ('risk_ratio', 'Risk ratio'), ('reciprocal', 'Reciprocal')]
OURS = [(f'ours_eps{e}_mutual', f'Ours, ε = {e}') for e in ('0.1', '0.2', '0.3')]
PRIOR = [(f'ours_eps{e}{w}_mutual', f'ε = {e}, w0 = {w[2:] or "0.97"}') for e in ('0.1', '0.2', '0.3')
         for w in ('_w1', '_w0.99', '', '_w0.9')]


def mean_se(v):
    v = np.array([x for x in v if x is not None and np.isfinite(x)], dtype=float)
    if not len(v):
        return np.nan, np.nan
    return float(v.mean()), float(v.std(ddof=1) / np.sqrt(len(v))) if len(v) > 1 else 0.0


def fmt(v, pct=False, nd=3):
    m, s = mean_se(v)
    if np.isnan(m):
        return '–'
    return f'{100 * m:.2f} ± {100 * s:.2f}' if pct else f'{m:.{nd}f} ± {s:.{nd}f}'


def mins(v):
    v = [x for x in v if x is not None and np.isfinite(x)]
    return f'{min(v):.2f}' if v else '–'


L = ['# Final experiments (replaces v41 Sec. 12.2)', '',
     'Ours: pairwise specification; mutual-trust exchange (m = w_ik(F) w_ki(F)); default step 1/(2 k_e); fixed risk '
     'δ = 0.05 per neighbour; in-layer coefficient a = w/(w + k_e α²) with public w = 1. Baselines as in Sec. 12.1. '
     'Six seeds × 120 s per scenario and method, the same seeds for every method. Mean ± standard error over seeds; '
     'minimum distances are the minimum over seeds; time in violation is the fraction of steps with some pair closer '
     'than 0.95ρ (toward externals, and among agents).', '']
for sc in ('S1', 'S2', 'S3', 'S4'):
    L += [f'## {sc}', '', '| method | cost | min dist. (agents) | time in violation, agents (%) | '
          'min dist. (externals) | time in violation, externals (%) |', '|---|---|---|---|---|---|']
    for key, label in BASE + OURS:
        rr = g.get((sc, key), [])
        if not rr:
            continue
        L.append(f'| {label} | {fmt([r["cost"] for r in rr])} | {mins([r["min_dist_team"] for r in rr])} | '
                 f'{fmt([r["viol_team"] for r in rr], pct=True)} | {mins([r["min_dist_ext"] for r in rr])} | '
                 f'{fmt([r["viol_ext"] for r in rr], pct=True)} |')
    L.append('')

L += ['## S1: efficiency and prices', '',
      'Price imbalance |μ_i − μ_k|/(μ_i + μ_k) over isolated two-agent encounters, averaged over encounter steps '
      '(time-weighted), overall, for equal-weight pairs and for 1-vs-3 pairs. Copy gap: max over agreements and steps '
      'of |r_ik + r_ki|.', '',
      '| method | cost | cost / Oracle | cost / Tan | imbalance, all | equal weights | 1 vs 3 | max |r_ik + r_ki| |',
      '|---|---|---|---|---|---|---|---|']
c_or = mean_se([r['cost'] for r in g[('S1', 'oracle')]])[0]
c_tan = mean_se([r['cost'] for r in g[('S1', 'tan')]])[0]
for key, label in BASE + OURS:
    rr = g.get(('S1', key), [])
    if not rr:
        continue
    c = mean_se([r['cost'] for r in rr])[0]
    gap = max((r['gap_max'] for r in rr if r.get('gap_max') is not None and np.isfinite(r['gap_max'])), default=None)
    L.append(f'| {label} | {fmt([r["cost"] for r in rr])} | {c / c_or:.2f} | {c / c_tan:.2f} | '
             f'{fmt([r.get("imbalance_time") for r in rr], nd=2)} | {fmt([r.get("imbalance_time_same_w") for r in rr], nd=2)} | '
             f'{fmt([r.get("imbalance_time_diff_w") for r in rr], nd=2)} | {"–" if gap is None else f"{gap:.1e}"} |')
L.append('')

L += ['## Prior sweep (Ours): cost and time in violation toward externals (%)', '',
      '| setting | S1 cost | S2 cost | S2 ext. (%) | S3 cost | S3 ext. (%) | S4 cost | S4 ext. (%) | S4 agents (%) |',
      '|---|---|---|---|---|---|---|---|---|']
for key, label in PRIOR:
    c = [g.get((sc, key), []) for sc in ('S1', 'S2', 'S3', 'S4')]
    L.append(f'| {label} | {fmt([r["cost"] for r in c[0]])} | {fmt([r["cost"] for r in c[1]])} | '
             f'{fmt([r["viol_ext"] for r in c[1]], pct=True)} | {fmt([r["cost"] for r in c[2]])} | '
             f'{fmt([r["viol_ext"] for r in c[2]], pct=True)} | {fmt([r["cost"] for r in c[3]])} | '
             f'{fmt([r["viol_ext"] for r in c[3]], pct=True)} | {fmt([r["viol_team"] for r in c[3]], pct=True)} |')
L.append('')
L += ['## Load transfer', '', (OUT / 'load_transfer.md').read_text().split('\n', 2)[2], '',
      '## Figures', '', '- `tradeoff_S3_S4.pdf`: cost against time in violation toward externals, S3 and S4, mean ± '
      'standard error over six seeds (Ours over ε for each prior w0; baselines as points).',
      '- `virial_S4.pdf`: virial pressure P_i = Σ_k λ_ik ‖d_ik‖² over agents in one S4 frame.']
(OUT / 'summary.md').write_text('\n'.join(L) + '\n')
print('\n'.join(L))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.size': 8, 'pdf.fonttype': 42})
fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0))
for ax, sc in zip(axes, ('S3', 'S4')):
    for w, style in (('', dict(color='tab:blue', lw=1.4, marker='o', ms=4, label='Ours, $w_0=0.97$')),
                     ('_w1', dict(color='tab:cyan', lw=0.8, marker='s', ms=3, label='Ours, $w_0=1$')),
                     ('_w0.99', dict(color='tab:purple', lw=0.8, marker='^', ms=3, label='Ours, $w_0=0.99$')),
                     ('_w0.9', dict(color='tab:green', lw=0.8, marker='v', ms=3, label='Ours, $w_0=0.9$'))):
        pts = []
        for e in ('0.1', '0.2', '0.3'):
            rr = g.get((sc, f'ours_eps{e}{w}_mutual'), [])
            if rr:
                (cx, sx), (cy, sy) = mean_se([r['cost'] for r in rr]), mean_se([100 * r['viol_ext'] for r in rr])
                pts.append((cx, sx, cy, sy, e))
        if pts:
            x, sx, y, sy, e = zip(*pts)
            ax.errorbar(x, y, xerr=sx, yerr=sy, capsize=2, elinewidth=0.6, **style)
            if w == '':
                for xi, yi, ei in zip(x, y, e):
                    ax.annotate(f'ε={ei}', (xi, yi), fontsize=6, xytext=(3, 3), textcoords='offset points')
    for key, label in BASE:
        rr = g.get((sc, key), [])
        if rr:
            (cx, sx), (cy, sy) = mean_se([r['cost'] for r in rr]), mean_se([100 * r['viol_ext'] for r in rr])
            ax.errorbar([cx], [cy], xerr=[sx], yerr=[sy], fmt='x', color='k', ms=5, capsize=2, elinewidth=0.6)
            ax.annotate(label, (cx, cy), fontsize=6, xytext=(3, -8), textcoords='offset points')
    ax.set_yscale('symlog', linthresh=0.1)
    ax.set_xlabel('cost')
    ax.set_ylabel('time in violation toward externals (%)')
    ax.set_title(sc)
axes[0].legend(fontsize=6, loc='upper right')
fig.tight_layout()
fig.savefig(OUT / 'tradeoff_S3_S4.pdf')
