"""Parameter tuning on the 2x3 grid (tuning seeds 100-102, never the evaluation seeds), then a 1-seed sweep.

    python scripts/run_tuning.py baselines   # small grid per baseline -> results/tuning/runs.jsonl, tuning.md
    python scripts/run_tuning.py ours        # coordinate-wise from the current point, then centred beta W0
    python scripts/run_tuning.py oneseed     # seed 0, 120 s, six cells x all methods -> results/tuning/one_seed.md

Selection rule (one setting for all cells): minimise the violation score (time in violation toward outsiders + among
the team, pp, mean over cells x seeds); among settings within max(1 s.e. of the best, 0.2 pp) of the best, the lowest
cost, measured as the mean ratio to the default setting's cost on the same cell and seed.
Runs already in runs.jsonl are skipped, so every stage resumes.
"""
import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

from mas_benchmark.analyzers import AgreementGap, Cost, Liveness, PriceImbalance, Safety
from mas_benchmark.configs import evaluate
from mas_benchmark.scenarios import GRID2X3

OUT = Path(__file__).resolve().parents[1] / 'results' / 'tuning'
RUNS = OUT / 'runs.jsonl'
CELLS = ('HOM-E8', 'HET-E8', 'HET-E0', 'HOM-E4')
SEEDS = (100, 101, 102)
WB = 16.88

CBF = [dict(kappa=k, margin=m) for k in (1.0, 2.0, 4.0, 8.0) for m in (0.0, 0.05, 0.1)]
GRIDS = {
    'oracle': list(CBF), 'reciprocal': list(CBF), 'pcca': list(CBF),
    'tan': [dict(k0=k, sat_width=s) for k in (0.5, 1.0, 2.0, 5.0) for s in (0.02, 0.1, 0.5)],
    'risk_ratio': [dict(c_scale=c, kappa=k) for c in (0.5, 1.0, 2.0, 4.0) for k in (1.0, 2.0, 4.0)],
}
# extension (2026-11-13): no chosen value on a grid edge -> wider margin / kappa where the first grid's choice sat on one
GRIDS['reciprocal'] += [dict(kappa=k, margin=m) for k in (4.0, 8.0) for m in (0.2, 0.3)] + \
    [dict(kappa=16.0, margin=m) for m in (0.1, 0.2, 0.3)]
GRIDS['pcca'] += [dict(kappa=k, margin=m) for k in (1.0, 2.0) for m in (0.2, 0.3)] + \
    [dict(kappa=0.5, margin=m) for m in (0.1, 0.2, 0.3)]
GRIDS['oracle'] += [dict(kappa=16.0, margin=m) for m in (0.0, 0.05, 0.1)]
GRIDS['risk_ratio'] += [dict(c_scale=c, kappa=8.0) for c in (1.0, 2.0, 4.0)]
# second extension: Oracle chose kappa 16 and Reciprocal kappa 16 / margin 0.3, both still on an edge
GRIDS['oracle'] += [dict(kappa=32.0, margin=m) for m in (0.0, 0.05)]
GRIDS['reciprocal'] += [dict(kappa=16.0, margin=0.4)] + [dict(kappa=32.0, margin=m) for m in (0.3, 0.4)]
DEFAULT = {'oracle': dict(kappa=2.0, margin=0.0), 'reciprocal': dict(kappa=2.0, margin=0.0),
           'pcca': dict(kappa=2.0, margin=0.0), 'tan': dict(k0=1.0, sat_width=0.1),
           'risk_ratio': dict(c_scale=1.0, kappa=2.0)}
OURS0 = dict(eps=0.1, ke=20.0, delta=0.05, window=50, follow_prior=0.97)
OURS_AXES = {'ke': (10.0, 40.0), 'delta': (0.02, 0.1), 'window': (25, 100), 'follow_prior': (0.99,)}
W0S = (2.1, 4.22, 8.44)


def key(cell, method, params, seed):
    return json.dumps([cell, method, sorted(params.items()), seed])


def run(cell, method, params, seed, horizon=120.0):
    t0 = time.time()
    log = evaluate(cell, method, seed, horizon, **params)
    f = 0.5 * log.weights[None] * np.sum((log.u - log.u_nom) ** 2, axis=2) * log.dt
    W = f.sum(axis=0)
    row = dict(cell=cell, method=method, params=params, seed=seed, wall_s=round(time.time() - t0, 1),
               W_cv=float(W.std() / W.mean()), jain=float(W.sum() ** 2 / (len(W) * np.sum(W ** 2))),
               W_range=float(W.max() - W.min()), **Cost()(log), **Safety()(log), **Liveness()(log))
    if method in ('ours', 'beta'):
        row.update(**AgreementGap()(log), **PriceImbalance()(log))
    return row


def load():
    return [json.loads(l) for l in RUNS.read_text().splitlines()] if RUNS.exists() else []


def execute(jobs, workers):
    have = {key(r['cell'], r['method'], r['params'], r['seed']) for r in load()}
    jobs = [j for j in jobs if key(*j) not in have]
    print(f'{len(jobs)} runs', flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(workers) as ex, RUNS.open('a') as fh:
        futs = [ex.submit(run, *j) for j in jobs]
        for n, fut in enumerate(as_completed(futs), 1):
            r = fut.result()
            fh.write(json.dumps(r) + '\n'); fh.flush()
            if n % 20 == 0 or n == len(futs):
                print(f'{n}/{len(futs)} done', flush=True)


def select(rows, method, settings, default, cells=CELLS, seeds=SEEDS):
    """-> (chosen params, table rows [(params, n, score m, s.e., rel. cost, cost, ext, team, W_cv, admissible)])."""
    idx = {(r['cell'], r['seed'], json.dumps(sorted(r['params'].items()))): r for r in rows if r['method'] == method}
    dk = json.dumps(sorted(default.items()))
    tab = []
    for p in settings:
        pk = json.dumps(sorted(p.items()))
        R = [(idx.get((c, s, pk)), idx.get((c, s, dk))) for c in cells for s in seeds]
        R = [(a, b) for a, b in R if a is not None and b is not None]
        if not R:
            continue
        ext = np.array([0.0 if not np.isfinite(a['viol_ext']) else 100 * a['viol_ext'] for a, _ in R])
        team = np.array([100 * a['viol_team'] for a, _ in R])
        v = ext + team
        rel = np.array([a['cost'] / b['cost'] for a, b in R])
        tab.append([p, len(R), v.mean(), v.std(ddof=1) / np.sqrt(len(v)), rel.mean(),
                    np.mean([a['cost'] for a, _ in R]), ext.mean(), team.mean(), np.mean([a['W_cv'] for a, _ in R])])
    best = min(tab, key=lambda t: t[2])
    tol = max(best[3], 0.2)
    for t in tab:
        t.append(t[2] <= best[2] + tol)
    chosen = min((t for t in tab if t[-1]), key=lambda t: t[4])
    return chosen[0], tab


def fmt_p(p):
    return ', '.join(f'{k}={v:g}' for k, v in p.items())


def table(tab, chosen, default):
    L = ['| setting | n | violation score (pp) | rel. cost | cost | ext. (pp) | team (pp) | W std/mean | admissible |',
         '|---|---|---|---|---|---|---|---|---|']
    for p, n, m, s, rel, c, e, tm, cv, ok in tab:
        tag = (' **(chosen)**' if p == chosen else '') + (' (default)' if p == default else '')
        L.append(f'| {fmt_p(p)}{tag} | {n} | {m:.2f} ± {s:.2f} | {rel:.3f} | {c:.3f} | {e:.2f} | {tm:.2f} | {cv:.3f} | '
                 f'{"yes" if ok else ""} |')
    return L


def cbar_of(rows, params, cells, seeds):
    pk = json.dumps(sorted(params.items()))
    return {c: float(np.mean([r['cost'] for r in rows if r['method'] == 'ours' and r['cell'] == c and r['seed'] in seeds
                              and json.dumps(sorted(r['params'].items())) == pk])) for c in cells}


def write_section(name, lines):
    p = OUT / 'tuning.md'
    text = p.read_text() if p.exists() else ('# Tuning\n\nCells ' + ', '.join(CELLS) + '; tuning seeds ' +
                                              ', '.join(map(str, SEEDS)) + ' (not the evaluation seeds 0–23); 120 s. '
                                              + __doc__.split('Selection rule')[1].split('Runs already')[0].strip()
                                              .replace('(one setting', 'Selection rule (one setting') + '\n')
    marker = f'\n## {name}\n'
    tail = ''
    if marker in text:
        text, rest = text.split(marker, 1)
        tail = rest[rest.index('\n## '):] if '\n## ' in rest else ''       # keep the sections after this one
    p.write_text(text + marker + '\n' + '\n'.join(lines) + '\n' + tail)


def stage_baselines(workers):
    jobs = [(c, m, p, s) for m, G in GRIDS.items() for p in G for c in CELLS for s in SEEDS]
    execute(jobs, workers)
    rows, L, chosen = load(), [], {}
    for m, G in GRIDS.items():
        ch, tab = select(rows, m, G, DEFAULT[m])
        chosen[m] = ch
        L += [f'### {m}', '', f'Default (published / as implemented): {fmt_p(DEFAULT[m])}. Chosen: {fmt_p(ch)}.', '']
        L += table(tab, ch, DEFAULT[m]) + ['']
    (OUT / 'chosen_baselines.json').write_text(json.dumps(chosen, indent=1))
    write_section('Baselines', ['κ: class-K gain of the CBF rows the method runs with; margin: the method keeps '
                                'ρ(1 + margin), scored against the true ρ. Tan: k0 and the width of sat in the Eq. 26 '
                                'law (published 0.1). Risk ratio: c as a multiple of its default for that κ (75 at κ = 2).',
                                ''] + L)
    print((OUT / 'tuning.md').read_text(), flush=True)


def stage_ours(workers):
    pts = [dict(OURS0)] + [dict(OURS0, **{a: v}) for a, vs in OURS_AXES.items() for v in vs]
    execute([(c, 'ours', p, s) for p in pts for c in CELLS for s in SEEDS], workers)
    rows = load()
    L, best = [], dict(OURS0)
    for a, vs in OURS_AXES.items():
        G = [dict(OURS0)] + [dict(OURS0, **{a: v}) for v in vs]
        ch, tab = select(rows, 'ours', G, OURS0)
        best[a] = ch[a]
        L += [f'### axis {a}', ''] + table(tab, ch, OURS0) + ['']
    if best != OURS0:
        execute([(c, 'ours', best, s) for c in CELLS for s in SEEDS], workers)
        rows = load()
        ch, tab = select(rows, 'ours', [dict(OURS0), best], OURS0)
        L += ['### combined coordinate-wise choice vs current', ''] + table(tab, ch, OURS0) + ['']
        best = ch
    # final choice: the same rule over every point evaluated (current, single-axis changes, combination), so a
    # single-axis change that beats both the current point and the combination is not lost
    allpts = pts + ([best] if best not in pts else [])
    ch, tab = select(rows, 'ours', allpts, OURS0)
    L += ['### final choice: rule over all evaluated points', ''] + table(tab, ch, OURS0) + ['']
    best = ch
    (OUT / 'chosen_ours.json').write_text(json.dumps(best, indent=1))
    cb = cbar_of(rows, best, CELLS, SEEDS)
    execute([(c, 'beta', dict(best, W0=w, cbar=cb[c]), s) for w in W0S for c in CELLS for s in SEEDS], workers)
    rows = load()
    # centred beta: lowest W std/mean among W0 whose violation score is not worse than the chosen point (+ tolerance)
    base = select(rows, 'ours', [best], best)[1][0]
    bt = []
    for w in W0S:
        R = [r for r in rows if r['method'] == 'beta' and r['params'].get('W0') == w and r['cell'] in CELLS
             and all(r['params'].get(k) == v for k, v in best.items())]
        v = np.array([(0 if not np.isfinite(r['viol_ext']) else 100 * r['viol_ext']) + 100 * r['viol_team'] for r in R])
        bt.append((w, len(R), v.mean(), v.std(ddof=1) / np.sqrt(len(v)), np.mean([r['W_cv'] for r in R]),
                   np.mean([r['cost'] for r in R]), v.mean() <= base[2] + max(base[3], 0.2)))
    ok = [t for t in bt if t[-1]]
    w_ch = min(ok, key=lambda t: t[4])[0] if ok else None
    (OUT / 'chosen_beta.json').write_text(json.dumps(dict(best, W0=w_ch, beta_max=8.0, cbar_tuning=cb), indent=1))
    L += ['### centred β on the chosen point', '', 'c̄ per cell (tuning seeds, chosen point): ' +
          ', '.join(f'{c} {v:.4f}' for c, v in cb.items()) + '. β_max = 8.', '',
          f'Chosen point (no β): violation score {base[2]:.2f} ± {base[3]:.2f}, W std/mean {base[8]:.3f}, cost {base[5]:.3f}.', '',
          '| W0 | n | violation score (pp) | W std/mean | cost | not worse in violation |', '|---|---|---|---|---|---|']
    L += [f'| {w:g}{" **(chosen)**" if w == w_ch else ""} | {n} | {m:.2f} ± {s:.2f} | {cv:.3f} | {c:.3f} | {"yes" if ok_ else "no"} |'
          for w, n, m, s, cv, c, ok_ in bt]
    write_section('Ours', [f'Current point: {fmt_p(OURS0)} (mutual law, default step 1/(2k_e)). Each axis varied with '
                           'the others at the current point; the per-axis choices are then combined and checked against '
                           'the current point with the same rule. Centred β: W0 chosen by the lowest W std/mean among '
                           'values whose violation score is within max(1 s.e., 0.2 pp) of the chosen point.', ''] + L)
    print((OUT / 'tuning.md').read_text().split('\n## Ours\n')[1], flush=True)


def stage_oneseed(workers):
    tuned = json.loads((OUT / 'chosen_baselines.json').read_text())
    ours_t = json.loads((OUT / 'chosen_ours.json').read_text())
    beta_t = json.loads((OUT / 'chosen_beta.json').read_text())
    confs = []
    for m in GRIDS:
        confs.append((f'{m} (default)', m, DEFAULT[m]))
        confs.append((f'{m} (tuned)', m, tuned[m]))
    for e in (0.1, 0.2, 0.3):
        confs.append((f'Ours current, ε = {e:g}', 'ours', dict(OURS0, eps=e)))
    for e in (0.1, 0.2, 0.3):
        confs.append((f'Ours tuned, ε = {e:g}', 'ours', dict(ours_t, eps=e)))
    execute([(c, m, p, 0) for _, m, p in confs for c in GRID2X3], workers)
    rows = load()
    cb = {c: next(r['cost'] for r in rows if r['method'] == 'ours' and r['cell'] == c and r['seed'] == 0
                  and r['params'] == dict(ours_t, eps=0.1)) for c in GRID2X3}
    W0s = sorted({beta_t['W0'], 2.1, 4.22})          # both candidates on the tuned point (decision 2026-11-13)
    bconf = {w: dict(ours_t, eps=0.1, W0=w, beta_max=8.0) for w in W0s}
    execute([(c, 'beta', dict(bconf[w], cbar=cb[c]), 0) for w in W0s for c in GRID2X3], workers)
    rows = load()
    confs += [(f'Ours tuned + centred β (W0 = {w:g})', 'beta', w) for w in W0s]
    L = ['# One seed', '', 'Seed 0, 120 s, every cell and method. Defaults vs tuned settings (results/tuning/tuning.md). '
         'Violation: % of time with some pair closer than 0.95ρ (true ρ). Centred β: c̄ per cell from the tuned ε = 0.1 run '
         'of that cell (this seed): ' + ', '.join(f'{c} {v:.4f}' for c, v in cb.items()) + '.', '']
    for c in GRID2X3:
        L += [f'## {c}', '', '| method | setting | cost | viol. outsiders (%) | viol. team (%) | min dist. outsiders | '
              'min dist. team | W std/mean |', '|---|---|---|---|---|---|---|---|']
        for name, m, p in confs:
            if m == 'beta':
                p = dict(bconf[p], cbar=cb[c])
            r = next((r for r in rows if r['method'] == m and r['cell'] == c and r['seed'] == 0 and r['params'] == p), None)
            if r is None:
                continue
            e0 = c.endswith('E0')
            ve = '–' if e0 else f"{100 * r['viol_ext']:.2f}"
            de = '–' if e0 else f"{r['min_dist_ext']:.2f}"
            L.append(f"| {name} | {fmt_p(p) if m not in ('ours', 'beta') else ''} | {r['cost']:.3f} | {ve} | "
                     f"{100 * r['viol_team']:.2f} | {de} | {r['min_dist_team']:.2f} | {r['W_cv']:.3f} |")
        L.append('')
    (OUT / 'one_seed.md').write_text('\n'.join(L) + '\n')
    print('\n'.join(L), flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=('baselines', 'ours', 'oneseed'))
    ap.add_argument('--workers', type=int, default=11)
    a = ap.parse_args()
    dict(baselines=stage_baselines, ours=stage_ours, oneseed=stage_oneseed)[a.stage](a.workers)
