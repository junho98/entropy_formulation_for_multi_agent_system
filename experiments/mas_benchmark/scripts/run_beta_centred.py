"""Centred beta: beta_i = clip(exp((W_i - cbar t)/W0), 1/beta_max, beta_max), cbar a public per-scenario constant
(fleet-mean rate of W in the final-configuration run: mean final W_i / 120 s). W0 in {1, 0.5, 0.25} x 16.88,
beta_max = 8; otherwise the ThermoBeta default. S1 and S4, eps 0.1, 6 seeds x 120 s. Appends to results/beta.md.

    python scripts/run_beta_centred.py [--workers 11]
"""
import argparse
import json
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from mas_benchmark.analyzers import BetaReading, BetaTuning, Cost, FairOverTime, PriceImbalance, Safety
from mas_benchmark.core import simulate
from mas_benchmark.dynamics import SingleIntegrator
from mas_benchmark.scenarios import make_scenario
from mas_benchmark.solvers import make_solver
from mas_benchmark.specs import PairwiseBarrier
from run_beta_tune import mse, ms

RES = Path(__file__).resolve().parents[1] / 'results'
WB = 16.88
CBAR = {'S1': 10.3774 / 120, 'S4': 29.3127 / 120}     # mean final W_i of the final configuration (6 seeds) / 120 s
FS = (1.0, 0.5, 0.25)


def job(sc, f, seed):
    n = f'beta_eps0.1_W0{f * WB:g}_leakinf_bmax8_cbar{CBAR[sc]:.6g}'
    log = simulate(make_scenario(sc), SingleIntegrator(), PairwiseBarrier(), make_solver(n), 120.0, 0.02, seed)
    return dict(scenario=sc, W0x=f, seed=seed, solver=n, **Cost()(log), **Safety()(log), **PriceImbalance()(log),
                **FairOverTime()(log), **BetaReading()(log), **BetaTuning(8.0)(log))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=11)
    args = ap.parse_args()
    jobs = [(sc, f, s) for sc in ('S1', 'S4') for f in FS for s in range(6)]
    with ProcessPoolExecutor(args.workers) as ex:
        rows = list(ex.map(job, *zip(*jobs)))
    (RES / 'beta_centred.jsonl').write_text('\n'.join(json.dumps(r) for r in rows) + '\n')
    final = defaultdict(list)
    for l in (RES / 'beta.jsonl').read_text().splitlines():
        r = json.loads(l)
        if r['variant'] == 'final':
            W = np.array(r['W'])
            r.update(jain=float(W.sum() ** 2 / (len(W) * np.sum(W ** 2))), W_max=float(W.max()))
            final[r['scenario']].append(r)
    tune = defaultdict(list)
    for l in (RES / 'beta_tune.jsonl').read_text().splitlines():
        r = json.loads(l)
        if r['bmax'] == 8.0:
            tune[(r['scenario'], r['W0x'])].append(r)
    g = defaultdict(list)
    for r in rows:
        g[(r['scenario'], r['W0x'])].append(r)
    cell = lambda rr, sc: (f"{ms([r['cost'] for r in rr])} | {ms([r['W_cv'] for r in rr])} | {ms([r['jain'] for r in rr])} | "
                           f"{ms([r['W_max'] for r in rr], nd=1)} | {ms([r.get('imbalance_time') for r in rr], nd=2)} | "
                           f"{ms([r['viol_team'] for r in rr], pct=True)} | "
                           f"{ms([r['viol_ext'] for r in rr], pct=True) if sc == 'S4' else '–'} | {max(r['gap_max'] for r in rr):.2g} | "
                           f"{np.nanmean([r['p_not_follow_mean'] for r in rr]):.3f} | "
                           f"{np.nanmean([r.get('cap_frac', np.nan) for r in rr]):.2f} | "
                           f"{np.nanmean([r.get('cap_low_frac', np.nan) for r in rr]):.2f} | "
                           f"{np.nanmean([r.get('below1_frac', np.nan) for r in rr]):.2f}")
    L = ['', '## Centred β', '',
         'β_i = clip(exp((W_i − c̄ t)/W0), 1/β_max, β_max), β_max = 8; c̄ public per scenario = mean final W_i of the final '
         f'configuration / 120 s: S1 {CBAR["S1"]:.4f}, S4 {CBAR["S4"]:.4f} (cost units per s; W from 6 seeds: S1 10.38, '
         'S4 29.31). Otherwise the ThermoBeta default (no reading, no leak, β frozen per contact, QP weight = max of the '
         'frozen β over current contacts). Same seeds; mean ± s.e. Rows "uncentred" are the tuning rows with β_max = 8.', '',
         'The max-of-frozen-β rule was **not** replaced by "β of the earliest still-active contact". That needs the start '
         'time stored per contact and a selection by it (two changes, not one line), so it was left as is.', '']
    for sc in ('S1', 'S4'):
        L += [f'### {sc}', '', '| setting | cost | W std/mean | Jain(W) | max W_i | imbalance (time-w.) | viol. agents (%) | '
              'viol. ext. (%) | max |r_ik+r_ki| | P(not following \\| follower) | β at upper cap | β at lower cap | β < 1 |',
              '|---|---|---|---|---|---|---|---|---|---|---|---|---|', f"| final | {cell(final[sc], sc)} |"]
        for f in FS:
            L.append(f'| uncentred, W0 = {f:g}× | {cell(tune[(sc, f)], sc)} |')
            L.append(f'| centred, W0 = {f:g}× | {cell(g[(sc, f)], sc)} |')
        L.append('')
    ev = [(r['scenario'], r['W0x'], r['seed'], e) for r in rows for e in r['viol_events']]
    L += ['### Team violations (centred)', '']
    if ev:
        L += ['| scenario | W0 | seed | t (s) | w_i, w_k | β_i, β_k (QP) | β frozen for the pair (i, k) | contacts | QP β from another contact | min dist. |',
              '|---|---|---|---|---|---|---|---|---|---|']
        for sc, f, s, e in ev:
            L.append(f"| {sc} | {f:g}× | {s} | {e['t']:.1f} | {e['w_i']:g}, {e['w_k']:g} | {e['beta_i']:.2f}, {e['beta_k']:.2f} | "
                     f"{e['pair_beta_i']:.2f}, {e['pair_beta_k']:.2f} | {e['nc_i']}, {e['nc_k']} | {e['from_other_i']}, {e['from_other_k']} | {e['min_dist']:.3f} |")
    else:
        L.append('No team violations.')
    fe = mse([r['viol_ext'] for r in final['S4']])
    L += ['', '### Against the selection criterion', '']
    for f in FS:
        t0 = all(r['viol_team'] == 0 for sc in ('S1', 'S4') for r in g[(sc, f)])
        ext = mse([r['viol_ext'] for r in g[('S4', f)]])[0]
        cv = (np.mean([r['W_cv'] for r in g[('S1', f)]]) + np.mean([r['W_cv'] for r in g[('S4', f)]])) / 2
        L.append(f'- centred, W0 = {f:g}×: team violation 0 in S1 and S4: {t0}; S4 ext. {100 * ext:.2f}% '
                 f'(limit {100 * (fe[0] + fe[1]):.2f}%); mean W std/mean {cv:.3f} (selected tuning cell (1×, 8): 0.234).')
    with (RES / 'beta.md').open('a') as fh:
        fh.write('\n'.join(L) + '\n')
    print('\n'.join(L))
