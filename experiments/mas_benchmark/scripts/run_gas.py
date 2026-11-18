"""Gas specification (one shared constraint, scalar costate per agent) vs the pairwise default + mutual law.

    python scripts/run_gas.py [--workers 11]  -> results/gas.{jsonl,md}, results/figures/gas_*.png
"""
import argparse
import json
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from mas_benchmark.analyzers import AgreementGap, Cost, GroupSpread, Liveness, PriceImbalance, Safety, agent_prices
from mas_benchmark.core import simulate
from mas_benchmark.dynamics import SingleIntegrator
from mas_benchmark.scenarios import make_scenario
from mas_benchmark.solvers import make_solver
from mas_benchmark.specs import GasBarrier, PairwiseBarrier

RES = Path(__file__).resolve().parents[1] / 'results'
GAS = {'gas (spec)': 'gas_eps{e}', 'gas, pair replica': 'gas_eps{e}_reppair',
       'gas, pair replica, pair coverage': 'gas_eps{e}_pair_reppair'}


def job(sc, e, variant, tau, seed):
    if variant == 'pairwise':
        spec, name = PairwiseBarrier(), f'ours_eps{e}_mutual'
    else:
        spec, name = GasBarrier(tau=tau), GAS[variant].format(e=e)
    log = simulate(make_scenario(sc), SingleIntegrator(), spec, make_solver(name), 120.0, 0.02, seed)
    row = dict(scenario=sc, eps=e, variant=variant, tau=tau, seed=seed, solver=name, **Cost()(log), **Safety()(log),
               **AgreementGap()(log), **PriceImbalance()(log), **Liveness()(log), **GroupSpread()(log))
    if seed == 0 and sc == 'S4' and e == '0.1':
        N = log.x.shape[1]
        row['snap'] = [dict(t=t * 0.02, x=log.x[t].tolist(), ext=log.ext_x[t].tolist(),
                            lam=agent_prices(log.info[t], N).tolist()) for t in (1500, 3000, 4500)]
    return row


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=11)
    ap.add_argument('--seeds', nargs='+', type=int, default=list(range(6)))
    args = ap.parse_args()
    jobs = [(sc, e, v, tau, s) for sc in ('S1', 'S4') for e in ('0.1', '0.3') for v in GAS for tau in (0.05, 0.1)
            for s in args.seeds]
    jobs += [(sc, e, 'pairwise', None, s) for sc in ('S1', 'S4') for e in ('0.1', '0.3') for s in args.seeds]
    with ProcessPoolExecutor(args.workers) as ex:
        rows = list(ex.map(job, *zip(*jobs)))
    (RES / 'gas.jsonl').write_text('\n'.join(json.dumps({k: v for k, v in r.items() if k != 'snap'}) for r in rows) + '\n')
    g = defaultdict(list)
    for r in rows:
        g[(r['scenario'], r['eps'], r['variant'], r['tau'])].append(r)
    keys = [('cost', '{:.3f}'), ('min_dist_team', '{:.2f}'), ('viol_team', '{:.2%}'), ('min_dist_ext', '{:.2f}'),
            ('viol_ext', '{:.2%}'), ('group_cv_median', '{:.3f}'), ('price_on_frac', '{:.2f}'), ('gap_max', '{:.3g}'),
            ('imbalance_time', '{:.3f}'), ('stop_frac', '{:.2%}')]
    lines = ['# Gas specification vs pairwise (Ours, default step, mutual law, B risk allotment)', '',
             '6 seeds x 120 s. Mean over seeds; min distances = min over seeds; gap_max = max over seeds. '
             'group_cv_median: median CV of the scalar prices across connected groups (contact graph, d < r_c = 3); '
             'for the pairwise solver the agent price is the mean of its active pair prices.', '',
             '| scenario | eps | variant | tau | ' + ' | '.join(k for k, _ in keys) + ' |', '|---|---|---|---|' + '---|' * len(keys)]
    for (sc, e, v, tau), rr in sorted(g.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2], kv[0][3] or 0)):
        cells = []
        for k, fmt in keys:
            vals = np.array([r.get(k, np.nan) for r in rr], dtype=float); vals = vals[~np.isnan(vals)]
            if not len(vals):
                cells.append('–'); continue
            x = vals.min() if k.startswith('min_dist') else vals.max() if k == 'gap_max' else vals.mean()
            cells.append(fmt.format(x))
        lines.append(f'| {sc} | {e} | {v} | {tau if tau else "–"} | ' + ' | '.join(cells) + ' |')
    (RES / 'gas.md').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    snaps = [r for r in rows if 'snap' in r and (r['variant'] == 'pairwise' or r['tau'] == 0.1)]
    fig, axes = plt.subplots(len(snaps), 3, figsize=(12, 3.6 * len(snaps)), squeeze=False)
    for a, r in enumerate(snaps):
        for b, sn in enumerate(r['snap']):
            ax = axes[a, b]
            X, E, L = np.array(sn['x']), np.array(sn['ext']), np.array(sn['lam'])
            sc_ = ax.scatter(X[:, 0], X[:, 1], c=L, cmap='viridis', s=80, vmin=0, vmax=max(L.max(), 1e-6))
            ax.scatter(E[:, 0], E[:, 1], marker='x', c='r', s=40)
            for i, (x, y) in enumerate(X):
                ax.annotate(f'{L[i]:.2g}', (x, y), fontsize=6, xytext=(4, 4), textcoords='offset points')
            ax.set_xlim(-7.5, 7.5); ax.set_ylim(-7.5, 7.5); ax.set_aspect('equal')
            ax.set_title(f"{r['variant']}{'' if r['variant'] == 'pairwise' else ', tau 0.1'}, t = {sn['t']:.0f} s", fontsize=8)
            plt.colorbar(sc_, ax=ax, fraction=0.046)
    fig.tight_layout()
    (RES / 'figures').mkdir(exist_ok=True)
    fig.savefig(RES / 'figures' / 'gas_price_map.png', dpi=130)
