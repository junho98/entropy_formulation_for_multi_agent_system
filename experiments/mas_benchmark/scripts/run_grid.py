"""Sec. 12.1 protocol: scenarios x methods x seeds, 120 s each, in parallel. Rows are appended to results/grid.jsonl;
runs already present are skipped, so an interrupted grid resumes.

    python scripts/run_grid.py [--scenarios S1 S2 S3 S4] [--solvers ...] [--seeds 0 1 2 3 4 5] [--horizon 120] [--workers 8]
"""
import argparse
import json
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from mas_benchmark.analyzers import AgreementGap, Cost, Liveness, PriceImbalance, Safety
from mas_benchmark.core import simulate
from mas_benchmark.dynamics import SingleIntegrator
from mas_benchmark.scenarios import make_scenario
from mas_benchmark.solvers import make_solver
from mas_benchmark.specs import PairwiseBarrier

SOLVERS = (['oracle', 'tan', 'pcca', 'risk_ratio', 'reciprocal', 'ours_eps0.1', 'ours_eps0.2', 'ours_eps0.3']
           + [f'ours_eps{e}_w{w}' for e in (0.1, 0.2, 0.3) for w in (1, 0.99, 0.9)])    # following-prior sweep
OUT = Path(__file__).resolve().parents[1] / 'results' / 'grid.jsonl'


def run(scenario, solver, seed, horizon):
    t0 = time.time()
    log = simulate(make_scenario(scenario), SingleIntegrator(), PairwiseBarrier(), make_solver(solver),
                   horizon=horizon, dt=0.02, seed=seed)
    return dict(scenario=scenario, solver=solver, seed=seed, horizon=horizon, wall_s=round(time.time() - t0, 1),
                **Cost()(log), **Safety()(log), **AgreementGap()(log), **PriceImbalance()(log), **Liveness()(log))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--scenarios', nargs='+', default=['S1', 'S2', 'S3', 'S4'])
    ap.add_argument('--solvers', nargs='+', default=SOLVERS)
    ap.add_argument('--seeds', nargs='+', type=int, default=list(range(6)))
    ap.add_argument('--horizon', type=float, default=120.0)
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--out', default=str(OUT))
    args = ap.parse_args()
    OUT = Path(args.out)
    OUT.parent.mkdir(exist_ok=True)
    done = set()
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            r = json.loads(line)
            done.add((r['scenario'], r['solver'], r['seed'], r['horizon']))
    jobs = [(s, m, k, args.horizon) for s in args.scenarios for m in args.solvers for k in args.seeds
            if (s, m, k, args.horizon) not in done]
    print(f'{len(jobs)} runs ({len(done)} already in {OUT.name})', flush=True)
    with ProcessPoolExecutor(args.workers) as ex, OUT.open('a') as f:
        futs = {ex.submit(run, *j): j for j in jobs}
        for fut in as_completed(futs):
            row = fut.result()
            f.write(json.dumps(row) + '\n'); f.flush()
            print(json.dumps(row), flush=True)
