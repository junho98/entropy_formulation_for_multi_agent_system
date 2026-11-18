"""Re-check the tuning with target_sep = 1.5 (no stuck target pairs): reduced grid around each chosen point (chosen
value, its neighbours, the default), same tuning seeds 100-102 and cells (+ts1.5), same selection rule over all
evaluated points. Ours: window 25 vs 50; centred beta W0 2.1 vs 4.22 on the chosen point. Then the standstill rate of
every chosen setting in HOM-E0 / HET-E0 (+ts1.5, seeds 0-11).

    python scripts/retune_ts.py [--workers 11]
      -> results/tuning/chosen_*.json (old ones kept as chosen_*_no_ts.json), section "Re-check with target_sep 1.5"
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_tuning as T                                                    # noqa: E402

TS = '+ts1.5'
CELLS = tuple(c + TS for c in T.CELLS)
E0 = ('HOM-E0' + TS, 'HET-E0' + TS)
GRID = {
    'oracle': [dict(kappa=k, margin=m) for k, m in ((16, 0), (8, 0), (32, 0), (16, 0.05), (2, 0))],
    'reciprocal': [dict(kappa=k, margin=m) for k, m in ((16, 0.3), (8, 0.3), (32, 0.3), (16, 0.2), (16, 0.4), (2, 0))],
    'pcca': [dict(kappa=k, margin=m) for k, m in ((1, 0.2), (0.5, 0.2), (2, 0.2), (1, 0.1), (1, 0.3), (2, 0))],
    'tan': [dict(k0=k, sat_width=s) for k, s in ((1, 0.1), (0.5, 0.1), (2, 0.1), (1, 0.02), (1, 0.5))],
    'risk_ratio': [dict(c_scale=c, kappa=k) for c, k in ((2, 4), (1, 4), (4, 4), (2, 2), (2, 8), (1, 2))],
}
GRID = {m: [{k: float(v) for k, v in p.items()} for p in G] for m, G in GRID.items()}
OURS = [dict(T.OURS0, window=25), dict(T.OURS0)]
W0S = (2.1, 4.22)


def dead_rate(rows, m, p):
    R = [r for r in rows if r['method'] == m and r['cell'] in E0 and r['params'] == p and r['seed'] < 12]
    R = list({(r['cell'], r['seed']): r for r in R}.values())
    ls = np.array([r['longest_stop_s'] for r in R])
    return f'{int((ls > 10).sum())}/{len(R)} (longest {ls.max():.0f} s, stop fraction {np.mean([r["stop_frac"] for r in R]):.3f})'


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=11)
    a = ap.parse_args()
    for n in ('baselines', 'ours', 'beta'):
        src, dst = T.OUT / f'chosen_{n}.json', T.OUT / f'chosen_{n}_no_ts.json'
        if not dst.exists():
            shutil.copy(src, dst)
    old_b = json.loads((T.OUT / 'chosen_baselines_no_ts.json').read_text())
    jobs = [(c, m, p, s) for m, G in GRID.items() for p in G for c in CELLS for s in T.SEEDS]
    jobs += [(c, 'ours', p, s) for p in OURS for c in CELLS for s in T.SEEDS]
    T.execute(jobs, a.workers)
    rows = T.load()
    L = ['Same tuning seeds (100–102) and cells, all with target_sep = 1.5; reduced grid around each earlier choice (chosen '
         'value, its neighbours, the default); same selection rule over every evaluated point. Relative cost is to the '
         'default on the same cell and seed under target_sep 1.5.', '']
    chosen = {}
    for m, G in GRID.items():
        ch, tab = T.select(rows, m, G, T.DEFAULT[m], cells=CELLS)
        chosen[m] = ch
        same = ch == {k: float(v) for k, v in old_b[m].items()}
        L += [f'### {m}', '', f'Earlier choice: {T.fmt_p(old_b[m])}. Now: {T.fmt_p(ch)} ({"unchanged" if same else "CHANGED"}).', '']
        L += T.table(tab, ch, T.DEFAULT[m]) + ['']
    ch, tab = T.select(rows, 'ours', OURS, T.OURS0, cells=CELLS)
    L += ['### Ours', '', f'Earlier choice: window 25. Now: window {ch["window"]:g} '
          f'({"unchanged" if ch["window"] == 25 else "CHANGED"}).', ''] + T.table(tab, ch, T.OURS0) + ['']
    best = ch
    cb = T.cbar_of(rows, best, CELLS, T.SEEDS)
    T.execute([(c, 'beta', dict(best, W0=w, cbar=cb[c]), s)
               for w in W0S for c in CELLS for s in T.SEEDS], a.workers)
    rows = T.load()
    base = T.select(rows, 'ours', [best], best, cells=CELLS)[1][0]
    bt = []
    for w in W0S:
        R = [r for r in rows if r['method'] == 'beta' and r['cell'] in CELLS and r['seed'] in T.SEEDS
             and r['params'] == dict(best, W0=w, cbar=cb[r['cell']])]
        v = np.array([(0 if not np.isfinite(r['viol_ext']) else 100 * r['viol_ext']) + 100 * r['viol_team'] for r in R])
        bt.append((w, len(R), v.mean(), v.std(ddof=1) / np.sqrt(len(v)), np.mean([r['W_cv'] for r in R]),
                   np.mean([r['cost'] for r in R]), v.mean() <= base[2] + max(base[3], 0.2)))
    ok = [t for t in bt if t[-1]]
    w_ch = min(ok, key=lambda t: t[4])[0] if ok else None
    L += ['### Centred β on the chosen point', '', 'c̄ per cell: ' + ', '.join(f'{c} {v:.4f}' for c, v in cb.items()) + '.', '',
          f'Chosen point (no β): violation score {base[2]:.2f} ± {base[3]:.2f}, W std/mean {base[8]:.3f}, cost {base[5]:.3f}.', '',
          '| W0 | n | violation score (pp) | W std/mean | cost | not worse in violation |', '|---|---|---|---|---|---|']
    L += [f'| {w:g}{" **(chosen)**" if w == w_ch else ""} | {n} | {m_:.2f} ± {s:.2f} | {cv:.3f} | {c:.3f} | {"yes" if o else "no"} |'
          for w, n, m_, s, cv, c, o in bt]
    (T.OUT / 'chosen_baselines.json').write_text(json.dumps(chosen, indent=1))
    (T.OUT / 'chosen_ours.json').write_text(json.dumps(best, indent=1))
    (T.OUT / 'chosen_beta.json').write_text(json.dumps(dict(best, W0=w_ch, beta_max=8.0, cbar_tuning=cb, target_sep=1.5), indent=1))
    # standstill rate of each chosen setting in the E0 cells (seeds 0-11)
    e0 = [(c, m, chosen[m], s) for m in GRID for c in E0 for s in range(12)]
    e0 += [(c, 'ours', dict(best, eps=e), s) for e in (0.1, 0.2, 0.3) for c in E0 for s in range(12)]
    T.execute(e0, a.workers)
    rows = T.load()
    L += ['', '### Standstills of the chosen settings, HOM-E0 and HET-E0 (+ts1.5), seeds 0–11', '',
          'Deadlocked runs (some agent stopped > 10 s) out of 24 (both cells).', '']
    L += [f'- {m} ({T.fmt_p(chosen[m])}): {dead_rate(rows, m, chosen[m])}' for m in GRID]
    L += [f'- Ours tuned ε {e:g}: {dead_rate(rows, "ours", dict(best, eps=e))}' for e in (0.1, 0.2, 0.3)]
    T.write_section('Re-check with target_sep 1.5', L)
    print('\n'.join(L), flush=True)
