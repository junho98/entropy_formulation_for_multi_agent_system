"""Short closed-loop run of every scenario with each implemented solver.

    python scripts/smoke.py [--horizon 10] [--seed 0]
"""
import argparse
import json
import time
from pathlib import Path

from mas_benchmark.analyzers import AgreementGap, Cost, PriceImbalance, Safety
from mas_benchmark.core import simulate
from mas_benchmark.dynamics import SingleIntegrator
from mas_benchmark.scenarios import PRESETS, make_scenario
from mas_benchmark.solvers import make_solver
from mas_benchmark.specs import PairwiseBarrier

ap = argparse.ArgumentParser()
ap.add_argument('--horizon', type=float, default=10.0)
ap.add_argument('--seed', type=int, default=0)
args = ap.parse_args()

rows = []
for name in PRESETS:
    for solver in map(make_solver, ['oracle', 'tan', 'pcca', 'risk_ratio', 'reciprocal', 'ours_eps0.1', 'ours_eps0.3']):
        t0 = time.time()
        log = simulate(make_scenario(name), SingleIntegrator(), PairwiseBarrier(), solver,
                       horizon=args.horizon, dt=0.02, seed=args.seed)
        row = dict(scenario=name, solver=solver.name, seed=args.seed, horizon=args.horizon,
                   wall_s=round(time.time() - t0, 1), **Cost()(log), **Safety()(log), **AgreementGap()(log), **PriceImbalance()(log))
        rows.append(row)
        print(json.dumps(row))

out = Path(__file__).resolve().parents[1] / 'results' / 'smoke.json'
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(rows, indent=1))
