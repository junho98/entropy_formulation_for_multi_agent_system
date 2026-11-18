"""Controlled fairness-exposure experiment (see scenarios/hypothesis.py, analyzers/bh_controlled.py).

    python scripts/run_bh_controlled.py [--seeds 200] [--workers 11]
-> results/bh_controlled_runs.jsonl, results/bh_controlled.md, results/figures/bh_controlled_{bound,frontier}.png
"""
import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from mas_benchmark.analyzers.bh_controlled import NS, reduce_run, summarize
from mas_benchmark.scenarios.hypothesis import GEOMETRIES, frozen_equilibrium, run
from mas_benchmark.solvers import make_solver

RES = Path(__file__).resolve().parents[1] / 'results'
RULES = {'default': 'ours_eps0.1_mutual', 'default x3': 'ours_eps0.1_mutual_s3', 'default x10': 'ours_eps0.1_mutual_s10',
         'iso': 'ours_eps0.1_mutual_region_iso', 'region': 'ours_eps0.1_mutual_region'}
SIGMAS = (0.02, 0.05, 0.1, 0.2)


def job(rule, geo, sig, hyp, seed):
    return dict(rule=rule, geometry=geo, sigma=sig, hyp=hyp, seed=seed,
                run=reduce_run(run(make_solver(RULES[rule]), hyp, geo, sig, seed)))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--seeds', type=int, default=200)
    ap.add_argument('--workers', type=int, default=11)
    args = ap.parse_args()
    deltas = {(r, g): frozen_equilibrium(make_solver(RULES[r]), g) for r in RULES for g in GEOMETRIES}
    jobs = [(r, g, s, h, k) for r in RULES for g in GEOMETRIES for s in SIGMAS for h in ('F', 'out') for k in range(args.seeds)]
    with ProcessPoolExecutor(args.workers) as ex:
        recs = list(ex.map(job, *zip(*jobs), chunksize=20))
    (RES / 'bh_controlled_runs.jsonl').write_text('\n'.join(json.dumps(r) for r in recs) + '\n')
    rows = summarize(recs, deltas)
    (RES / 'bh_controlled_rows.json').write_text(json.dumps(rows))

    below = [r for r in rows if r['sum'] < r['bound'] - 1e-12]
    lines = ['# Controlled fairness-exposure check: P_F(A_n^c) + P_out(A_n) >= 1/2 exp(-KL_n)', '',
             f'{args.seeds} seeds per cell; rules {", ".join(f"{k} = {v}" for k, v in RULES.items())}; '
             f'sigma_v in {SIGMAS}; geometries {list(GEOMETRIES)}; A_n = {{r_ik(n) >= m}}.', '',
             'Delta* (frozen two-agent equilibrium of r_ik, H_F):', '',
             '| rule | ' + ' | '.join(GEOMETRIES) + ' |', '|---|' + '---|' * len(GEOMETRIES)]
    for r in RULES:
        lines.append(f'| {r} | ' + ' | '.join(f'{deltas[(r, g)]:.3f}' for g in GEOMETRIES) + ' |')
    lines += ['', f'Points below the curve: {len(below)} of {len(rows)}.', '']
    # compact table: n = 25 and 50, all m, per rule / geometry / sigma
    lines += ['## P_F(A^c), P_out(A), KL_n and the bound (n = 10 and 50)', '',
              '| rule | geometry | sigma | n | m | m value | P_F(A^c) | P_out(A) | sum | KL_n | ½e^{-KL} | gap |',
              '|---|---|---|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        if r['n'] in (10, 50):
            lines.append(f"| {r['rule']} | {r['geometry']} | {r['sigma']} | {r['n']} | {r['m_name']} | {r['m']:.3f} | "
                         f"{r['P_F_fail']:.3f} | {r['P_out_A']:.3f} | {r['sum']:.3f} | {r['KL']:.3g} | {r['bound']:.3g} | {r['gap']:.3f} |")
    # tightness summary
    lines += ['', '## Tightness: smallest gap (sum − bound) per rule', '', '| rule | min gap | at (geometry, sigma, n, m) | KL there |',
              '|---|---|---|---|']
    for rule in RULES:
        rr = [r for r in rows if r['rule'] == rule]
        if rr:
            b = min(rr, key=lambda r: r['gap'])
            lines.append(f"| {rule} | {b['gap']:.3f} | {b['geometry']}, {b['sigma']}, {b['n']}, {b['m_name']} | {b['KL']:.3g} |")
    nact = {}
    for rec in recs:
        key = (rec['rule'], rec['hyp'])
        nact.setdefault(key, [0, 0])
        nact[key][0] += rec['run'] is not None
        nact[key][1] += 1
    lines += ['', 'Activated runs: ' + '; '.join(f'{k[0]}/{k[1]}: {v[0]}/{v[1]}' for k, v in nact.items())]
    (RES / 'bh_controlled.md').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines[:40]))

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6, 4.2))
    xs = np.logspace(-3, np.log10(max(r['KL'] for r in rows) + 1), 300)
    ax.plot(xs, 0.5 * np.exp(-xs), 'k--', label=r'$\frac{1}{2}e^{-x}$')
    for i, rule in enumerate(RULES):
        rr = [r for r in rows if r['rule'] == rule]
        ax.scatter([r['KL'] for r in rr], [r['sum'] for r in rr], s=6, alpha=0.5, label=rule)
    ax.set_xscale('symlog', linthresh=1e-2)
    ax.set_xlabel(r'$KL_n$ (chain rule, true noise model)')
    ax.set_ylabel(r'$P_F(A_n^c)+P_{out}(A_n)$')
    ax.legend(fontsize=7, markerscale=2)
    fig.tight_layout()
    (RES / 'figures').mkdir(exist_ok=True)
    fig.savefig(RES / 'figures' / 'bh_controlled_bound.png', dpi=150)

    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    for ax, geo in zip(axes, GEOMETRIES):
        for rule in RULES:
            rr = [r for r in rows if r['rule'] == rule and r['geometry'] == geo and r['n'] == 50]
            ax.scatter([r['P_F_fail'] for r in rr], [r['P_out_A'] for r in rr], s=12, label=rule)
        t = np.linspace(0, 1, 50)
        ax.plot(t, 1 - t, 'k:', lw=0.8)
        ax.set_xlabel(r'$P_F(A^c)$ (fairness failure)')
        ax.set_ylabel(r'$P_{out}(A)$ (exposure)')
        ax.set_title(f'{geo}, n = 50 (all sigma, all m)')
        ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(RES / 'figures' / 'bh_controlled_frontier.png', dpi=150)
