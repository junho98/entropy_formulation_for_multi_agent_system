"""Beta tuning: W0 in {1, 0.5, 0.25} x 16.88 and beta_max in {2, 4, 8}; ThermoBeta default (own beta, neighbours at
public w = 1), no leak. S1 and S4, eps 0.1, 6 seeds x 120 s, same seeds. Appends "Tuning" to results/beta.md.

    python scripts/run_beta_tune.py [--workers 11]
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

RES = Path(__file__).resolve().parents[1] / 'results'
WB = 16.88
CELLS = [(f, b) for f in (1.0, 0.5, 0.25) for b in (2.0, 4.0, 8.0)]


def name(f, b):
    return f'beta_eps0.1_W0{f * WB:g}_leakinf' + ('' if b == 4.0 else f'_bmax{b:g}')


def job(sc, f, b, seed):
    log = simulate(make_scenario(sc), SingleIntegrator(), PairwiseBarrier(), make_solver(name(f, b)), 120.0, 0.02, seed)
    return dict(scenario=sc, W0x=f, bmax=b, seed=seed, **Cost()(log), **Safety()(log), **PriceImbalance()(log),
                **FairOverTime()(log), **BetaReading()(log), **BetaTuning(b)(log))


def ms(v, pct=False, nd=3):
    v = np.array([x for x in v if x is not None and np.isfinite(x)], float)
    if not len(v):
        return '–'
    m, s = v.mean(), (v.std(ddof=1) / np.sqrt(len(v)) if len(v) > 1 else 0.0)
    return f'{100 * m:.2f} ± {100 * s:.2f}' if pct else f'{m:.{nd}f} ± {s:.{nd}f}'


def mse(v):
    v = np.array(v, float)
    return v.mean(), (v.std(ddof=1) / np.sqrt(len(v)))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=11)
    args = ap.parse_args()
    jobs = [(sc, f, b, s) for sc in ('S1', 'S4') for f, b in CELLS for s in range(6)]
    with ProcessPoolExecutor(args.workers) as ex:
        rows = list(ex.map(job, *zip(*jobs)))
    (RES / 'beta_tune.jsonl').write_text('\n'.join(json.dumps(r) for r in rows) + '\n')
    final = defaultdict(list)
    for l in (RES / 'beta.jsonl').read_text().splitlines():
        r = json.loads(l)
        if r['variant'] == 'final':
            W = np.array(r['W'])
            r.update(jain=float(W.sum() ** 2 / (len(W) * np.sum(W ** 2))), W_max=float(W.max()), cap_frac=np.nan)
            final[r['scenario']].append(r)
    g = defaultdict(list)
    for r in rows:
        g[(r['scenario'], r['W0x'], r['bmax'])].append(r)
    L = ['', '## Tuning', '',
         f'ThermoBeta default (own β; neighbours at the public w = 1; no reading), no leak. W0 ∈ {{1, 0.5, 0.25}} × {WB} and '
         f'β_max ∈ {{2, 4, 8}}; ε = 0.1, 6 seeds × 120 s, same seeds; mean ± s.e. All nine cells were rerun with the extra '
         f'logging (the round-1 (1×, 4) and (0.5×, 4) rows had no per-step β logs). Jain index of W = (Σ W)² / (N Σ W²). '
         f'Cap fraction: agent-time with β^QP at β_max.', '']
    keys = lambda rr, sc: (f"{ms([r['cost'] for r in rr])} | {ms([r['W_cv'] for r in rr])} | {ms([r['jain'] for r in rr])} | "
                           f"{ms([r['W_max'] for r in rr], nd=1)} | {ms([r.get('imbalance_time') for r in rr], nd=2)} | "
                           f"{ms([r['viol_team'] for r in rr], pct=True)} | "
                           f"{ms([r['viol_ext'] for r in rr], pct=True) if sc == 'S4' else '–'} | {max(r['gap_max'] for r in rr):.2g} | "
                           f"{np.nanmean([r['p_not_follow_mean'] for r in rr]):.3f} | "
                           f"{np.nanmean([r.get('cap_frac', np.nan) for r in rr]):.2f}")
    for sc in ('S1', 'S4'):
        L += [f'### {sc}', '', '| setting | cost | W std/mean | Jain(W) | max W_i | imbalance (time-w.) | viol. agents (%) | '
              'viol. ext. (%) | max |r_ik+r_ki| | P(not following \\| follower) | β at cap |',
              '|---|---|---|---|---|---|---|---|---|---|---|', f'| final | {keys(final[sc], sc)} |']
        for f, b in CELLS:
            L.append(f'| W0 = {f:g}×, β_max = {b:g} | {keys(g[(sc, f, b)], sc)} |')
        L.append('')
    # team-violation diagnostics
    ev = [(r['scenario'], r['W0x'], r['bmax'], r['seed'], e) for r in rows for e in r['viol_events']]
    L += ['### Team violations: state at the first step of each violating episode', '']
    if ev:
        L += ['| scenario | W0 | β_max | seed | t (s) | w_i, w_k | β_i, β_k (QP) | β frozen for this pair (i, k) | '
              'contacts (i, k) | QP β from another contact (i, k) | min dist. |', '|---|---|---|---|---|---|---|---|---|---|---|']
        for sc, f, b, s, e in ev:
            L.append(f"| {sc} | {f:g}× | {b:g} | {s} | {e['t']:.1f} | {e['w_i']:g}, {e['w_k']:g} | {e['beta_i']:.2f}, {e['beta_k']:.2f} | "
                     f"{e['pair_beta_i']:.2f}, {e['pair_beta_k']:.2f} | {e['nc_i']}, {e['nc_k']} | {e['from_other_i']}, {e['from_other_k']} | "
                     f"{e['min_dist']:.3f} |")
        n_other = sum(e['from_other_i'] or e['from_other_k'] for *_, e in ev)
        L += ['', f'{len(ev)} episodes; in {n_other} the QP weight of at least one agent came from another contact\'s frozen β '
              f'(the max-of-frozen-β rule); in {len(ev) - n_other} both agents used the β frozen for this very pair.']
    else:
        L.append('No team violations in any cell.')
    # selection
    fe = mse([r['viol_ext'] for r in final['S4']])
    ok = []
    for f, b in CELLS:
        t0 = all(r['viol_team'] == 0 for sc in ('S1', 'S4') for r in g[(sc, f, b)])
        ext = mse([r['viol_ext'] for r in g[('S4', f, b)]])
        if t0 and ext[0] <= fe[0] + fe[1]:
            ok.append(((np.mean([r['W_cv'] for r in g[('S1', f, b)]]) + np.mean([r['W_cv'] for r in g[('S4', f, b)]])) / 2, f, b))
    L += ['', '### Selection', '',
          'Criterion: the lowest W std/mean (mean of S1 and S4) among cells with no team violation in S1 and S4 and S4 external '
          f'violation at most the final configuration\'s mean + one s.e. ({100 * fe[0]:.2f} + {100 * fe[1]:.2f} %).', '']
    if ok:
        best = min(ok)
        L.append(f'Selected: W0 = {best[1]:g}×, β_max = {best[2]:g} (mean W std/mean {best[0]:.3f}). Admissible cells: ' +
                 ', '.join(f'({f:g}×, {b:g}): {v:.3f}' for v, f, b in sorted(ok)) + '.')
    else:
        L.append('No cell meets both conditions.')
    with (RES / 'beta.md').open('a') as fh:
        fh.write('\n'.join(L) + '\n')
    print('\n'.join(L))
