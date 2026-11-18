"""Nominal right-hand bias against head-on deadlocks: u_des = v (g + b R(-90°) g) / |.|, the same for every method
(scenario-level, default off). Variants: b in {0.05, 0.1, 0.2} always on, and b = 0.1 only while another body is within
5 and ahead ('near'). HOM-E0 / HET-E0, seeds 0-11, 120 s, Ours current/tuned at eps 0.1/0.2/0.3 and every baseline
(default and tuned); sanity on HOM-E8 (seeds 0-5: Ours eps 0.1, PCCA tuned, Oracle tuned).

    python scripts/bias_check.py [--workers 11]   -> appends "Nominal bias" to results/tuning/tuning.md
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_tuning as T                                                    # noqa: E402

VARIANTS = [('none', ''), ('b = 0.05', '+b0.05'), ('b = 0.1', '+b0.1'), ('b = 0.2', '+b0.2'), ('b = 0.1, near', '+bn0.1'),
            ('body b = 0.05', '+bb0.05'), ('body b = 0.1', '+bb0.1'), ('body b = 0.2', '+bb0.2'),
            ('targets ≥ 1.5 apart', '+ts1.5'), ('targets ≥ 2 apart', '+ts2')]
CELLS = ('HOM-E0', 'HET-E0')
SEEDS = list(range(12))
DEAD = 10.0
TUNED = json.loads((T.OUT / 'chosen_baselines.json').read_text())
OURS_T = json.loads((T.OUT / 'chosen_ours.json').read_text())
METHODS = ([(f'Ours current ε {e:g}', 'ours', dict(T.OURS0, eps=e)) for e in (0.1, 0.2, 0.3)]
           + [(f'Ours tuned ε {e:g}', 'ours', dict(OURS_T, eps=e)) for e in (0.1, 0.2, 0.3)]
           + [(f'{m} default', m, T.DEFAULT[m]) for m in ('oracle', 'reciprocal', 'pcca', 'risk_ratio')]
           + [(f'{m} tuned', m, TUNED[m]) for m in ('oracle', 'reciprocal', 'pcca', 'risk_ratio')]
           + [('tan', 'tan', T.DEFAULT['tan'])])
SANITY = [('Ours ε 0.1', 'ours', dict(T.OURS0)), ('PCCA tuned', 'pcca', TUNED['pcca']), ('Oracle tuned', 'oracle', TUNED['oracle'])]


def find(rows, cell, m, p, seeds):
    R = {r['seed']: r for r in rows if r['cell'] == cell and r['method'] == m and r['params'] == p and r['seed'] in seeds}
    return list(R.values())                    # one row per seed (Tan default = tuned was stored twice)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=11)
    a = ap.parse_args()
    jobs = [(c + v, m, p, s) for _, v in VARIANTS for c in CELLS for _, m, p in METHODS for s in SEEDS]
    jobs += [('HOM-E8' + v, m, p, s) for _, v in VARIANTS for _, m, p in SANITY for s in range(6)]
    T.execute(jobs, a.workers)
    rows = T.load()
    L = ['Scenario-level option, default off (all earlier results unchanged): the shared nominal controller turns the goal '
         'direction g slightly clockwise, u_des = v (g + b R(−90°) g)/‖·‖, for every method alike; outsiders unchanged. '
         '"near": the bias is applied only while another body is within 5 and ahead (g·(q − p) > 0). "body": instead of '
         'rotating g, add b R(−90°) r̂ with r̂ the unit vector to the nearest body ahead within 2 (sidestep to the right of '
         'that body), u_des = v (g + b R(−90°) r̂)/‖·‖. "targets ≥ s apart": no bias; a newly drawn target keeps at least s '
         'from the other agents’ current targets (redrawn otherwise). HOM-E0 and HET-E0, '
         'seeds 0–11 × 120 s. Deadlock: some agent stopped (|u| < 0.15) for more than 10 s in a row.', '']
    for c in CELLS:
        L += [f'### {c}', '', '| method | ' + ' | '.join(n for n, _ in VARIANTS) + ' |', '|---|' + '---|' * len(VARIANTS)]
        for name, m, p in METHODS:
            cells = []
            for _, v in VARIANTS:
                R = find(rows, c + v, m, p, SEEDS)
                if not R:
                    cells.append('–'); continue
                ls = np.array([r['longest_stop_s'] for r in R])
                cells.append(f"{int((ls > DEAD).sum())}/{len(R)} · {ls.max():.0f} s · {np.mean([r['cost'] for r in R]):.3f} · "
                             f"{100 * np.mean([r['viol_team'] for r in R]):.2f} · {np.mean([r['W_cv'] for r in R]):.2f}")
            L.append(f'| {name} | ' + ' | '.join(cells) + ' |')
        L += ['', 'Each cell: deadlocked seeds · longest stop (max over seeds) · cost · team violation (%) · W std/mean (means over seeds).', '']
    L += ['### Sanity: HOM-E8, seeds 0–5', '', '| method | ' + ' | '.join(n for n, _ in VARIANTS) + ' |', '|---|' + '---|' * len(VARIANTS)]
    for name, m, p in SANITY:
        cells = []
        for _, v in VARIANTS:
            R = find(rows, 'HOM-E8' + v, m, p, set(range(6)))
            e = np.array([100 * r['viol_ext'] for r in R])
            cells.append(f"{e.mean():.2f} ± {e.std(ddof=1) / np.sqrt(len(e)):.2f} · {100 * np.mean([r['viol_team'] for r in R]):.2f} · "
                         f"{np.mean([r['cost'] for r in R]):.3f} · {max(r['longest_stop_s'] for r in R):.0f} s")
        L.append(f'| {name} | ' + ' | '.join(cells) + ' |')
    L += ['', 'Each cell: outsider violation (%, mean ± s.e.) · team violation (%) · cost · longest stop.', '']
    T.write_section('Nominal bias', L)
    print('\n'.join(L), flush=True)
