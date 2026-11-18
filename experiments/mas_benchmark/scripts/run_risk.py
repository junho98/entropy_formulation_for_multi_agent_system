"""Risk allotment experiment (v41 Prop. 6.4): B (per neighbour), U (uniform), T (temperature), default step, mutual law.

    python scripts/run_risk.py [--workers 11]  -> results/risk_allotment.{jsonl,md}, results/figures/risk_*.png
"""
import argparse
import json
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from mas_benchmark.analyzers import AgreementGap, Cost, PriceImbalance, RiskAllotment, Safety
from mas_benchmark.core import simulate
from mas_benchmark.dynamics import SingleIntegrator
from mas_benchmark.scenarios import make_scenario
from mas_benchmark.solvers import make_solver
from mas_benchmark.specs import PairwiseBarrier

RES = Path(__file__).resolve().parents[1] / 'results'
VARIANTS = {'B': '', 'U': '_riskU', 'T': '_riskT'}


def job(sc, eps, var, seed):
    name = f'ours_eps{eps}_mutual{VARIANTS[var]}'
    log = simulate(make_scenario(sc), SingleIntegrator(), PairwiseBarrier(), make_solver(name), 120.0, 0.02, seed)
    ra = RiskAllotment()(log)
    series = ra.pop('T_series')
    return dict(scenario=sc, eps=eps, variant=var, solver=name, seed=seed, **Cost()(log), **Safety()(log),
                **AgreementGap()(log), **PriceImbalance()(log), **ra, T_series=series[::10])


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=11)
    ap.add_argument('--seeds', nargs='+', type=int, default=list(range(6)))
    args = ap.parse_args()
    jobs = [(sc, e, v, s) for sc in ('S1', 'S3', 'S4') for e in ('0.1', '0.3') for v in VARIANTS for s in args.seeds]
    with ProcessPoolExecutor(args.workers) as ex:
        rows = list(ex.map(job, *zip(*jobs)))
    (RES / 'risk_allotment.jsonl').write_text('\n'.join(json.dumps(r) for r in rows) + '\n')
    g = defaultdict(list)
    for r in rows:
        g[(r['scenario'], r['eps'], r['variant'])].append(r)
    keys = [('cost', '{:.3f}'), ('min_dist_team', 'min {:.2f}'), ('viol_team', '{:.2%}'), ('min_dist_ext', 'min {:.2f}'),
            ('viol_ext', '{:.2%}'), ('coverage', '{:.3f}'), ('union_delta', '{:.3f}'), ('T_mean', '{:.3g}'),
            ('T_median', '{:.3g}'), ('nu_cv', '{:.3f}'), ('gap_max', '{:.3f}'), ('imbalance_time', '{:.3f}'),
            ('imbalance_settled_diff_w', '{:.3f}'), ('stop_frac', '{:.2%}')]
    lines = ['# Risk allotment (v41 Prop. 6.4): per-agent budget delta_i = 0.05 per step', '',
             'B: delta_ik = 0.05 per neighbour (union risk K_i 0.05). U: delta_ik = delta_i / K_i. '
             'T: delta_ik proportional to lam_ik theta*_ik (previous step), floor 0.01 delta_i/K_i, EMA 0.8, renormalised. '
             'Default step, mutual exchange; 6 seeds x 120 s; mean over seeds, min distances = min over seeds.', '',
             '| scenario | eps | variant | ' + ' | '.join(k for k, _ in keys) + ' |', '|---|---|---|' + '---|' * len(keys)]
    for (sc, e, v), rr in sorted(g.items()):
        cells = []
        for k, fmt in keys:
            vals = np.array([r.get(k, np.nan) for r in rr], dtype=float)
            vals = vals[~np.isnan(vals)]
            if not len(vals):
                cells.append('–'); continue
            x = vals.min() if k.startswith('min_dist') else vals.max() if k == 'gap_max' else vals.mean()
            cells.append(fmt.format(x))
        lines.append(f'| {sc} | {e} | {v} | ' + ' | '.join(cells) + ' |')
    (RES / 'risk_allotment.md').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 3, figsize=(14, 7))
    for col, sc in enumerate(('S1', 'S3', 'S4')):
        ax = axes[0, col]
        for v in VARIANTS:
            rr = g[(sc, '0.1', v)]
            L = min(len(r['T_series']) for r in rr)
            m = np.nanmean([r['T_series'][:L] for r in rr], axis=0)
            ax.plot(np.arange(L) * 0.2, m, label=v, lw=0.8)
        ax.set_yscale('log'); ax.set_title(f'{sc}, eps 0.1: agent temperature T_i (mean over agents, seeds)')
        ax.set_xlabel('t [s]'); ax.legend(fontsize=8)
        ax = axes[1, col]
        for v in VARIANTS:
            vals = [x for r in g[(sc, '0.1', v)] for x in r['T_series'] if np.isfinite(x) and x > 0]
            if vals:
                ax.hist(np.log10(vals), bins=40, alpha=0.5, label=v, density=True)
        ax.set_xlabel('log10 T_i'); ax.set_title(f'{sc}, eps 0.1: distribution of T_i'); ax.legend(fontsize=8)
    fig.tight_layout()
    (RES / 'figures').mkdir(exist_ok=True)
    fig.savefig(RES / 'figures' / 'risk_temperature.png', dpi=150)
