"""Extension of the W0 / dW_c curve: centred beta (beta_max 8) at W0 = 0.5, 1 and 2 x the scenario's median dW_c,
24 seeds, S1 and S4. Appends the full curve (all W0 run so far) to results/beta.md.

    python scripts/run_beta_dwc2.py [--workers 11]
"""
import argparse
import json
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from mas_benchmark.analyzers import BetaTuning, Cost, FairOverTime, PriceImbalance, Safety
from mas_benchmark.core import simulate
from mas_benchmark.dynamics import SingleIntegrator
from mas_benchmark.scenarios import make_scenario
from mas_benchmark.solvers import make_solver
from mas_benchmark.specs import PairwiseBarrier
from run_beta_dwc import CBAR, DWC, RES, WB, name


def job(sc, W0, seed):
    log = simulate(make_scenario(sc), SingleIntegrator(), PairwiseBarrier(), make_solver(name(sc, W0)), 120.0, 0.02, seed)
    out = dict(scenario=sc, W0=W0, seed=seed, **Cost()(log), **Safety()(log), **PriceImbalance()(log),
               **FairOverTime()(log), **BetaTuning(8.0)(log))
    out.pop('viol_events', None)
    return out


def se(v):
    v = np.asarray(v, float)
    return v.std(ddof=1) / np.sqrt(len(v))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=11)
    args = ap.parse_args()
    jobs = [(sc, m * DWC[sc], s) for sc in ('S1', 'S4') for m in (0.5, 1.0, 2.0) for s in range(24)]
    with ProcessPoolExecutor(args.workers) as ex:
        new = list(ex.map(job, *zip(*jobs)))
    (RES / 'beta_dwc2.jsonl').write_text('\n'.join(json.dumps(r) for r in new) + '\n')
    pts = defaultdict(dict)
    for f in ('beta_dwc.jsonl', 'beta_dwc2.jsonl'):
        for l in (RES / f).read_text().splitlines():
            r = json.loads(l); pts[(r['scenario'], round(r['W0'], 6))][r['seed']] = r
    for l in (RES / 'beta_centred.jsonl').read_text().splitlines():
        r = json.loads(l); pts[(r['scenario'], round(r['W0x'] * WB, 6))][r['seed']] = r
    for l in (RES / 'beta_24.jsonl').read_text().splitlines():
        r = json.loads(l)
        if r['conf'].startswith('centred'):
            pts[(r['scenario'], round(WB if r['conf'] == 'centred 1x' else 0.25 * WB, 6))][r['seed']] = r
    final = {}
    for f in ('beta.jsonl', 'beta_24.jsonl'):
        for l in (RES / f).read_text().splitlines():
            r = json.loads(l)
            if r.get('variant') == 'final' or r.get('conf') == 'final':
                final[(r['scenario'], r['seed'])] = r
    L = ['', '## W0 against work per contact: full curve (with 0.5×, 1× and 2× dW_c)', '',
         'Centred β, β_max 8, seeds 0–23 at every point; each scenario uses its own median dW_c (S1 '
         f'{DWC["S1"]:.3g}, S4 {DWC["S4"]:.3g}). New points: W0 = 0.5, 1 and 2 × dW_c. Δ = paired difference to the final '
         'configuration (same seeds). Cap fractions: agent-time with β^QP at β_max (upper) or 1/β_max (lower); "–" where the '
         'earlier runs did not log them for all seeds.', '']
    best = {}
    for sc in ('S1', 'S4'):
        L += [f'### {sc}', '', '| W0 | W0 / dW_c | n | W std/mean | Δ vs final | cost | team viol. (%) | ext. viol. (%) | '
              'β at upper cap | β at lower cap |', '|---|---|---|---|---|---|---|---|---|---|']
        rows = sorted([(W0, d) for (s, W0), d in pts.items() if s == sc])
        curve = []
        for W0, d in rows:
            rr = list(d.values())
            cv = np.array([r['W_cv'] for r in rr]); dl = np.array([r['W_cv'] - final[(sc, r['seed'])]['W_cv'] for r in rr])
            ext = np.array([r['viol_ext'] for r in rr], float); team = np.array([r['viol_team'] for r in rr], float)
            up = [r.get('cap_frac') for r in rr]; lo = [r.get('cap_low_frac') for r in rr]
            capu = f'{np.mean(up):.2f}' if all(x is not None for x in up) else '–'
            capl = f'{np.mean(lo):.2f}' if all(x is not None for x in lo) else '–'
            L.append(f"| {W0:.3g} | {W0 / DWC[sc]:.1f} | {len(rr)} | {cv.mean():.3f} ± {se(cv):.3f} | {dl.mean():+.3f} ± {se(dl):.3f} | "
                     f"{np.mean([r['cost'] for r in rr]):.3f} | {100 * team.mean():.2f} ± {100 * se(team):.2f} | "
                     f"{'–' if sc == 'S1' else f'{100 * np.nanmean(ext):.2f} ± {100 * se(ext):.2f}'} | {capu} | {capl} |")
            curve.append((W0 / DWC[sc], cv.mean(), se(cv), d))
        L.append('')
        i = int(np.argmin([c[1] for c in curve]))
        best[sc] = curve[i]
        L.append(f'Minimum of the point estimates in {sc}: W0 = {curve[i][0]:.1f} × dW_c (W std/mean {curve[i][1]:.3f} ± {curve[i][2]:.3f}).')
        L.append('Paired differences to the minimum (same seeds):')
        for m, mu, s_, d in curve:
            if m == curve[i][0]:
                continue
            ks = sorted(set(d) & set(curve[i][3]))
            dd = np.array([d[k]['W_cv'] - curve[i][3][k]['W_cv'] for k in ks])
            L.append(f'- {m:.1f}× − {curve[i][0]:.1f}×: {dd.mean():+.3f} ± {se(dd):.3f}')
        L.append('')
    with (RES / 'beta.md').open('a') as fh:
        fh.write('\n'.join(L) + '\n')
    print('\n'.join(L))
