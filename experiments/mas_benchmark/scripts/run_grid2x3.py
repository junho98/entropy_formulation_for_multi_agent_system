"""2x3 grid (team HOM/HET x outsiders E0/E4/E8): main table at 24 seeds x 120 s, then 600 s horizon at 12 seeds.

Methods: Oracle, Tan, PCCA, Risk ratio, Reciprocal; Ours final (pairwise, mutual, default step, delta 0.05, prior 0.97) at
eps 0.1, 0.2, 0.3; Ours + centred beta (W0 4.22, beta_max 8) at eps 0.1 with c-bar per cell by the public rule: the
fleet-mean work rate of the final eps-0.1 run of that cell (mean of cost = mean_i W_i(120)/120 over the 24 seeds).
Rows go to results/grid2x3/grid.jsonl (120 s) and results/grid2x3/horizon.jsonl (600 s); runs already present are
skipped, so an interrupted grid resumes. c-bar values: results/grid2x3/cbar.json.

    python scripts/run_grid2x3.py [--workers 11] [--phase grid|horizon|both]
"""
import argparse
import json
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from pathlib import Path

import numpy as np

from mas_benchmark.analyzers import AgreementGap, Cost, Liveness, PriceImbalance, Safety
from mas_benchmark.core import simulate
from mas_benchmark.dynamics import SingleIntegrator
from mas_benchmark.scenarios import GRID2X3, make_scenario
from mas_benchmark.solvers import make_solver
from mas_benchmark.specs import PairwiseBarrier

OUT = Path(__file__).resolve().parents[1] / 'results' / 'grid2x3'
WB = 16.88
FINAL = 'ours_eps0.1_mutual'
FIRST = [FINAL]
REST = ['oracle', 'tan', 'pcca', 'risk_ratio', 'reciprocal', 'ours_eps0.2_mutual', 'ours_eps0.3_mutual']
SEEDS, SEEDS_H = list(range(24)), list(range(12))
T_AT = (20, 40, 60, 80, 100, 120, 240, 360, 480, 600)


def beta_name(cbar):
    return f'beta_eps0.1_W0{0.25 * WB:g}_leakinf_bmax8_cbar{cbar:.6g}'


def wstats(W):
    W = np.asarray(W, float)
    return dict(W_cv=float(W.std() / W.mean()), jain=float(W.sum() ** 2 / (len(W) * np.sum(W ** 2))),
                W_range=float(W.max() - W.min()))


def run(scenario, solver, seed, horizon, conf):
    t0 = time.time()
    log = simulate(make_scenario(scenario), SingleIntegrator(), PairwiseBarrier(), make_solver(solver),
                   horizon=horizon, dt=0.02, seed=seed)
    f = 0.5 * log.weights[None] * np.sum((log.u - log.u_nom) ** 2, axis=2) * log.dt
    cum = np.cumsum(f, axis=0)
    row = dict(scenario=scenario, conf=conf, solver=solver, seed=seed, horizon=horizon, wall_s=round(time.time() - t0, 1),
               W=[float(w) for w in cum[-1]], **wstats(cum[-1]), **Cost()(log), **Safety()(log))
    if horizon > 120:
        row['at'] = {str(t): wstats(cum[int(round(t / log.dt)) - 1]) for t in T_AT if t <= horizon}
    else:
        row.update(**AgreementGap()(log), **PriceImbalance()(log), **Liveness()(log))
    return row


def done_keys(path):
    if not path.exists():
        return set()
    return {(r['scenario'], r['conf'], r['seed']) for r in map(json.loads, path.read_text().splitlines())}


def rows(path):
    return [json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []


def cbar_of(grid_rows, sc):
    v = [r['cost'] for r in grid_rows if r['scenario'] == sc and r['conf'] == 'final' and r['seed'] in SEEDS]
    return float(np.mean(v)) if len(v) == len(SEEDS) else None


def pool(ex, path, jobs, feed=None):
    """Run jobs (args tuples for run), append rows to path; feed(row) may return more jobs to submit."""
    done = done_keys(path)
    pend = {ex.submit(run, *j) for j in jobs if (j[0], j[4], j[2]) not in done}
    print(f'{len(pend)} runs -> {path.name}', flush=True)
    with path.open('a') as fh:
        while pend:
            fin, pend = wait(pend, return_when=FIRST_COMPLETED)
            for fut in fin:
                r = fut.result()
                fh.write(json.dumps(r) + '\n'); fh.flush()
                print(f"{r['scenario']} {r['conf']} seed {r['seed']} {r['wall_s']} s", flush=True)
                for j in (feed(r) if feed else []):
                    if (j[0], j[4], j[2]) not in done:
                        pend.add(ex.submit(run, *j))


def grid(ex):
    path = OUT / 'grid.jsonl'
    cb = {}

    def beta_jobs(sc):
        c = cbar_of(rows(path), sc)
        if c is None or sc in cb:
            return []
        cb[sc] = c
        (OUT / 'cbar.json').write_text(json.dumps(cb, indent=1))
        print(f'c-bar {sc} = {c:.4f}', flush=True)
        return [(sc, beta_name(c), s, 120.0, 'centred') for s in SEEDS]

    jobs = [(sc, FINAL, s, 120.0, 'final') for sc in GRID2X3 for s in SEEDS]
    jobs += [(sc, m, s, 120.0, m) for sc in GRID2X3 for m in REST for s in SEEDS]
    for sc in GRID2X3:                       # resume: cells whose final runs are already complete
        jobs += beta_jobs(sc)
    pool(ex, path, jobs, feed=lambda r: beta_jobs(r['scenario']) if r['conf'] == 'final' else [])


def horizon(ex):
    cb = json.loads((OUT / 'cbar.json').read_text())
    jobs = [(sc, FINAL, s, 600.0, 'final') for sc in GRID2X3 for s in SEEDS_H]
    jobs += [(sc, beta_name(cb[sc]), s, 600.0, 'centred') for sc in GRID2X3 for s in SEEDS_H]
    pool(ex, OUT / 'horizon.jsonl', jobs)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=11)
    ap.add_argument('--phase', choices=('grid', 'horizon', 'both'), default='both')
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(a.workers) as ex:
        if a.phase in ('grid', 'both'):
            grid(ex)
            print('GRID DONE', flush=True)
        if a.phase in ('horizon', 'both'):
            horizon(ex)
            print('HORIZON DONE', flush=True)
