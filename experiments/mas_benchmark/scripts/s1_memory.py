"""S1 side experiment: agreement memory across exits (re-identification by observation) vs forgetting.

Variants (Ours, eps = 0.1, default step): forget (default), mem (keep r forever), mem10 (keep r, forget after 10 s
unseen). Horizons 120 s and 600 s. Reports imbalance, safety, and imbalance against the encounter index of the same
pair (1st, 2nd, 3rd, 4th+ isolated encounter).

    python scripts/s1_memory.py [--seeds 0 1 2 3 4 5] [--horizons 120 600] [--workers 4]
-> results/s1_memory.jsonl, results/s1_memory.md
"""
import argparse
import json
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from mas_benchmark.analyzers import AgreementGap, Cost, Liveness, PriceImbalance, Safety, encounters
from mas_benchmark.core import simulate
from mas_benchmark.dynamics import SingleIntegrator
from mas_benchmark.scenarios import make_scenario
from mas_benchmark.solvers import make_solver
from mas_benchmark.specs import PairwiseBarrier

RES = Path(__file__).resolve().parents[1] / 'results'
VARIANTS = ['ours_eps0.1', 'ours_eps0.1_mem', 'ours_eps0.1_mem10']


def run(method, seed, horizon):
    log = simulate(make_scenario('S1'), SingleIntegrator(), PairwiseBarrier(), make_solver(method),
                   horizon=horizon, dt=0.02, seed=seed)
    w = log.weights
    per_pair = defaultdict(list)
    for e in sorted(encounters(log), key=lambda e: e['start']):
        imb = np.abs(e['mu_i'] - e['mu_k']) / (e['mu_i'] + e['mu_k'])
        per_pair[(e['i'], e['k'])].append((float(imb.mean()), len(imb), bool(w[e['i']] == w[e['k']])))
    by_index = defaultdict(list)
    for encs in per_pair.values():
        for n, (m, _, same) in enumerate(encs):
            by_index[(min(n, 3), same)].append(m)
    row = dict(method=method, seed=seed, horizon=horizon, **Cost()(log), **Safety()(log), **AgreementGap()(log),
               **PriceImbalance()(log), **Liveness()(log),
               pairs=len(per_pair), encounters_per_pair=float(np.mean([len(v) for v in per_pair.values()])) if per_pair else 0.0,
               by_index={f'{k[0] + 1}{"+" if k[0] == 3 else ""}_{"same" if k[1] else "diff"}': [float(np.mean(v)), len(v)]
                         for k, v in by_index.items()})
    return row


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--seeds', nargs='+', type=int, default=list(range(6)))
    ap.add_argument('--horizons', nargs='+', type=float, default=[120.0, 600.0])
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--variants', nargs='+', default=VARIANTS)
    ap.add_argument('--tag', default='')
    args = ap.parse_args()
    VARIANTS = args.variants
    jobs = [(m, s, h) for h in args.horizons for m in VARIANTS for s in args.seeds]
    rows = []
    with ProcessPoolExecutor(args.workers) as ex:
        for row in ex.map(run, *zip(*jobs)):
            rows.append(row)
            print(json.dumps(row), flush=True)
    (RES / f's1_memory{args.tag}.jsonl').write_text('\n'.join(json.dumps(r) for r in rows) + '\n')
    keys = ['cost', 'min_dist_team', 'viol_team', 'imbalance', 'imbalance_time', 'imbalance_settled_diff_w',
            'imbalance_settled_same_w', 'encounters_per_pair', 'gap_min', 'stop_frac']
    lines = [f'# S1 agreement memory ({", ".join(VARIANTS)}; mean (std) over seeds; min_dist_team = min over seeds)', '']
    for h in args.horizons:
        lines += [f'## {h:g} s', '', '| variant | ' + ' | '.join(keys) + ' |', '|---|' + '---|' * len(keys)]
        for m in VARIANTS:
            sub = [r for r in rows if r['method'] == m and r['horizon'] == h]
            cells = []
            for k in keys:
                v = np.array([r[k] for r in sub], dtype=float); v = v[~np.isnan(v)]
                cells.append('–' if not len(v) else f'{v.min():.3f}' if k == 'min_dist_team' else f'{v.mean():.3f} ({v.std():.3f})')
            lines.append(f'| {m} | ' + ' | '.join(cells) + ' |')
        lines += ['', 'Imbalance by encounter index of the same pair (mean over encounters pooled across seeds; n):', '',
                  '| variant | ' + ' | '.join(f'{n}{"+" if n == 4 else ""} {t}' for t in ('diff', 'same') for n in (1, 2, 3, 4)) + ' |',
                  '|---|' + '---|' * 8]
        for m in VARIANTS:
            pool = defaultdict(list)
            for r in rows:
                if r['method'] == m and r['horizon'] == h:
                    for k, (mean, n) in r['by_index'].items():
                        pool[k] += [mean] * n
            cells = []
            for t in ('diff', 'same'):
                for n in ('1', '2', '3', '4+'):
                    v = pool.get(f'{n}_{t}', [])
                    cells.append(f'{np.mean(v):.3f} ({len(v)})' if v else '–')
            lines.append(f'| {m} | ' + ' | '.join(cells) + ' |')
        lines.append('')
    (RES / f's1_memory{args.tag}.md').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))
