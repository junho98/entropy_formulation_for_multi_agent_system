"""Beta variant sweep vs the final configuration. S1 and S4, eps 0.1, 6 seeds x 120 s, same seeds.

    python scripts/run_beta.py [--workers 11]  -> results/beta.{jsonl,md}
"""
import argparse
import json
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from mas_benchmark.analyzers import BetaReading, Cost, FairOverTime, PriceImbalance, Safety
from mas_benchmark.core import simulate
from mas_benchmark.dynamics import SingleIntegrator
from mas_benchmark.scenarios import make_scenario
from mas_benchmark.solvers import make_solver
from mas_benchmark.specs import PairwiseBarrier

RES = Path(__file__).resolve().parents[1] / 'results'
WB = 16.88    # mean final W_i of the final-configuration S1 run (seed 0, 120 s)
VARIANTS = {'final': 'ours_eps0.1_mutual',
            'beta, W0 = 1x, no leak': f'beta_eps0.1_W0{WB:g}_leakinf',
            'beta, W0 = 1x, leak 30 s': f'beta_eps0.1_W0{WB:g}_leak30',
            'beta, W0 = 0.5x, no leak': f'beta_eps0.1_W0{0.5 * WB:g}_leakinf',
            'beta, W0 = 0.5x, leak 30 s': f'beta_eps0.1_W0{0.5 * WB:g}_leak30',
            'beta, W0 = 1x, no leak, read on constrained steps (diagnostic)': f'beta_eps0.1_W0{WB:g}_leakinf_rc'}


def job(sc, var, seed):
    log = simulate(make_scenario(sc), SingleIntegrator(), PairwiseBarrier(), make_solver(VARIANTS[var]), 120.0, 0.02, seed)
    return dict(scenario=sc, variant=var, seed=seed, **Cost()(log), **Safety()(log),
                **PriceImbalance()(log), **FairOverTime()(log), **BetaReading()(log))


def ms(v, pct=False, nd=3):
    v = np.array([x for x in v if x is not None and np.isfinite(x)], float)
    if not len(v):
        return '–'
    m, s = v.mean(), (v.std(ddof=1) / np.sqrt(len(v)) if len(v) > 1 else 0.0)
    return f'{100 * m:.2f} ± {100 * s:.2f}' if pct else f'{m:.{nd}f} ± {s:.{nd}f}'


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=11)
    args = ap.parse_args()
    jobs = [(sc, v, s) for sc in ('S1', 'S4') for v in VARIANTS for s in range(6)]
    with ProcessPoolExecutor(args.workers) as ex:
        rows = list(ex.map(job, *zip(*jobs)))
    (RES / 'beta.jsonl').write_text('\n'.join(json.dumps(r) for r in rows) + '\n')
    g = defaultdict(list)
    for r in rows:
        g[(r['scenario'], r['variant'])].append(r)
    L = ['# Beta variant: own cost weighted by beta_i = min(exp(W_i/W0), 4)', '',
         f'Final configuration (pairwise, mutual law, step 1/(2 k_e), delta = 0.05 per neighbour) with one change '
         f'(solvers/thermo/beta.py). W0 in {{1, 0.5}} x {WB:.2f} (mean final W_i of the final-configuration S1 run), leak '
         f'1/kappa in {{inf, 30 s}}, beta_max = 4. eps = 0.1, 6 seeds x 120 s, same seeds; mean ± s.e. W std/mean is the '
         f'true accumulated base cost without leak (from the log).', '']
    for sc in ('S1', 'S4'):
        L += [f'## {sc}', '',
              '| setting | cost | W std/mean | W range | min dist. agents | viol. agents (%) | min dist. ext. | viol. ext. (%) | '
              'max |r_ik+r_ki| | imbalance (time-w.) | w~ read exact / within 1 grid step | mean |ln(w~/true)| | max w~ | '
              'P(not following), true followers (mean / p95) |',
              '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
        for v in VARIANTS:
            rr = g[(sc, v)]
            L.append(f"| {v} | {ms([r['cost'] for r in rr])} | {ms([r['W_cv'] for r in rr])} | {ms([r['W_range'] for r in rr], nd=2)} | "
                     f"{min(r['min_dist_team'] for r in rr):.2f} | {ms([r['viol_team'] for r in rr], pct=True)} | "
                     f"{np.nanmin([r['min_dist_ext'] for r in rr]):.2f} | {ms([r['viol_ext'] for r in rr], pct=True)} | "
                     f"{max(r['gap_max'] for r in rr):.2g} | {ms([r.get('imbalance_time') for r in rr], nd=2)} | "
                     f"{np.nanmean([r.get('read_exact', np.nan) for r in rr]):.2f} / {np.nanmean([r.get('read_within1', np.nan) for r in rr]):.2f} | "
                     f"{np.nanmean([r.get('read_logerr', np.nan) for r in rr]):.2f} | {np.nanmax([r.get('wt_max', np.nan) for r in rr]):.2g} | "
                     f"{np.nanmean([r['p_not_follow_mean'] for r in rr]):.3f} / {np.nanmean([r['p_not_follow_p95'] for r in rr]):.3f} |")
        L.append('')
    (RES / 'beta.md').write_text('\n'.join(L) + '\n')
    print('\n'.join(L))
