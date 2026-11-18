"""Internal: does the grid follow from the model? (results/grid2x3/model_check_note.md)

The grid logs keep neither the nominal inputs nor the full local state, so Ours eps 0.1 (with contact logging, which is
read-only) is rerun for seeds 0-5 in all six cells, keeping positions, nominal inputs and the contact log; each rerun's
cost is checked against its grid row. Item 2 also uses the per-contact summaries of all 24 seeds (results/grid2x3/contacts).

    python scripts/model_check.py record     # reruns -> results/grid2x3/diag/model_check/*.npz
    python scripts/model_check.py analyse    # prints the four items
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_grid2x3_ts as G                                                # noqa: E402
from mas_benchmark.analyzers import Cost                                  # noqa: E402
from mas_benchmark.configs import RHO, build, evaluate                    # noqa: E402
from mas_benchmark.utils.qp import solve_qp                               # noqa: E402

D = G.OUT / 'diag' / 'model_check'
CELLS = ['HOM-E0', 'HET-E0', 'HOM-E4', 'HOM-E8', 'HET-E4', 'HET-E8']
SEEDS = range(6)
F = ('t', 'i', 'k', 'lam', 'U', 'r', 's', 'alpha', 'h')


def record(cell, seed):
    log = evaluate(cell + '+ts1.5', 'ours', seed, 120.0, **dict(G.OURS, eps=0.1, log_contacts=True))
    tracks = np.asarray(log.meta['tracks'])
    body = np.empty_like(tracks); body[tracks] = np.arange(len(tracks))
    rows = [dict(c, t=t, k=int(body[c['track']])) for t, inf in zip(log.t, log.info) for c in inf.get('clog', [])]
    arr = {q: np.array([r[q] for r in rows], float) for q in F}
    np.savez_compressed(D / f'{cell}_seed{seed}.npz', x=log.x[..., :2], q=log.ext_x[..., :2], u_nom=log.u_nom,
                        u=log.u, w=log.weights, v_env=0.0, **{'c_' + q: v for q, v in arr.items()})
    return cell, seed, Cost()(log)['cost']


def load(cell, seed):
    z = np.load(D / f'{cell}_seed{seed}.npz')
    return z, {q: z['c_' + q] for q in F}


if __name__ == '__main__' and sys.argv[1] == 'record':
    D.mkdir(parents=True, exist_ok=True)
    grid = {(r['cell'][:6], r['seed']): r['cost'] for r in G.load(G.RUNS) if r['conf'] == 'ours_eps0.1'}
    jobs = [(c, s) for c in CELLS for s in SEEDS if not (D / f'{c}_seed{s}.npz').exists()]
    with ProcessPoolExecutor(8) as ex:
        for c, s, cost in ex.map(record, *zip(*jobs)) if jobs else ():
            print(c, s, 'identical' if cost == grid[(c, s)] else f'DIFFERENT {cost} {grid[(c, s)]}', flush=True)


# ---- analysis --------------------------------------------------------------------------------------------------------
DT, KE, EPS, M, KAPPA = 0.02, 20.0, 0.1, 1000.0, 2.0


def ptype(w, i, k):
    return '-'.join(str(int(x)) for x in sorted((w[i], w[k])))


def item1(cell):
    """Team pair-steps at which either side's layer row is active (lam > 0), each unordered pair once per step.
    c_i0 = g_i(u0_i) = -2 d.u0_i - kappa h / 2 (d = p_i - p_k), c_k0 likewise from k's side; 'norm' divides both by
    alpha = 2|d| (speed units), which makes w (c0)_+^2 / 2 the cost of meeting the row alone."""
    out = {}
    for s in SEEDS:
        z, c = load(cell, s)
        x, u0, w = z['x'], z['u_nom'], z['w']
        N = x.shape[1]
        k_ = np.round(c['t'] / DT).astype(int)
        m = (c['k'] < N) & (c['lam'] > 0)
        keys = {(int(kk), int(min(i, b)), int(max(i, b))) for kk, i, b in zip(k_[m], c['i'][m], c['k'][m])}
        for kk, i, b in keys:
            d = x[kk, i] - x[kk, b]
            h = d @ d - RHO ** 2
            ci, ck = -2 * d @ u0[kk, i] - 0.5 * KAPPA * h, 2 * d @ u0[kk, b] - 0.5 * KAPPA * h
            out.setdefault(ptype(w, i, b), []).append((ci, ck, w[i], w[b], 2 * np.linalg.norm(d)))
    res = {}
    for t, v in out.items():
        a = np.array(v)
        ci, ck, wi, wk, al = a.T
        for tag, sc in (('raw', 1.0), ('norm', 1.0 / al)):
            xi, xk = ci * sc, ck * sc
            E1 = np.mean(wi * np.maximum(xi, 0) ** 2 + wk * np.maximum(xk, 0) ** 2)
            E2 = np.mean(np.maximum(xi + xk, 0) ** 2 * wi * wk / (wi + wk))
            res[(t, tag)] = dict(n=len(a), mean_i=xi.mean(), mean_k=xk.mean(), sd=np.std(np.r_[xi, xk]),
                                 corr=np.corrcoef(xi, xk)[0, 1], both_pos=np.mean((xi > 0) & (xk > 0)),
                                 one_pos=np.mean((xi > 0) ^ (xk > 0)), E1=E1, E2=E2, ratio=E1 / E2)
    return res


def contacts_T(cell, conf):
    """Constrained time per team contact (sum of steps with lam > 0, from i's side, i < k), all 24 seeds."""
    T, typ = [], []
    for s in range(24):
        z = np.load(G.OUT / 'contacts' / f'{cell}+ts1.5_{conf}_seed{s}.npz')
        i, k = z['i'].astype(int), z['k'].astype(int)
        w = np.array([1.0, 3.0] * 4) if cell.startswith('HET') else np.ones(8)
        m = (k < 8) & (i < k)
        Tc = (z['n_steps'] * z['constrained'] * DT)[m]
        T += list(Tc); typ += [ptype(w, a, b) for a, b in zip(i[m], k[m])]
    return np.array(T), np.array(typ)


def thermo_qp(w, u0, A, b, rows, eps=EPS):
    """Ours' local QP: min w/2|u-u0|^2 + ke/2 sum p^2 + M sum z, layer g.a u - p <= -(g.b + R + eps), wall
    g.a u - z <= -(g.b + R), input polytope; rows = [(a, b, R)] -> (u, slack s per row, lam = ke p per row)."""
    K, n_u = len(rows), 2
    n = n_u + 2 * K
    P = np.zeros((n, n)); P[:n_u, :n_u] = w * np.eye(n_u); P[n_u:n_u + K, n_u:n_u + K] = KE * np.eye(K)
    q = np.concatenate([-w * u0, np.zeros(K), M * np.ones(K)])
    Gm = [np.hstack([A, np.zeros((len(b), 2 * K))]), np.hstack([np.zeros((2 * K, n_u)), -np.eye(2 * K)])]
    h_ = [b, np.zeros(2 * K)]
    for j, (ga, gb, R) in enumerate(rows):
        lay = np.zeros(n); lay[:n_u], lay[n_u + j] = ga, -1.0
        wal = np.zeros(n); wal[:n_u], wal[n_u + K + j] = ga, -1.0
        Gm += [lay[None], wal[None]]; h_ += [[-(gb + R + eps)], [-(gb + R)]]
    sol, _ = solve_qp(P, q, np.vstack(Gm), np.concatenate(h_))
    u = sol[:n_u]
    s = np.array([-(ga @ u + gb + R) for ga, gb, R in rows])
    return u, s, KE * sol[n_u:n_u + K]


def item3_run(cell, seed):
    """Re-solve each constrained local problem (some lam > 0) with U = 0 (R = r) at the logged state."""
    from mas_benchmark.dynamics import SingleIntegrator
    A, b = SingleIntegrator().input_polytope()
    z, c = load(cell, seed)
    x, q, u0, w = z['x'], z['q'], z['u_nom'], z['w']
    N = x.shape[1]
    P = np.concatenate([x, q], axis=1)
    k_ = np.round(c['t'] / DT).astype(int)
    order = np.lexsort((c['i'], k_))
    key = k_[order] * N + c['i'][order].astype(int)
    starts = np.r_[0, np.flatnonzero(np.diff(key)) + 1, len(order)]
    tot, chk = 0.0, []
    for a0, a1 in zip(starts[:-1], starts[1:]):
        idx = order[a0:a1]
        if not np.any(c['lam'][idx] > 0):
            continue
        kk, i = int(k_[idx[0]]), int(c['i'][idx[0]])
        rows_p, rows_m = [], []
        for j in idx:
            bb = int(c['k'][j]); d = P[kk, i] - P[kk, bb]
            ga, gb = -2 * d, -0.5 * KAPPA * (d @ d - RHO ** 2)
            rows_p.append((ga, gb, c['r'][j] + c['U'][j])); rows_m.append((ga, gb, c['r'][j]))
        _, sp, lp = thermo_qp(w[i], u0[kk, i], A, b, rows_p)
        _, sm, lm = thermo_qp(w[i], u0[kk, i], A, b, rows_m)
        chk.append(np.max(np.abs(lp - c['lam'][idx])))
        tot += np.sum(0.5 * (lp + lm) * np.maximum(c['U'][idx] - sm, 0.0))
    K = x.shape[0]
    return cell, seed, tot / (N * K), float(np.max(chk)) if chk else 0.0, float(np.median(chk)) if chk else 0.0


def item4(cell):
    """Outsider-violation agent-outsider-steps (d < 0.95 rho) on which the agent's local problem has some s < 0, and
    the number K of active rows (lam > 0) given at least one active outsider row."""
    neg, tot, Ks = 0, 0, []
    for s in SEEDS:
        z, c = load(cell, s)
        x, q = z['x'], z['q']
        N = x.shape[1]
        k_ = np.round(c['t'] / DT).astype(int)
        key = k_ * N + c['i'].astype(int)
        has_neg = np.zeros(x.shape[0] * N, bool); np.logical_or.at(has_neg, key, c['s'] < 0)
        act = np.bincount(key, c['lam'] > 0, x.shape[0] * N)
        out_act = np.bincount(key, (c['lam'] > 0) & (c['k'] >= N), x.shape[0] * N)
        Ks += list(act[out_act > 0])
        dist = np.linalg.norm(x[:, :, None] - q[:, None], axis=3)
        kk, ii, _ = np.nonzero(dist < 0.95 * RHO)
        tot += len(kk); neg += int(has_neg[kk * N + ii].sum())
    Ks = np.array(Ks)
    return dict(viol_steps=tot, on_neg_slack=neg / max(tot, 1),
                K_dist={str(v): float(np.mean(Ks == v)) for v in (1, 2, 3)} | {'4+': float(np.mean(Ks >= 4))})


if __name__ == '__main__' and sys.argv[1] == 'analyse':
    print('ITEM 1')
    for cell in ('HOM-E0', 'HET-E0'):
        for (t, tag), r in sorted(item1(cell).items()):
            print(cell, t, tag, json.dumps({k: round(float(v), 4) for k, v in r.items()}))
    print('ITEM 3')
    with ProcessPoolExecutor(6) as ex:
        for r in ex.map(item3_run, *zip(*[(c, s) for c in ('HOM-E4', 'HOM-E8', 'HET-E4', 'HET-E8') for s in SEEDS])):
            print(*r, flush=True)
    print('ITEM 4')
    for cell in ('HOM-E4', 'HOM-E8', 'HET-E4', 'HET-E8'):
        print(cell, json.dumps(item4(cell)))
