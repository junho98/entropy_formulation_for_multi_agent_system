"""1-seed table with target_sep 1.5: seed 0, 120 s, six cells +ts1.5; baselines default and re-checked tuned values,
Ours (window 50) at eps 0.1/0.2/0.3, centred beta W0 2.1 and 4.22 (c-bar per cell = fleet-mean work rate of the Ours
eps 0.1 run of that cell, seed 0).

    python scripts/oneseed_ts.py [--workers 11]   -> results/tuning/one_seed_ts.md
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_tuning as T                                                    # noqa: E402
from mas_benchmark.scenarios import GRID2X3                               # noqa: E402

TS = '+ts1.5'
CELLS = [c + TS for c in GRID2X3]
W0S = (2.1, 4.22)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=11)
    a = ap.parse_args()
    tuned = json.loads((T.OUT / 'chosen_baselines.json').read_text())
    ours = json.loads((T.OUT / 'chosen_ours.json').read_text())
    confs = []
    for m in T.GRIDS:
        confs.append((f'{m} default', m, T.DEFAULT[m]))
        if tuned[m] != T.DEFAULT[m]:
            confs.append((f'{m} tuned', m, tuned[m]))
    confs += [(f'Ours ε {e:g}', 'ours', dict(ours, eps=e)) for e in (0.1, 0.2, 0.3)]
    T.execute([(c, m, p, 0) for _, m, p in confs for c in CELLS], a.workers)
    rows = T.load()
    get = lambda c, m, p: next((r for r in rows if r['cell'] == c and r['method'] == m and r['params'] == p and r['seed'] == 0), None)
    cb = {c: get(c, 'ours', dict(ours, eps=0.1))['cost'] for c in CELLS}
    T.execute([(c, 'beta', dict(ours, W0=w, cbar=cb[c]), 0) for w in W0S for c in CELLS], a.workers)
    rows = T.load()
    L = ['# One seed, target_sep 1.5', '',
         'Seed 0, 120 s, all six cells with target_sep = 1.5. Baselines at default and at the values re-checked under '
         'target_sep 1.5 (Tan: published only). Ours: window 50 (the re-check kept the original point). Centred β: β_max 8, '
         'c̄ per cell = fleet-mean work rate (mean_i W_i(120)/120) of the Ours ε = 0.1 run of the same cell and seed: '
         + ', '.join(f'{c[:-len(TS)]} {v:.4f}' for c, v in cb.items()) + '. Violation: % of time below 0.95ρ (true ρ).', '']
    for c in CELLS:
        e0 = c.split('+')[0].endswith('E0')
        L += [f'## {c[:-len(TS)]}', '', '| method | setting | cost | viol. outsiders (%) | viol. team (%) | min dist. outsiders | '
              'min dist. team | W std/mean | longest stop (s) |', '|---|---|---|---|---|---|---|---|---|']
        for name, m, p in confs + [(f'Ours + centred β, W0 = {w:g}', 'beta', w) for w in W0S]:
            if m == 'beta':
                p = dict(ours, W0=p, cbar=cb[c])
            r = get(c, m, p)
            if r is None:
                continue
            ve = '–' if e0 else f"{100 * r['viol_ext']:.2f}"
            de = '–' if e0 else f"{r['min_dist_ext']:.2f}"
            L.append(f"| {name} | {T.fmt_p(p) if m not in ('ours', 'beta') else ''} | {r['cost']:.3f} | {ve} | "
                     f"{100 * r['viol_team']:.2f} | {de} | {r['min_dist_team']:.2f} | {r['W_cv']:.3f} | {r['longest_stop_s']:.1f} |")
        L.append('')
    (T.OUT / 'one_seed_ts.md').write_text('\n'.join(L) + '\n')
    print('\n'.join(L), flush=True)
