"""Ablation (2026-11-15): exchange with transmissions (ThermoRho, lam*rho) vs the v42 exchange (rho = 1), Ours eps 0.1,
seed 0 (default), 120 s, on S1, S4 and the six grid2x3 (+ts1.5) cells. -> results/rho_ablation.jsonl

    python scripts/run_rho_ablation.py [--workers 11] [--seeds 0]
"""
import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_grid2x3_ts as G                                                # noqa: E402

OUT = Path(__file__).resolve().parents[1] / 'results' / 'rho_ablation.jsonl'

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=11)
    ap.add_argument('--seeds', type=int, nargs='+', default=[0])
    a = ap.parse_args()
    cells = ['S1', 'S4'] + G.CELLS
    jobs = [(conf, c, m, dict(G.OURS, eps=0.1), s, 120.0) for conf, m in (('ours_eps0.1', 'ours'), ('ours_rho_eps0.1', 'ours_rho'))
            for c in cells for s in a.seeds]
    have = {(r['conf'], r['cell'], r['seed']) for r in G.load(OUT)}
    jobs = [j for j in jobs if (j[0], j[1], j[4]) not in have]
    print(len(jobs), 'runs', flush=True)
    with ProcessPoolExecutor(a.workers) as ex, OUT.open('a') as fh:
        for n, f in enumerate(as_completed([ex.submit(G.run, *j) for j in jobs]), 1):
            fh.write(json.dumps(f.result()) + '\n'); fh.flush()
            print(f'{n}/{len(jobs)}', flush=True)
