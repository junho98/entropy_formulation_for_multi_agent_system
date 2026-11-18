"""Beta choice with 24 seeds: final config, uncentred (1x, beta_max 8), centred 1x and 0.25x (beta_max 8, c-bar S1
.0865, S4 .2443). Runs seeds 6-23 and pools them with the existing seeds 0-5. Appends "24 seeds" to results/beta.md.

    python scripts/run_beta_24.py [--workers 11]
"""
import argparse
import json
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from mas_benchmark.analyzers import BetaReading, BetaTuning, Cost, FairOverTime, PriceImbalance, Safety
from mas_benchmark.core import simulate
from mas_benchmark.dynamics import SingleIntegrator
from mas_benchmark.scenarios import make_scenario
from mas_benchmark.solvers import make_solver
from mas_benchmark.specs import PairwiseBarrier

RES = Path(__file__).resolve().parents[1] / 'results'
WB = 16.88
CBAR = {'S1': 10.3774 / 120, 'S4': 29.3127 / 120}
CONF = {'final': lambda sc: 'ours_eps0.1_mutual',
        'uncentred (1x, 8)': lambda sc: f'beta_eps0.1_W0{WB:g}_leakinf_bmax8',
        'centred 1x': lambda sc: f'beta_eps0.1_W0{WB:g}_leakinf_bmax8_cbar{CBAR[sc]:.6g}',
        'centred 0.25x': lambda sc: f'beta_eps0.1_W0{0.25 * WB:g}_leakinf_bmax8_cbar{CBAR[sc]:.6g}'}


def job(sc, conf, seed):
    log = simulate(make_scenario(sc), SingleIntegrator(), PairwiseBarrier(), make_solver(CONF[conf](sc)), 120.0, 0.02, seed)
    out = dict(scenario=sc, conf=conf, seed=seed, **Cost()(log), **Safety()(log), **PriceImbalance()(log),
               **FairOverTime()(log), **BetaReading()(log))
    if conf != 'final':
        out.update(BetaTuning(8.0)(log))
    out.pop('viol_events', None)
    return out


def jain(W):
    W = np.asarray(W, float)
    return float(W.sum() ** 2 / (len(W) * np.sum(W ** 2)))


def old_rows():
    rows = []
    for l in (RES / 'beta.jsonl').read_text().splitlines():
        r = json.loads(l)
        if r['variant'] == 'final':
            rows.append(dict(r, conf='final'))
    for l in (RES / 'beta_tune.jsonl').read_text().splitlines():
        r = json.loads(l)
        if r['W0x'] == 1.0 and r['bmax'] == 8.0:
            rows.append(dict(r, conf='uncentred (1x, 8)'))
    for l in (RES / 'beta_centred.jsonl').read_text().splitlines():
        r = json.loads(l)
        if r['W0x'] in (1.0, 0.25):
            rows.append(dict(r, conf='centred 1x' if r['W0x'] == 1.0 else 'centred 0.25x'))
    return rows


def ms(v, pct=False, nd=3):
    v = np.array([x for x in v if x is not None and np.isfinite(x)], float)
    m, s = v.mean(), v.std(ddof=1) / np.sqrt(len(v))
    return f'{100 * m:.2f} ± {100 * s:.2f}' if pct else f'{m:.{nd}f} ± {s:.{nd}f}'


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=11)
    args = ap.parse_args()
    jobs = [(sc, c, s) for sc in ('S1', 'S4') for c in CONF for s in range(6, 24)]
    with ProcessPoolExecutor(args.workers) as ex:
        new = list(ex.map(job, *zip(*jobs)))
    (RES / 'beta_24.jsonl').write_text('\n'.join(json.dumps(r) for r in new) + '\n')
    rows = old_rows() + new
    for r in rows:
        r['jain'] = jain(r['W']); r['W_max'] = float(np.max(r['W']))
    g = defaultdict(dict)
    for r in rows:
        g[(r['scenario'], r['conf'])][r['seed']] = r
    L = ['', '## 24 seeds', '',
         'Seeds 0–23 (0–5 from the earlier runs, 6–23 new), 120 s, ε = 0.1; c̄ as before (S1 0.0865, S4 0.2443); β_max = 8 '
         'for the β rows. Mean ± s.e. over seeds. Paired differences use the same seed in both configurations.', '']
    for sc in ('S1', 'S4'):
        L += [f'### {sc}', '', '| configuration | n | cost | W std/mean | Jain(W) | max W_i | viol. agents (%) | viol. ext. (%) | '
              'imbalance (time-w.) |', '|---|---|---|---|---|---|---|---|---|']
        for c in CONF:
            rr = list(g[(sc, c)].values())
            L.append(f"| {c} | {len(rr)} | {ms([r['cost'] for r in rr])} | {ms([r['W_cv'] for r in rr])} | {ms([r['jain'] for r in rr])} | "
                     f"{ms([r['W_max'] for r in rr], nd=1)} | {ms([r['viol_team'] for r in rr], pct=True)} | "
                     f"{ms([r['viol_ext'] for r in rr], pct=True) if sc == 'S4' else '–'} | {ms([r.get('imbalance_time') for r in rr], nd=2)} |")
        L += ['', 'Paired differences (row − reference, same seeds; mean ± s.e.):', '',
              '| comparison | n | Δ W std/mean | Δ ext. viol. (pp) | Δ cost |', '|---|---|---|---|---|']
        for a, b in [('uncentred (1x, 8)', 'final'), ('centred 1x', 'final'), ('centred 0.25x', 'final'),
                     ('centred 0.25x', 'uncentred (1x, 8)')]:
            seeds = sorted(set(g[(sc, a)]) & set(g[(sc, b)]))
            dW = [g[(sc, a)][s]['W_cv'] - g[(sc, b)][s]['W_cv'] for s in seeds]
            dE = [100 * (g[(sc, a)][s]['viol_ext'] - g[(sc, b)][s]['viol_ext']) for s in seeds] if sc == 'S4' else None
            dC = [g[(sc, a)][s]['cost'] - g[(sc, b)][s]['cost'] for s in seeds]
            L.append(f"| {a} − {b} | {len(seeds)} | {ms(dW)} | {ms(dE, nd=2) if dE else '–'} | {ms(dC)} |")
        L.append('')
    with (RES / 'beta.md').open('a') as fh:
        fh.write('\n'.join(L) + '\n')
    print('\n'.join(L))
