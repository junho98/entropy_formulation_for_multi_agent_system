"""Per-step beta (2026-11-15, paper v42 Def. 6.5): beta_i = clip(exp((W_i - c-bar t)/W0), 1/8, 8) at every step, no
per-contact freezing (ThermoBeta(per_step=True)). Reruns only the beta rows, under new conf names (old rows kept):

  paper  S1/S4, W0 4.22, beta_max 8, c-bar 0.0865/0.2443: 24 seeds x 120 s and 12 seeds x 600 s
         -> results/beta_step.jsonl (Table fair, Fig. fair; reference 'final' rows in beta*.jsonl, beta_horizon.jsonl)
  grid   grid2x3 (+ts1.5): beta_step_W04.22, beta_step_W02.1 (eps 0.1), beta_step_W04.22_eps0.2 (24 seeds x 120 s),
         beta_step_W04.22 600 s (12 seeds) -> results/grid2x3/runs.jsonl, horizon.jsonl (same c-bar files as before)
  h02    grid2x3 600 s at eps 0.2 (12 seeds): beta_step_W04.22_eps0.2 and ours_eps0.2 (no beta) -> horizon.jsonl

    python scripts/run_beta_step.py [--workers 11] [--phase paper|grid|all]
"""
import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_grid2x3_ts as G                                                # noqa: E402
from mas_benchmark.analyzers import Cost, FairOverTime, PriceImbalance, Safety   # noqa: E402
from mas_benchmark.core import simulate                                   # noqa: E402
from mas_benchmark.dynamics import SingleIntegrator                       # noqa: E402
from mas_benchmark.scenarios import make_scenario                         # noqa: E402
from mas_benchmark.solvers import make_solver                             # noqa: E402
from mas_benchmark.specs import PairwiseBarrier                           # noqa: E402

RES = Path(__file__).resolve().parents[1] / 'results'
OUT = RES / 'beta_step.jsonl'
CBAR = {'S1': 10.3774 / 120, 'S4': 29.3127 / 120}
T_AT = (20, 40, 60, 80, 100, 120, 240, 360, 480, 600)


def name(sc):
    return f'beta_eps0.1_W04.22_leakinf_bmax8_cbar{CBAR[sc]:.6g}_step'


def job(sc, seed, horizon):
    log = simulate(make_scenario(sc), SingleIntegrator(), PairwiseBarrier(), make_solver(name(sc)), horizon, 0.02, seed)
    f = 0.5 * log.weights[None] * np.sum((log.u - log.u_nom) ** 2, axis=2) * log.dt
    cum = np.cumsum(f, axis=0)
    out = dict(scenario=sc, conf='step', seed=seed, horizon=horizon, W=[float(w) for w in cum[-1]],
               at={str(t): G.wstats(cum[int(round(t / log.dt)) - 1]) for t in T_AT if t <= horizon},
               **Cost()(log), **Safety()(log))
    if horizon <= 120:
        out.update(**PriceImbalance()(log), **FairOverTime()(log))
    out.pop('viol_events', None)
    return out


def paper(workers):
    have = {(r['scenario'], r['seed'], r['horizon']) for r in G.load(OUT)}
    jobs = [(sc, s, 120.0) for sc in ('S1', 'S4') for s in range(24)] + [(sc, s, 600.0) for sc in ('S1', 'S4') for s in range(12)]
    jobs = [j for j in jobs if j not in have]
    print(f'{len(jobs)} runs -> {OUT.name}', flush=True)
    with ProcessPoolExecutor(workers) as ex, OUT.open('a') as fh:
        futs = [ex.submit(job, *j) for j in sorted(jobs, key=lambda j: -j[2])]
        for n, fut in enumerate(as_completed(futs), 1):
            fh.write(json.dumps(fut.result()) + '\n'); fh.flush()
            if n % 10 == 0 or n == len(futs):
                print(f'{n}/{len(futs)} done', flush=True)


def grid(workers):
    cb = json.loads((G.OUT / 'cbar.json').read_text())
    cb2 = json.loads((G.OUT / 'cbar_eps0.2.json').read_text())
    P = lambda **k: dict(G.OURS, per_step=True, **k)
    jobs = [(f'beta_step_W0{w:g}', c, 'beta', P(eps=0.1, W0=w, cbar=cb[c]), s, 120.0) for w in G.W0S
            for c in G.CELLS for s in G.SEEDS]
    jobs += [('beta_step_W04.22_eps0.2', c, 'beta', P(eps=0.2, W0=4.22, cbar=cb2[c]), s, 120.0)
             for c in G.CELLS for s in G.SEEDS]
    G.execute(G.RUNS, jobs, workers)
    G.execute(G.HZ, [('beta_step_W04.22', c, 'beta', P(eps=0.1, W0=4.22, cbar=cb[c]), s, 600.0)
                     for c in G.CELLS for s in G.SEEDS_H], workers)


def h02(workers):
    cb2 = json.loads((G.OUT / 'cbar_eps0.2.json').read_text())
    jobs = [('beta_step_W04.22_eps0.2', c, 'beta', dict(G.OURS, per_step=True, eps=0.2, W0=4.22, cbar=cb2[c]), s, 600.0)
            for c in G.CELLS for s in G.SEEDS_H]
    jobs += [('ours_eps0.2', c, 'ours', dict(G.OURS, eps=0.2), s, 600.0) for c in G.CELLS for s in G.SEEDS_H]
    G.execute(G.HZ, jobs, workers)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=11)
    ap.add_argument('--phase', default='all', choices=('paper', 'grid', 'h02', 'all'))
    ap.add_argument('--seeds', type=int, nargs='+', default=None, help='grid/h02: restrict to these seeds')
    a = ap.parse_args()
    if a.seeds is not None:
        G.SEEDS = [s for s in G.SEEDS if s in a.seeds]
        G.SEEDS_H = [s for s in G.SEEDS_H if s in a.seeds]
    if a.phase in ('paper', 'all'):
        paper(a.workers)
    if a.phase in ('grid', 'all'):
        grid(a.workers)
    if a.phase in ('h02', 'all'):
        h02(a.workers)
