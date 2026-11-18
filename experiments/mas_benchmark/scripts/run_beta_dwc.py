"""Centred beta against W0 / dW_c (work per contact, final configuration; results/beta_work_per_contact.json).

Runs centred beta (beta_max 8, c-bar as before) at W0 = 4 and 8 x the scenario's own median dW_c where no existing cell
is within 30%, and completes the existing 0.5x cell to 24 seeds, so every point of the curve has seeds 0-23.
Appends "W0 against work per contact" to results/beta.md.

    python scripts/run_beta_dwc.py [--workers 11]
"""
import argparse
import json
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from mas_benchmark.analyzers import Cost, FairOverTime, PriceImbalance, Safety
from mas_benchmark.core import simulate
from mas_benchmark.dynamics import SingleIntegrator
from mas_benchmark.scenarios import make_scenario
from mas_benchmark.solvers import make_solver
from mas_benchmark.specs import PairwiseBarrier

RES = Path(__file__).resolve().parents[1] / 'results'
WB = 16.88
CBAR = {'S1': 10.3774 / 120, 'S4': 29.3127 / 120}
DWC = {k: v['median'] for k, v in json.loads((RES / 'beta_work_per_contact.json').read_text()).items()}
EXIST = {'S1': [WB, 0.5 * WB, 0.25 * WB], 'S4': [WB, 0.5 * WB, 0.25 * WB]}


def name(sc, W0):
    return f'beta_eps0.1_W0{W0:.6g}_leakinf_bmax8_cbar{CBAR[sc]:.6g}'


def job(sc, W0, seed):
    log = simulate(make_scenario(sc), SingleIntegrator(), PairwiseBarrier(), make_solver(name(sc, W0)), 120.0, 0.02, seed)
    return dict(scenario=sc, W0=W0, seed=seed, **Cost()(log), **Safety()(log), **PriceImbalance()(log), **FairOverTime()(log))


def plan():
    jobs, notes = [], []
    for sc in ('S1', 'S4'):
        for m in (4, 8):
            target = m * DWC[sc]
            near = [w for w in EXIST[sc] if abs(w - target) / target <= 0.3]
            if near:
                notes.append(f'{sc}: {m} x dW_c = {target:.3g} is within 30% of the existing W0 = {near[0]:.3g}; not run.')
            else:
                notes.append(f'{sc}: {m} x dW_c = {target:.3g} has no existing cell within 30%; run (24 seeds).')
                jobs += [(sc, target, s) for s in range(24)]
        jobs += [(sc, 0.5 * WB, s) for s in range(6, 24)]               # complete the 0.5x cell to 24 seeds
    return jobs, notes


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=11)
    args = ap.parse_args()
    jobs, notes = plan()
    with ProcessPoolExecutor(args.workers) as ex:
        new = list(ex.map(job, *zip(*jobs)))
    (RES / 'beta_dwc.jsonl').write_text('\n'.join(json.dumps(r) for r in new) + '\n')
    pts = defaultdict(dict)                     # (sc, W0) -> seed -> row
    for r in new:
        pts[(r['scenario'], round(r['W0'], 6))][r['seed']] = r
    for l in (RES / 'beta_centred.jsonl').read_text().splitlines():
        r = json.loads(l); pts[(r['scenario'], round(r['W0x'] * WB, 6))][r['seed']] = r
    for l in (RES / 'beta_24.jsonl').read_text().splitlines():
        r = json.loads(l)
        if r['conf'].startswith('centred'):
            W0 = WB if r['conf'] == 'centred 1x' else 0.25 * WB
            pts[(r['scenario'], round(W0, 6))][r['seed']] = r
    final = {}
    for l in (RES / 'beta_24.jsonl').read_text().splitlines():
        r = json.loads(l)
        if r['conf'] == 'final':
            final[(r['scenario'], r['seed'])] = r
    for l in (RES / 'beta.jsonl').read_text().splitlines():
        r = json.loads(l)
        if r['variant'] == 'final':
            final[(r['scenario'], r['seed'])] = r
    wpc = json.loads((RES / 'beta_work_per_contact.json').read_text())
    L = ['', '## W0 against work per contact', '',
         'Work per contact dW_c in the final configuration (seeds 0–5): for each agent and each contact (a body within '
         'sensing range, from entry to exit: the span over which β is frozen), the base cost the agent accumulated during it.', '',
         '| scenario | contacts | median dW_c | 10–90% | mean dW_c | mean contact duration (s) | median duration (s) | '
         'mean simultaneous contacts |', '|---|---|---|---|---|---|---|---|']
    for sc in ('S1', 'S4'):
        w = wpc[sc]
        L.append(f"| {sc} | {w['n']} | {w['median']:.3g} | {w['p10']:.3g}–{w['p90']:.3g} | {w['mean']:.3g} | {w['dur_mean']:.1f} | "
                 f"{w['dur_median']:.1f} | {w['n_sim']:.1f} |")
    L += ['', f'dW_c differs between the scenarios (S1 {DWC["S1"]:.3g}, S4 {DWC["S4"]:.3g}), so each scenario uses its own dW_c. '
          'W0 already run, as multiples of dW_c: ' + '; '.join(
              f'{sc}: ' + ', '.join(f'{w:.3g} = {w / DWC[sc]:.1f}×' for w in EXIST[sc]) for sc in ('S1', 'S4')) + '.', '']
    L += ['Runs: ' + ' '.join(notes) + ' The existing 0.5× cell (W0 = 8.44) was completed to 24 seeds in both scenarios.', '',
          'W std/mean against W0/dW_c (centred β, β_max 8; seeds 0–23; mean ± s.e.; Δ = paired difference to the final '
          'configuration, same seeds):', '']
    for sc in ('S1', 'S4'):
        L += [f'### {sc}', '', '| W0 | W0 / dW_c | n | W std/mean | Δ vs final | cost | team viol. (%) | ext. viol. (%) |',
              '|---|---|---|---|---|---|---|---|']
        rows = sorted([(W0, d) for (s, W0), d in pts.items() if s == sc])
        for W0, d in rows:
            rr = list(d.values())
            cv = np.array([r['W_cv'] for r in rr]); dl = np.array([r['W_cv'] - final[(sc, r['seed'])]['W_cv'] for r in rr])
            se = lambda v: v.std(ddof=1) / np.sqrt(len(v))
            ext = np.array([r['viol_ext'] for r in rr], float)
            L.append(f"| {W0:.3g} | {W0 / DWC[sc]:.1f} | {len(rr)} | {cv.mean():.3f} ± {se(cv):.3f} | {dl.mean():+.3f} ± {se(dl):.3f} | "
                     f"{np.mean([r['cost'] for r in rr]):.3f} | {100 * np.mean([r['viol_team'] for r in rr]):.2f} | "
                     f"{'–' if sc == 'S1' else f'{100 * np.nanmean(ext):.2f} ± {100 * se(ext):.2f}'} |")
        L.append('')
    with (RES / 'beta.md').open('a') as fh:
        fh.write('\n'.join(L) + '\n')
    print('\n'.join(L))
