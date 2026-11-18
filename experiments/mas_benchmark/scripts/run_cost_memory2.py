"""Cost memory, follow-up (a)+(b): constrained-step-only inference, mu clipped to [0, 4], step 1/(2 k_e (1 + mu_max))
('fixed') or 1/(2 k_e (1 + max(mu_i, mu_k))) ('adaptive'). Appends a section to results/cost_memory.md.

    python scripts/run_cost_memory2.py [--workers 11]
"""
import argparse
import json
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from mas_benchmark.analyzers import Cost, FairOverTime, PriceImbalance, Safety
from mas_benchmark.core import simulate
from mas_benchmark.dynamics import SingleIntegrator
from mas_benchmark.scenarios import make_scenario
from mas_benchmark.solvers import make_solver
from mas_benchmark.specs import PairwiseBarrier

RES = Path(__file__).resolve().parents[1] / 'results'
W0_MED = 17.38
NEW = {f'fair (a)+(b), W0 = {lab}, step {fx}': f'fair_eps0.1_W0{w0:g}_{fx}'
       for lab, w0 in (('1x', W0_MED), ('0.3x', 0.3 * W0_MED)) for fx in ('fixed', 'adaptive')}


def job(sc, var, seed):
    log = simulate(make_scenario(sc), SingleIntegrator(), PairwiseBarrier(), make_solver(NEW[var]), 120.0, 0.02, seed)
    return dict(scenario=sc, variant=var, seed=seed, weights=log.weights.tolist(), **Cost()(log), **Safety()(log),
                **PriceImbalance()(log), **FairOverTime()(log))


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
    jobs = [(sc, v, s) for sc in ('S1', 'S4') for v in NEW for s in range(6)]
    with ProcessPoolExecutor(args.workers) as ex:
        rows = list(ex.map(job, *zip(*jobs)))
    (RES / 'cost_memory2.jsonl').write_text('\n'.join(json.dumps(r) for r in rows) + '\n')
    old = [json.loads(l) for l in (RES / 'cost_memory.jsonl').read_text().splitlines()]
    g = defaultdict(list)
    for r in old + rows:
        g[(r['scenario'], r['variant'])].append(r)
    show = ['final (W0 = inf)', 'fair, W0 = 1x', 'fair, W0 = 0.3x'] + list(NEW)
    L = ['', '## Follow-up (a)+(b): constrained-step inference, clipped mu, scaled step', '',
         '(a) μ log-likelihood and the ŵ MAP use only steps where the contact is constrained (s_i < ε or s_k < ε, own and '
         'replicated slack); no sliding window; the posterior is frozen otherwise and reset at contact start. '
         '(b) μ clipped to [0, 4] on both sides; exchange and shadow step 1/(2 k_e (1 + 4)) ("fixed") or '
         '1/(2 k_e (1 + max(μ_i, μ̂_k))) ("adaptive"; the shadow for hypothesis μ uses max(μ, μ_i)). '
         'Same seeds; rows of the final configuration and of the first fair runs repeated for comparison.', '']
    for sc in ('S1', 'S4'):
        L += [f'### {sc}', '',
              '| variant | cost | W std/mean | W range | cost, w = 1 | cost, w = 3 | min dist. agents | viol. agents (%) | '
              'min dist. ext. | viol. ext. (%) | |r_ik+r_ki| p95 / max | imbalance (time-w.) |',
              '|---|---|---|---|---|---|---|---|---|---|---|---|']
        for v in show:
            rr = g[(sc, v)]
            L.append(f"| {v} | {ms([r['cost'] for r in rr])} | {ms([r['W_cv'] for r in rr])} | {ms([r['W_range'] for r in rr], nd=2)} | "
                     f"{ms([r['cost_w1'] for r in rr])} | {ms([r['cost_w3'] for r in rr])} | {min(r['min_dist_team'] for r in rr):.2f} | "
                     f"{ms([r['viol_team'] for r in rr], pct=True)} | {np.nanmin([r['min_dist_ext'] for r in rr]):.2f} | "
                     f"{ms([r['viol_ext'] for r in rr], pct=True)} | {np.median([r['gap_p95'] for r in rr]):.2g} / "
                     f"{max(r['gap_max'] for r in rr):.2g} | {ms([r.get('imbalance_time') for r in rr], nd=2)} |")
        L += ['', 'Inference on contacts that were ever constrained (state at the end of the contact; truth offline only):', '',
              '| variant | fraction of contacts ever constrained | n | mean true μ_k | mean μ̂ | abs error | corr(μ̂, μ) | '
              'ŵ fixed (fraction) | ŵ accuracy |', '|---|---|---|---|---|---|---|---|---|']
        for v in list(NEW):
            rr = g[(sc, v)]
            L.append(f"| {v} | {np.nanmean([r.get('frac_constrained', np.nan) for r in rr]):.2f} | "
                     f"{sum(r.get('n_contacts_c', 0) for r in rr)} | {np.nanmean([r.get('mu_true_mean_c', np.nan) for r in rr]):.2f} | "
                     f"{np.nanmean([r.get('mu_hat_mean_c', np.nan) for r in rr]):.2f} | {np.nanmean([r.get('mu_abs_err_c', np.nan) for r in rr]):.2f} | "
                     f"{np.nanmean([r.get('mu_corr_c', np.nan) for r in rr]):.2f} | {np.nanmean([r.get('w_fixed_frac_c', np.nan) for r in rr]):.2f} | "
                     f"{np.nanmean([r.get('w_acc_c', np.nan) for r in rr]):.2f} |")
        L.append('')
    with (RES / 'cost_memory.md').open('a') as f:
        f.write('\n'.join(L) + '\n')
    print('\n'.join(L))
