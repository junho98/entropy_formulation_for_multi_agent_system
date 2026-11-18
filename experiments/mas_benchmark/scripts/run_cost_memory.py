"""Fairness over time (own cost memory) vs the final configuration. S1 and S4, eps 0.1, 6 seeds x 120 s.

    python scripts/run_cost_memory.py [--workers 11]  -> results/cost_memory.{jsonl,md}, results/figures/cost_memory_*.pdf
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
W0_MED = 17.38            # median per-agent accumulated cost, final configuration, S1 seed 0, 120 s
VARIANTS = {'final (W0 = inf)': 'ours_eps0.1_mutual', 'fair, W0 = inf (inference only)': 'fair_eps0.1_W0inf',
            'fair, W0 = 1x': f'fair_eps0.1_W0{W0_MED:g}', 'fair, W0 = 0.3x': f'fair_eps0.1_W0{0.3 * W0_MED:g}'}


def job(sc, var, seed):
    log = simulate(make_scenario(sc), SingleIntegrator(), PairwiseBarrier(), make_solver(VARIANTS[var]), 120.0, 0.02, seed)
    return dict(scenario=sc, variant=var, seed=seed, weights=log.weights.tolist(), **Cost()(log), **Safety()(log),
                **PriceImbalance()(log), **FairOverTime()(log))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=11)
    ap.add_argument('--seeds', nargs='+', type=int, default=list(range(6)))
    args = ap.parse_args()
    jobs = [(sc, v, s) for sc in ('S1', 'S4') for v in VARIANTS for s in args.seeds]
    with ProcessPoolExecutor(args.workers) as ex:
        rows = list(ex.map(job, *zip(*jobs)))
    (RES / 'cost_memory.jsonl').write_text('\n'.join(json.dumps(r) for r in rows) + '\n')
    g = defaultdict(list)
    for r in rows:
        g[(r['scenario'], r['variant'])].append(r)

    def ms(v, pct=False, nd=3):
        v = np.array([x for x in v if x is not None and np.isfinite(x)], float)
        if not len(v):
            return '–'
        m, s = v.mean(), (v.std(ddof=1) / np.sqrt(len(v)) if len(v) > 1 else 0.0)
        return f'{100 * m:.2f} ± {100 * s:.2f}' if pct else f'{m:.{nd}f} ± {s:.{nd}f}'
    L = ['# Fairness over time: own cost memory in the exchange', '',
         f'Final configuration (pairwise, mutual trust, step 1/(2 k_e), delta = 0.05 per neighbour) vs the cost-memory '
         f'variant (solvers/thermo/fair.py). W0 sweep: inf, 1x and 0.3x the median per-agent accumulated cost of one '
         f'120 s S1 run of the final configuration ({W0_MED:.2f}). eps = 0.1, 6 seeds x 120 s, same seeds; mean ± s.e.', '']
    for sc in ('S1', 'S4'):
        L += [f'## {sc}', '',
              '| variant | cost | W range (max−min) | W std/mean | cost, w = 1 | cost, w = 3 | min dist. agents | '
              'viol. agents (%) | min dist. ext. | viol. ext. (%) | |r_ik+r_ki| median / p95 / max | imbalance (time-w.) |',
              '|---|---|---|---|---|---|---|---|---|---|---|---|']
        for v in VARIANTS:
            rr = g[(sc, v)]
            L.append(f"| {v} | {ms([r['cost'] for r in rr])} | {ms([r['W_range'] for r in rr], nd=2)} | "
                     f"{ms([r['W_cv'] for r in rr])} | {ms([r['cost_w1'] for r in rr])} | {ms([r['cost_w3'] for r in rr])} | "
                     f"{min(r['min_dist_team'] for r in rr):.2f} | {ms([r['viol_team'] for r in rr], pct=True)} | "
                     f"{np.nanmin([r['min_dist_ext'] for r in rr]):.2f} | {ms([r['viol_ext'] for r in rr], pct=True)} | "
                     f"{np.median([r['gap_med'] for r in rr]):.2g} / {np.median([r['gap_p95'] for r in rr]):.2g} / "
                     f"{max(r['gap_max'] for r in rr):.2g} | {ms([r.get('imbalance_time') for r in rr], nd=2)} |")
        L += ['', 'Inference accuracy (fair variants; truth from the offline log only). "End": last step of the contact. '
              '"Active": last step with the pair price active (the 50-step window has forgotten the informative steps by '
              'the end of the contact).', '',
              '| variant | contacts | mean true mu_k | mean mu_hat (end) | abs error (end) | w_hat acc. (end) | '
              'mean mu_hat (active) | abs error (active) | corr(mu_hat, mu) (active) | w_hat acc. (active) |',
              '|---|---|---|---|---|---|---|---|---|---|']
        for v in VARIANTS:
            rr = [r for r in g[(sc, v)] if 'mu_abs_err' in r]
            if rr:
                L.append(f"| {v} | {sum(r['n_contacts'] for r in rr)} | {np.mean([r['mu_true_mean'] for r in rr]):.2f} | "
                         f"{np.mean([r['mu_hat_mean'] for r in rr]):.2f} | {np.mean([r['mu_abs_err'] for r in rr]):.2f} | "
                         f"{np.nanmean([r['w_acc'] for r in rr]):.2f} | {np.nanmean([r.get('mu_hat_mean_act', np.nan) for r in rr]):.2f} | "
                         f"{np.nanmean([r.get('mu_abs_err_act', np.nan) for r in rr]):.2f} | {np.nanmean([r.get('mu_corr_act', np.nan) for r in rr]):.2f} | "
                         f"{np.nanmean([r.get('w_acc_act', np.nan) for r in rr]):.2f} |")
        L.append('')
    (RES / 'cost_memory.md').write_text('\n'.join(L) + '\n')
    print('\n'.join(L))

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size': 8, 'pdf.fonttype': 42})
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0))
    for ax, sc in zip(axes, ('S1', 'S4')):
        data = [np.concatenate([r['W'] for r in g[(sc, v)]]) for v in VARIANTS]
        ax.boxplot(data, tick_labels=[v.replace(' (', '\n(').replace(', ', '\n') for v in VARIANTS], showfliers=True)
        ax.set_ylabel('accumulated cost W_i (per agent, 120 s)')
        ax.set_title(f'{sc}: spread of W across agents')
        ax.tick_params(axis='x', labelsize=6)
    fig.tight_layout()
    (RES / 'figures').mkdir(exist_ok=True)
    fig.savefig(RES / 'figures' / 'cost_memory_W.pdf')
