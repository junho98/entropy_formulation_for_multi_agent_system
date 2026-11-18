"""Tables and figures for the 2x3 grid -> results/grid2x3/summary.md (+ tradeoff_E4_E8.pdf, range_vs_time.pdf).

    python scripts/grid2x3_summary.py   (works on a partial horizon.jsonl: the horizon section lists what is there)
"""
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from mas_benchmark.scenarios import GRID2X3
from mas_benchmark.viz import results, style

OUT = Path(__file__).resolve().parents[1] / 'results' / 'grid2x3'
METHODS = [('oracle', 'Oracle'), ('tan', 'Tan'), ('pcca', 'PCCA'), ('risk_ratio', 'Risk ratio'), ('reciprocal', 'Reciprocal'),
           ('final', 'Ours, ε = 0.1'), ('ours_eps0.2_mutual', 'Ours, ε = 0.2'), ('ours_eps0.3_mutual', 'Ours, ε = 0.3'),
           ('centred', 'Ours + centred β, ε = 0.1')]
T_AT = ('120', '240', '360', '480', '600')


def load(name):
    p = OUT / name
    return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []


def ms(v, nd=3, pct=False):
    v = np.array([x for x in v if x is not None and np.isfinite(x)], float)
    if len(v) < 2:
        return '–' if not len(v) else (f'{100 * v[0]:.2f}' if pct else f'{v[0]:.{nd}f}')
    m, s = v.mean(), v.std(ddof=1) / np.sqrt(len(v))
    return f'{100 * m:.2f} ± {100 * s:.2f}' if pct else f'{m:.{nd}f} ± {s:.{nd}f}'


def mn(v):
    v = [x for x in v if x is not None and np.isfinite(x)]
    return f'{min(v):.2f}' if v else '–'


def paired(A, B, key, scale=1.0, nd=3):
    s = sorted(set(A) & set(B))
    return ms([scale * (B[k][key] - A[k][key]) for k in s], nd), len(s)


grid, hz = load('grid.jsonl'), load('horizon.jsonl')
cbar = json.loads((OUT / 'cbar.json').read_text()) if (OUT / 'cbar.json').exists() else {}
g = defaultdict(dict)
for r in grid:
    g[(r['scenario'], r['conf'])][r['seed']] = r
h = defaultdict(dict)
for r in hz:
    h[(r['scenario'], r['conf'])][r['seed']] = r

L = ['# 2×3 grid', '',
     'Team of 8 on the circle arena (targets redrawn on arrival). Team: HOM = all w = 1; HET = w alternating 1, 3. '
     'Outsiders: E0 none; E4 / E8 = 4 / 8 outsiders as in S4 (speed 0.8, heading noise 2 rad/√s, never yield); only the '
     'count changes. v_env = 1.0 for E4/E8 (as S4); E0 uses 1.2 as S1 (no outsiders, so it only enters as the public '
     'capability). HET-E0 is S1 and HOM-E8 is S4 (seed 0 reproduces both exactly). Ours: pairwise specification, mutual '
     'law, default step, δ = 0.05 per neighbour, prior 0.97. Centred β: W0 = 4.22, β_max = 8, ε = 0.1, c̄ per cell = '
     'fleet-mean work rate of the final ε = 0.1 runs of that cell (mean of mean_i W_i(120)/120 over the 24 seeds). '
     '24 seeds (0–23) × 120 s per cell and method, same seeds for all; mean ± s.e. over seeds; minimum distances are '
     'the minimum over seeds; violation = fraction of steps with some pair closer than 0.95ρ. W_i = accumulated base '
     'cost ½ w_i‖u_i − u0_i‖²; range = max_i W_i − min_i W_i. Price imbalance: time-weighted, isolated two-agent '
     'encounters. Copy gap: max over agreements and steps of |r_ik + r_ki|.', '',
     '| c̄ | ' + ' | '.join(GRID2X3) + ' |', '|---|' + '---|' * len(GRID2X3),
     '| fleet-mean work rate | ' + ' | '.join(f'{cbar[c]:.4f}' if c in cbar else '–' for c in GRID2X3) + ' |', '']
for sc in GRID2X3:
    ext = not sc.endswith('E0')
    L += [f'## {sc}', '',
          '| method | n | cost | min dist. (outsiders) | viol. outsiders (%) | min dist. (team) | viol. team (%) | '
          'W std/mean | Jain | W range | price imbalance | max \\|r_ik + r_ki\\| | stop fraction |',
          '|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for key, name in METHODS:
        D = g.get((sc, key), {})
        if not D:
            continue
        R = list(D.values())
        ours = key not in ('oracle', 'tan', 'pcca', 'risk_ratio', 'reciprocal')
        gap = f"{max(r['gap_max'] for r in R):.2g}" if ours else '–'
        L.append(f"| {name} | {len(R)} | {ms([r['cost'] for r in R])} | "
                 f"{mn([r['min_dist_ext'] for r in R]) if ext else '–'} | "
                 f"{ms([r['viol_ext'] for r in R], pct=True) if ext else '–'} | {mn([r['min_dist_team'] for r in R])} | "
                 f"{ms([r['viol_team'] for r in R], pct=True)} | {ms([r['W_cv'] for r in R])} | {ms([r['jain'] for r in R])} | "
                 f"{ms([r['W_range'] for r in R], 2)} | {ms([r['imbalance_time'] for r in R], 2) if ours else '–'} | "
                 f"{gap} | {ms([r['stop_frac'] for r in R])} |")
    F, C = g.get((sc, 'final'), {}), g.get((sc, 'centred'), {})
    if F and C:
        a, n = paired(F, C, 'W_cv')
        b, _ = paired(F, C, 'viol_ext', 100, 2)
        c, _ = paired(F, C, 'cost')
        d, _ = paired(F, C, 'W_range', 1, 2)
        L += ['', f'Paired centred β − final (ε = 0.1, n = {n}): Δ W std/mean {a}; Δ W range {d}; '
                  f'Δ viol. outsiders {b if ext else "–"} pp; Δ cost {c}.']
    L.append('')

if hz:
    L += ['## Horizon (600 s)', '', 'Final (ε = 0.1) vs centred β, 12 seeds (0–11), same seeds; Δ = centred − final, paired.', '']
    for sc in GRID2X3:
        F, C = h.get((sc, 'final'), {}), h.get((sc, 'centred'), {})
        s = sorted(set(F) & set(C))
        if not s:
            continue
        L += [f'### {sc} (n = {len(s)})', '', '| t (s) | range: final | centred | Δ | W std/mean: final | centred | Δ |',
              '|---|---|---|---|---|---|---|']
        for t in T_AT:
            fr, cr = [F[k]['at'][t]['W_range'] for k in s], [C[k]['at'][t]['W_range'] for k in s]
            fc, cc = [F[k]['at'][t]['W_cv'] for k in s], [C[k]['at'][t]['W_cv'] for k in s]
            L.append(f'| {t} | {ms(fr, 2)} | {ms(cr, 2)} | {ms(np.subtract(cr, fr), 2)} | {ms(fc)} | {ms(cc)} | '
                     f'{ms(np.subtract(cc, fc))} |')
        L += ['', f"600 s run: cost final {ms([F[k]['cost'] for k in s])}, centred {ms([C[k]['cost'] for k in s])}; "
                  f"viol. team final {ms([F[k]['viol_team'] for k in s], pct=True)} %, centred "
                  f"{ms([C[k]['viol_team'] for k in s], pct=True)} %"
              + (f"; viol. outsiders final {ms([F[k]['viol_ext'] for k in s], pct=True)} %, centred "
                 f"{ms([C[k]['viol_ext'] for k in s], pct=True)} %." if not sc.endswith('E0') else '.'), '']

(OUT / 'summary.md').write_text('\n'.join(L) + '\n')
print('\n'.join(L))

if grid:
    rows = [dict(r, solver=('ours_eps0.1_mutual' if r['conf'] == 'final' else r['solver'])) for r in grid]
    results.tradeoff(rows, OUT / 'tradeoff_E4_E8', scenarios=('HOM-E4', 'HOM-E8', 'HET-E4', 'HET-E8'),
                     centred='beta_', ncols=2)
if hz:
    results.range_vs_time(hz, OUT / 'range_vs_time', scenarios=GRID2X3, confs=(('final', 'final'), ('centred', 'centred')),
                          ncols=3)
