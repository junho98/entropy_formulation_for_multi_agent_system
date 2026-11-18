"""Offline test of a public initial agreement r_ik(t0) = g(o_ik), seed 0, Ours eps 0.1, HOM-E0 / HET-E0 (+ts1.5).

Seed 0 is rerun with contact logging because positions, velocities and nominal inputs at contact start are not in the
contact logs (the run is identical to the logged one: same cost). One row per unordered team pair contact (i < k),
r = r_ik from i's side (the mutual law keeps r_ki = -r_ik exactly).

Pair row: g_i(u) = -2 d.u - kappa h/2 with d = p_i - p_k (own share of c_ik = g_i + g_k <= 0). r_ik is the usage
i leaves to k (its own row is g_i(u_i) <= -R_ik, R_ik >= r_ik), so r_ik > 0 means i gives way.
  target 1  r_ik at the last step of the contact
  target 2  mean of r_ik over the last quarter of the contact
  target 3  equal-weight split of the nominal conflict, r* = (g_k(u0_k) - g_i(u0_i))/2 = d.(u0_i + u0_k), from the true
            nominal inputs (private; yardstick only), averaged over the last quarter of the contact
  g1  the same expression with the velocities observed at contact start: g1 = d.(v_i + v_k)
  g2  difference of closing speeds along the line of centres: g2 = c_k - c_i, c_i = -dhat.v_i, c_k = dhat.v_k
      (g1 = |d| g2: same sign, different scale)
  g3  right of way: +1 if k is on i's right (cross(v_i, p_k - p_i) < 0: i gives way), else -1
  g4  g1 at the first step at which either side's layer is reached (lambda_i > 0 or lambda_hat_k > 0), with the
      velocities observed then; falls back to contact start if never constrained (public too, but later)

    python scripts/public_rule_seed0.py
"""
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt                                           # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_tuning as T                                                    # noqa: E402
from mas_benchmark.configs import evaluate                                # noqa: E402
from mas_benchmark.viz import style                                       # noqa: E402

OUT = Path(__file__).resolve().parents[1] / 'results' / 'grid2x3'
CELLS = ('HOM-E0', 'HET-E0')


def contacts(cell):
    log = evaluate(cell + '+ts1.5', 'ours', 0, 120.0, **dict(T.OURS0, eps=0.1, log_contacts=True))
    dt, N = log.dt, log.x.shape[1]
    tracks = np.asarray(log.meta['tracks'])
    body = np.empty_like(tracks); body[tracks] = np.arange(len(tracks))
    C = {}
    for s, inf in enumerate(log.info):
        for c in inf.get('clog', []):
            i, k = c['i'], int(body[c['track']])
            if k >= N:
                continue
            key = (min(i, k), max(i, k), round(c['t0'], 4)) if i < k else None
            if i < k:
                C.setdefault((i, k, round(c['t0'], 4)), []).append((s, c['r'], c['lam'], c['lam_hat']))
    rows = []
    x, u, u0, w = log.x, log.u, log.u_nom, log.weights
    for (i, k, t0), L in C.items():
        L = np.array(L)
        steps = L[:, 0].astype(int)
        s0, s1 = steps[0], steps[-1]
        n = len(steps)
        q = steps[int(0.75 * n):] if n >= 4 else steps
        d = x[:, i] - x[:, k]
        rstar = np.einsum('sj,sj->s', d[q], u0[q, i] + u0[q, k])
        v = lambda s, a: u[s - 1, a] if s > 0 else np.zeros(2)               # velocity observed at step s
        def g1_at(s):
            return float(d[s] @ (v(s, i) + v(s, k)))
        dh = d[s0] / np.linalg.norm(d[s0])
        c_i, c_k = -dh @ v(s0, i), dh @ v(s0, k)
        rel = x[s0, k] - x[s0, i]
        cross = v(s0, i)[0] * rel[1] - v(s0, i)[1] * rel[0]
        # g3 from k's side: k gives way if i is on k's right; antisymmetric only if the two disagree
        cross_k = v(s0, k)[0] * (-rel[1]) - v(s0, k)[1] * (-rel[0])
        g3_i = 1.0 if cross < 0 else -1.0
        g3_k = 1.0 if cross_k < 0 else -1.0                                  # k's own g_ki
        con = np.where((L[:, 2] > 0) | (L[:, 3] > 0))[0]
        s_c = steps[con[0]] if len(con) else s0
        rows.append(dict(cell=cell, i=i, k=k, n=n, w=(w[i], w[k]), t1=L[-1, 1], t2=float(np.mean(L[int(0.75 * n):, 1])),
                         t3=float(np.mean(rstar)), t3_end=float(d[s1] @ (u0[s1, i] + u0[s1, k])), g1=g1_at(s0),
                         g2=float(c_k - c_i), g3=g3_i, g3_sum=g3_i + g3_k, g4=g1_at(s_c), constrained=len(con) > 0,
                         cost=float(np.mean(0.5 * w[None] * np.sum((u - u0) ** 2, axis=2)))))
    return rows


def stats(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < 3 or np.std(x) == 0 or np.std(y) == 0:
        return dict(n=len(x), r=np.nan, R2=np.nan, b=np.nan, R2o=np.nan, bo=np.nan, sign=np.nan)
    r = np.corrcoef(x, y)[0, 1]
    b = np.sum((x - x.mean()) * (y - y.mean())) / np.sum((x - x.mean()) ** 2)
    bo = np.sum(x * y) / np.sum(x * x)
    R2o = 1 - np.sum((y - bo * x) ** 2) / np.sum((y - y.mean()) ** 2)
    nz = (np.abs(y) > 1e-9) & (np.abs(x) > 1e-9)
    return dict(n=len(x), r=r, R2=r ** 2, b=b, R2o=R2o, bo=bo, sign=float(np.mean(np.sign(x[nz]) == np.sign(y[nz]))) if nz.any() else np.nan)


if __name__ == '__main__':
    with ProcessPoolExecutor(2) as ex:
        R = [r for rows in ex.map(contacts, CELLS) for r in rows]
    L = ['# Public initial agreement (offline, seed 0)', '', __doc__.split('Pair row:')[1].split('    python')[0].strip()
         .replace('\n  ', '\n- ').replace('\n      ', ' '), '',
         'Statistics: n contacts; Pearson r and R² (free slope b); R² through the origin (slope b₀; can be negative); sign '
         'agreement on contacts where both are non-zero. Short: under 50 steps. Observations are noiseless in the simulator, '
         'so g1, g2 and g4 computed by i and by k are exactly antisymmetric (d_ki = −d_ik, the velocity sum is symmetric); '
         'g3 is not (distribution below).', '']
    fig, axes = plt.subplots(2, 4, figsize=(15, 7))
    style.use()
    for row, cell in zip(axes, CELLS):
        Rc = [r for r in R if r['cell'] == cell]
        L += [f'## {cell}', '', f"{len(Rc)} team-pair contacts ({sum(r['constrained'] for r in Rc)} with a constrained step); "
              f"median length {np.median([r['n'] for r in Rc]):.0f} steps.", '',
              '| subset | target | variant | n | r | R² (free) | slope | R² (origin) | slope₀ | sign agreement |',
              '|---|---|---|---|---|---|---|---|---|---|']
        subsets = [('all', Rc), ('short (< 50 steps)', [r for r in Rc if r['n'] < 50]), ('long', [r for r in Rc if r['n'] >= 50]),
                   ('constrained contacts', [r for r in Rc if r['constrained']])]
        if cell.startswith('HET'):
            subsets += [(f'w {a:g}–{b:g}', [r for r in Rc if sorted(r['w']) == [a, b]]) for a, b in ((1, 1), (1, 3), (3, 3))]
        for sname, sub in subsets:
            for t, tname in (('t1', 'r at end'), ('t2', 'r, last quarter'), ('t3', 'r* (true nominals)')):
                for g in ('g1', 'g2', 'g3', 'g4'):
                    s = stats([r[g] for r in sub], [r[t] for r in sub])
                    L.append(f"| {sname} | {tname} | {g} | {s['n']} | {s['r']:.2f} | {s['R2']:.2f} | {s['b']:.3g} | "
                             f"{s['R2o']:.2f} | {s['bo']:.3g} | {s['sign']:.2f} |")
        c13 = stats([r['t3'] for r in Rc], [r['t2'] for r in Rc])
        Rcon = [r for r in Rc if r['constrained']]
        c13c = stats([r['t3'] for r in Rcon], [r['t2'] for r in Rcon])
        L += ['', f"Convergence of the exchange: r over the last quarter against r* (true nominals): r = {c13['r']:.2f}, slope "
                  f"{c13['b']:.3g}, median |r − r*| = {np.median([abs(r['t2'] - r['t3']) for r in Rc]):.3g} (median |r*| = "
                  f"{np.median([abs(r['t3']) for r in Rc]):.3g}); constrained contacts only: r = {c13c['r']:.2f}, median |r − r*| = "
                  f"{np.median([abs(r['t2'] - r['t3']) for r in Rcon]):.3g}.",
              '', f"Antisymmetry: g1, g2, g4: g_ik + g_ki = 0 exactly (noiseless observations). g3: g_ik + g_ki = 0 on "
                  f"{np.mean([r['g3_sum'] == 0 for r in Rc]):.2f} of contacts, ±2 (both give way or neither) on the rest.", '']
        for ax, g in zip(row, ('g1', 'g2', 'g3', 'g4')):
            xs = np.array([r[g] for r in Rc]); con = np.array([r['constrained'] for r in Rc])
            ax.scatter(xs[~con], [r['t2'] for r, c in zip(Rc, con) if not c], s=10, color=style.OUTSIDER, alpha=0.6, label='never constrained')
            ax.scatter(xs[con], [r['t2'] for r, c in zip(Rc, con) if c], s=12, color=style.colour('final'), alpha=0.8, label='constrained')
            ax.axhline(0, color=style.INK2, lw=0.6); ax.axvline(0, color=style.INK2, lw=0.6)
            ax.set_title(f'{cell}: {g}'); ax.set_xlabel(g); ax.set_ylabel('r, last quarter')
        row[0].legend(fontsize=7)
    fig.tight_layout()
    style.save(fig, OUT / 'public_rule_seed0')
    plt.close(fig)
    (OUT / 'public_rule_seed0.md').write_text('\n'.join(L) + '\n')
    print('\n'.join(L))
