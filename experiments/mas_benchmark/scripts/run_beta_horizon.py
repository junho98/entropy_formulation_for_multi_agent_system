"""Horizon: does the spread of accumulated cost keep growing under the final configuration and level off under centred
beta? Final vs centred beta (W0 = 4.22, beta_max 8, c-bar as before), 600 s, S1 and S4, eps 0.1, 12 seeds (same for both).
Reports W std/mean, Jain and range (max - min W_i) at t = 20..120 s (every 20 s) and 120..600 s (every 120 s), plus cost,
team and external violation and the per-window cost rate (stationarity). Baselines Tan, PCCA, Oracle at 120 s (seeds 0-5).

    python scripts/run_beta_horizon.py [--workers 11]  -> appends "Horizon" to results/beta.md, results/beta_horizon.pdf
"""
import argparse
import json
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from mas_benchmark.analyzers import Cost, Safety
from mas_benchmark.core import simulate
from mas_benchmark.dynamics import SingleIntegrator
from mas_benchmark.scenarios import make_scenario
from mas_benchmark.solvers import make_solver
from mas_benchmark.specs import PairwiseBarrier

RES = Path(__file__).resolve().parents[1] / 'results'
WB = 16.88
CBAR = {'S1': 10.3774 / 120, 'S4': 29.3127 / 120}
CONF = {'final': lambda sc: 'ours_eps0.1_mutual',
        'centred 0.25x': lambda sc: f'beta_eps0.1_W0{0.25 * WB:g}_leakinf_bmax8_cbar{CBAR[sc]:.6g}'}
T_EARLY = (20, 40, 60, 80, 100, 120)
T_LATE = (120, 240, 360, 480, 600)


def stats(W):
    W = np.asarray(W, float)
    return dict(cv=float(W.std() / W.mean()), jain=float(W.sum() ** 2 / (len(W) * np.sum(W ** 2))), range=float(W.max() - W.min()))


def job(sc, conf, seed, horizon):
    solver = make_solver(CONF[conf](sc) if conf in CONF else conf)
    log = simulate(make_scenario(sc), SingleIntegrator(), PairwiseBarrier(), solver, horizon, 0.02, seed)
    f = 0.5 * log.weights[None] * np.sum((log.u - log.u_nom) ** 2, axis=2) * log.dt
    cum = np.cumsum(f, axis=0)
    ts = [t for t in sorted(set(T_EARLY) | set(T_LATE)) if t <= horizon]
    at = {str(t): stats(cum[int(round(t / log.dt)) - 1]) for t in ts}
    rate = [float(f[int(a / log.dt):int(b / log.dt)].sum() / (b - a) / f.shape[1])
            for a, b in zip([0] + list(T_LATE[:-1]), T_LATE) if b <= horizon]
    return dict(scenario=sc, conf=conf, seed=seed, horizon=horizon, at=at, rate=rate, **Cost()(log), **Safety()(log))


def ms(v, nd=3, pct=False):
    v = np.array([x for x in v if x is not None and np.isfinite(x)], float)
    if not len(v):
        return '–'
    m, s = v.mean(), v.std(ddof=1) / np.sqrt(len(v))
    return f'{100 * m:.2f} ± {100 * s:.2f}' if pct else f'{m:.{nd}f} ± {s:.{nd}f}'


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=11)
    args = ap.parse_args()
    jobs = [(sc, c, s, 600.0) for sc in ('S1', 'S4') for c in CONF for s in range(12)]
    jobs += [(sc, b, s, 120.0) for sc in ('S1', 'S4') for b in ('tan', 'pcca', 'oracle') for s in range(6)]
    with ProcessPoolExecutor(args.workers) as ex:
        rows = list(ex.map(job, *zip(*jobs)))
    (RES / 'beta_horizon.jsonl').write_text('\n'.join(json.dumps(r) for r in rows) + '\n')
    g = defaultdict(dict)
    for r in rows:
        g[(r['scenario'], r['conf'])][r['seed']] = r
    L = ['', '## Horizon', '',
         'Final configuration vs centred β (W0 = 4.22, β_max 8, c̄ S1 0.0865, S4 0.2443), 600 s, ε = 0.1, 12 seeds (0–11, same '
         'for both). W_i(t) = base cost ½ w_i‖u_i − u0_i‖² accumulated to t. Range = max_i W_i − min_i W_i. Mean ± s.e.; '
         'Δ = centred − final, paired by seed. The 20–120 s rows come from the first 120 s of the same 600 s runs (W_i(t) was '
         'not logged in the earlier 24-seed runs).', '']
    for sc in ('S1', 'S4'):
        F, C = g[(sc, 'final')], g[(sc, 'centred 0.25x')]
        seeds = sorted(set(F) & set(C))
        L += [f'### {sc}', '', '| t (s) | W std/mean: final | centred | Δ | Jain: final | centred | Δ | range: final | centred | Δ |',
              '|---|---|---|---|---|---|---|---|---|---|']
        for t in sorted(set(T_EARLY) | set(T_LATE)):
            k = str(t)
            line = [f'{t}']
            for q in ('cv', 'jain', 'range'):
                a = [F[s]['at'][k][q] for s in seeds]; b = [C[s]['at'][k][q] for s in seeds]
                nd = 2 if q == 'range' else 3
                line += [ms(a, nd), ms(b, nd), ms(np.array(b) - np.array(a), nd)]
            L.append('| ' + ' | '.join(line) + ' |')
        L += ['', '| 600 s run | cost | Δ cost | team viol. (%) | ext. viol. (%) | Δ ext. (pp) |', '|---|---|---|---|---|---|']
        for name, D in (('final', F), ('centred 0.25×', C)):
            L.append(f"| {name} | {ms([D[s]['cost'] for s in seeds])} | "
                     f"{ms([C[s]['cost'] - F[s]['cost'] for s in seeds]) if name != 'final' else '–'} | "
                     f"{ms([D[s]['viol_team'] for s in seeds], pct=True)} | "
                     f"{ms([D[s]['viol_ext'] for s in seeds], pct=True) if sc == 'S4' else '–'} | "
                     f"{ms([100 * (C[s]['viol_ext'] - F[s]['viol_ext']) for s in seeds], nd=2) if (sc == 'S4' and name != 'final') else '–'} |")
        rates = np.array([F[s]['rate'] for s in seeds])
        L += ['', f'Stationarity (final): fleet-mean cost rate per agent in the windows 0–120, …, 480–600 s: ' +
              ', '.join(f'{m:.3f} ± {s_:.3f}' for m, s_ in zip(rates.mean(0), rates.std(0, ddof=1) / np.sqrt(len(seeds)))) +
              ' (targets are redrawn on arrival and externals reflect at the arena boundary, so routes do not end).', '']
    L += ['### Baselines at 120 s (seeds 0–5)', '', '| scenario | method | W std/mean | Jain | range |', '|---|---|---|---|---|']
    for sc in ('S1', 'S4'):
        for c in ('final', 'tan', 'pcca', 'oracle'):
            D = g[(sc, c)]
            ss = [s for s in range(6) if s in D]
            L.append(f"| {sc} | {c} | {ms([D[s]['at']['120'][ 'cv'] for s in ss])} | {ms([D[s]['at']['120']['jain'] for s in ss])} | "
                     f"{ms([D[s]['at']['120']['range'] for s in ss], 2)} |")
    with (RES / 'beta.md').open('a') as fh:
        fh.write('\n'.join(L) + '\n')
    print('\n'.join(L))

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size': 8, 'pdf.fonttype': 42})
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.8))
    for ax, sc in zip(axes, ('S1', 'S4')):
        for c, col in (('final', 'tab:gray'), ('centred 0.25x', 'tab:blue')):
            D = g[(sc, c)]
            ts = sorted(set(T_EARLY) | set(T_LATE))
            vals = np.array([[D[s]['at'][str(t)]['range'] for t in ts] for s in sorted(D)])
            ax.errorbar(ts, vals.mean(0), yerr=vals.std(0, ddof=1) / np.sqrt(len(vals)), marker='o', ms=3, capsize=2, color=col,
                        label='final' if c == 'final' else r'centred $\beta$, $W_0=4.22$')
        ax.set_xlabel('t (s)'); ax.set_ylabel(r'range $\max_i W_i-\min_i W_i$'); ax.set_title(sc); ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(RES / 'beta_horizon.pdf')
