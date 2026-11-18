"""E0 deadlock check: Ours current (window 50) and tuned (window 25) at eps 0.1/0.2/0.3 on HOM-E0 and HET-E0, seeds 0-11,
120 s; deadlock = some agent stopped (|u| < 0.15) for more than 10 s in a row. Then a trace diagnosis of deadlocked runs.

    python scripts/e0_deadlock.py [--workers 11]   -> appends "E0 deadlock check" to results/tuning/tuning.md
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_tuning as T                                                    # noqa: E402
from mas_benchmark.configs import evaluate                                # noqa: E402

CELLS = ('HOM-E0', 'HET-E0')
WIN = {'current (window 50)': 50, 'tuned (window 25)': 25}
EPS = (0.1, 0.2, 0.3)
SEEDS = list(range(12))
DEAD = 10.0


def params(win, eps):
    return dict(T.OURS0, window=win, eps=eps)


def stops(stopped, dt):
    """-> list of (agent, start step, end step) of every run of stopped steps, longest first."""
    out = []
    for i, col in enumerate(stopped.T):
        s = None
        for k, v in enumerate(list(col) + [False]):
            if v and s is None:
                s = k
            elif not v and s is not None:
                out.append((i, s, k)); s = None
    return sorted(out, key=lambda r: r[1] - r[2])


def diagnose(cell, win, eps, seed):
    log = evaluate(cell, 'ours', seed, **params(win, eps))
    dt, N = log.dt, log.x.shape[1]
    stopped = np.linalg.norm(log.u, axis=2) < 0.15
    runs = [r for r in stops(stopped, dt) if (r[2] - r[1]) * dt > DEAD]
    tracks = np.asarray(log.meta['tracks'])
    body = np.empty_like(tracks); body[tracks] = np.arange(len(tracks))
    L = [f'**{cell}, {[k for k, v in WIN.items() if v == win][0]}, ε = {eps:g}, seed {seed}**', '']
    if not runs:
        return L + ['no stop longer than 10 s on rerun', '']
    i0, a, b = runs[0]
    stuck = sorted({i for i, s, e in runs if s < b and e > a})
    L.append(f'Longest stop: agent {i0}, t = {a * dt:.1f}–{b * dt:.1f} s ({(b - a) * dt:.1f} s'
             + (', ends before 120 s' if b < len(log.t) else ', still stopped at 120 s') + f'). Agents stopped > 10 s overlapping it: {stuck}.')
    k = (a + b) // 2
    p = log.x[k]
    L.append(f'At t = {k * dt:.1f} s (middle of the stop):')
    L.append('')
    L.append('| agent | w | |p| (circle 6, wall 7) | |u| | |u0| | contacts (agent: dist, λ_i, λ̂_k, r_ik, follow) |')
    L.append('|---|---|---|---|---|---|')
    inf = log.info[k]
    involved = set(stuck)
    for i in stuck:
        for (j, t), lam in inf.get('mu', {}).items():
            if j == i and body[t] < N:
                involved.add(int(body[t]))
    for i in sorted(involved):
        cs = []
        for (j, t), lam in inf.get('mu', {}).items():
            if j != i:
                continue
            kb = int(body[t])
            if kb >= N:
                continue
            d = np.linalg.norm(p[i] - p[kb])
            cs.append(f"{kb}: {d:.2f}, {lam:.2f}, {inf['lam_hat'].get((i, t), np.nan):.2f}, "
                      f"{inf['r'].get((i, t), np.nan):+.2f}, {inf['follow'].get((i, t), np.nan):.2f}")
        L.append(f'| {i}{" (stuck)" if i in stuck else ""} | {log.weights[i]:g} | {np.linalg.norm(p[i]):.2f} | '
                 f'{np.linalg.norm(log.u[k, i]):.2f} | {np.linalg.norm(log.u_nom[k, i]):.2f} | {"; ".join(cs) or "–"} |')
    # geometry of the stuck agents: nominal directions toward each other?
    geo = []
    for x in stuck:
        for y in stuck:
            if x < y:
                d = p[y] - p[x]; d /= np.linalg.norm(d)
                geo.append(f'{x}–{y}: dist {np.linalg.norm(p[y] - p[x]):.2f}, u0_{x}·d̂ {log.u_nom[k, x] @ d:+.2f}, '
                           f'u0_{y}·(−d̂) {-(log.u_nom[k, y] @ d):+.2f}, weights {log.weights[x]:g}/{log.weights[y]:g}')
    L += ['', 'Pairs among stuck agents (u0·d̂ > 0: nominal heads toward the other): ' + ('; '.join(geo) or '–'), '']
    return L


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=11)
    a = ap.parse_args()
    jobs = [(c, 'ours', params(w, e), s) for c in CELLS for w in WIN.values() for e in EPS for s in SEEDS]
    T.execute(jobs, a.workers)
    rows = T.load()
    L = ['Ours, mutual law, ε ∈ {0.1, 0.2, 0.3}, current (window 50) and tuned (window 25); seeds 0–11 × 120 s. Stopped: '
         '|u_i| < 0.15. Deadlock: some agent stopped for more than 10 s in a row. Mean ± s.e. over seeds.', '',
         '| cell | setting | ε | deadlocked seeds | longest stop (s, median / max) | stop fraction | cost | W std/mean |',
         '|---|---|---|---|---|---|---|---|']
    dead = []
    for c in CELLS:
        for name, w in WIN.items():
            for e in EPS:
                pk = params(w, e)
                R = [r for r in rows if r['method'] == 'ours' and r['cell'] == c and r['params'] == pk and r['seed'] in SEEDS]
                ls = np.array([r['longest_stop_s'] for r in R])
                dead += [(c, w, e, r['seed'], r['longest_stop_s']) for r in R if r['longest_stop_s'] > DEAD]
                f = lambda q, nd=3: f"{np.mean([r[q] for r in R]):.{nd}f} ± {np.std([r[q] for r in R], ddof=1) / np.sqrt(len(R)):.{nd}f}"
                L.append(f'| {c} | {name} | {e:g} | {int((ls > DEAD).sum())}/{len(R)} '
                         f'({", ".join(str(r["seed"]) for r in R if r["longest_stop_s"] > DEAD) or "–"}) | '
                         f'{np.median(ls):.1f} / {ls.max():.1f} | {f("stop_frac")} | {f("cost")} | {f("W_cv")} |')
    old = [json.loads(l) for l in (T.OUT.parent / 'final_mutual' / 'grid.jsonl').read_text().splitlines()]
    L += ['', 'Old S1 final grid (= HET-E0, window 50, seeds 0–5): longest stop per seed (s):', '']
    for e in EPS:
        R = sorted((r for r in old if r['scenario'] == 'S1' and r['solver'] == f'ours_eps{e:g}_mutual'), key=lambda r: r['seed'])
        L.append(f'- ε = {e:g}: ' + ', '.join(f"seed {r['seed']} {r['longest_stop_s']:.1f}" for r in R)
                 + f"; cost {np.mean([r['cost'] for r in R]):.3f}")
    L += ['', '### Traces', '']
    dead.sort(key=lambda d: -d[4])
    picks = []
    for d in dead:                     # two runs from different settings / cells where possible
        if not picks or (d[0], d[1], d[2]) != picks[0][:3]:
            picks.append(d)
        if len(picks) == 2:
            break
    for c, w, e, s, _ in picks:
        L += diagnose(c, w, e, s)
    T.write_section('E0 deadlock check', L)
    print('\n'.join(L), flush=True)
