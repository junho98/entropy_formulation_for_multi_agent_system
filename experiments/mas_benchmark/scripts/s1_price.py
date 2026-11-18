"""S1 price analysis (grid settings unchanged): imbalance split by weights and by early / settled phase of each
isolated encounter, the first-activation imbalance against the |w_a - w_b|/(w_a + w_b) bound, an exchange-step
sensitivity for Ours, and per-encounter price traces.

    python scripts/s1_price.py [--seeds 0 1 2 3 4 5] [--horizon 120] [--workers 11]
-> results/s1_price.jsonl (per run), results/s1_price.md (table), results/figures/s1_prices_*.png
"""
import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from mas_benchmark.analyzers import PriceImbalance, encounters
from mas_benchmark.core import simulate
from mas_benchmark.dynamics import SingleIntegrator
from mas_benchmark.scenarios import make_scenario
from mas_benchmark.solvers import make_solver
from mas_benchmark.specs import PairwiseBarrier

RES = Path(__file__).resolve().parents[1] / 'results'
METHODS = ['ours_eps0.1', 'ours_eps0.2', 'ours_eps0.3', 'ours_eps0.1_newton', 'ours_eps0.2_newton', 'ours_eps0.3_newton',
           'ours_eps0.1_s0.5', 'pcca', 'oracle', 'tan', 'reciprocal', 'risk_ratio']
TRACED = ['ours_eps0.1', 'ours_eps0.1_newton', 'pcca', 'oracle']


def run(method, seed, horizon):
    log = simulate(make_scenario('S1'), SingleIntegrator(), PairwiseBarrier(), make_solver(method),
                   horizon=horizon, dt=0.02, seed=seed)
    w = log.weights
    encs = encounters(log)
    first = [abs(e['mu_i'][0] - e['mu_k'][0]) / (e['mu_i'][0] + e['mu_k'][0]) for e in encs if w[e['i']] != w[e['k']]]
    row = dict(method=method, seed=seed, **PriceImbalance()(log),
               first_step_diff_w=float(np.mean(first)) if first else np.nan)
    traces = [dict(seed=seed, wi=float(w[e['i']]), wk=float(w[e['k']]), mu_i=e['mu_i'].tolist(),
                   mu_k=e['mu_k'].tolist()) for e in encs] if method in TRACED or 'region' in method else []
    return row, traces


def plot(traces, dt, tag=''):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig_dir = RES / 'figures'
    fig_dir.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(len(traces), 3, figsize=(12, 3 * len(traces)), squeeze=False)
    for r, m in enumerate(traces):
        tr = traces[m]
        diff = sorted([e for e in tr if e['wi'] != e['wk']], key=lambda e: -len(e['mu_i']))[:2]
        same = sorted([e for e in tr if e['wi'] == e['wk']], key=lambda e: -len(e['mu_i']))[:1]
        for c, e in enumerate(diff + same):
            ax = axes[r, c]
            t = dt * np.arange(len(e['mu_i']))
            ax.plot(t, e['mu_i'], label=f"agent i (w={e['wi']:g})")
            ax.plot(t, e['mu_k'], label=f"agent k (w={e['wk']:g})")
            ax.axvline(0.2, color='grey', lw=0.8, ls=':')
            ax.set_title(f"{m}, seed {e['seed']}", fontsize=9)
            ax.set_xlabel('time since activation [s]')
            ax.set_ylabel('price')
            ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(fig_dir / f's1_prices_traces{tag}.png', dpi=150)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--seeds', nargs='+', type=int, default=list(range(6)))
    ap.add_argument('--horizon', type=float, default=120.0)
    ap.add_argument('--workers', type=int, default=11)
    ap.add_argument('--methods', nargs='+', default=METHODS)
    ap.add_argument('--tag', default='', help='suffix for the output files')
    args = ap.parse_args()
    METHODS = args.methods
    TRACED = [m for m in TRACED if m in METHODS] + [m for m in METHODS if 'region' in m]
    jobs = [(m, s, args.horizon) for m in METHODS for s in args.seeds]
    rows, traces = [], {m: [] for m in TRACED}
    tag = args.tag
    with ProcessPoolExecutor(args.workers) as ex:
        for (m, s, _), (row, tr) in zip(jobs, ex.map(run, *zip(*jobs))):
            rows.append(row)
            if m in TRACED:
                traces[m] += tr
            print(json.dumps(row), flush=True)
    (RES / f's1_price{tag}.jsonl').write_text('\n'.join(json.dumps(r) for r in rows) + '\n')
    (RES / f's1_traces{tag}.json').write_text(json.dumps(traces))
    keys = ['imbalance', 'imbalance_time', 'imbalance_early', 'imbalance_settled',
            'imbalance_same_w', 'imbalance_time_same_w', 'imbalance_settled_same_w',
            'imbalance_diff_w', 'imbalance_time_diff_w', 'imbalance_early_diff_w', 'imbalance_settled_diff_w',
            'first_step_diff_w', 'n_encounters', 'n_short']
    lines = ['# S1 price imbalance (mean (std) over seeds; grid settings unchanged)', '',
             'Lower bound at first activation for weights 1 vs 3: |w_a - w_b|/(w_a + w_b) = 0.5.', '',
             '| method | ' + ' | '.join(keys) + ' |', '|---|' + '---|' * len(keys)]
    for m in METHODS:
        sub = [r for r in rows if r['method'] == m]
        cells = []
        for k in keys:
            v = np.array([r[k] for r in sub], dtype=float)
            v = v[~np.isnan(v)]
            cells.append(f'{v.mean():.3f} ({v.std():.3f})' if len(v) else '–')
        lines.append(f'| {m} | ' + ' | '.join(cells) + ' |')
    (RES / f's1_price{tag}.md').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    plot(traces, 0.02, tag)
