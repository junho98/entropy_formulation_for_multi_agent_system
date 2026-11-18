"""Main 2x3 grid with target_sep 1.5: six cells (+ts1.5), seeds 0-23, 120 s; then 600 s x 12 seeds (Ours eps 0.1 vs
centred beta W0 4.22). Rows -> results/grid2x3/runs.jsonl and results/grid2x3/horizon.jsonl (resumable).

Order: Ours eps 0.1 (gives c-bar), then centred beta (W0 4.22, 2.1), Ours no_cover eps 0.1, Ours eps 0.2/0.3, tuned
baselines and Tan, then default baselines, then the horizon runs.
Logging (2026-11-15): Ours eps 0.1, beta W0 4.22 and Ours no_cover run with log_contacts (read-only). Every logged run
writes per-contact aggregates to results/grid2x3/contacts/; seeds 0-5 also write the per-step contact log to
results/grid2x3/clog_main/. Each row carries info_cost = sum lam U / (N K). Files are written before the row, so a
restart reruns any run whose row is missing.
c-bar per cell = fleet-mean work rate of that cell's Ours eps 0.1 runs over the 24 seeds (mean of mean_i W_i(120)/120).

    python scripts/run_grid2x3_ts.py [--workers 11] [--phase main|defaults|horizon|all]
"""
import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_tuning as T                                                    # noqa: E402
from info_cost_seed0 import FIELDS                                        # noqa: E402
from mas_benchmark.analyzers import AgreementGap, Cost, Liveness, PriceImbalance, Safety   # noqa: E402
from mas_benchmark.configs import evaluate                                # noqa: E402
from mas_benchmark.scenarios import GRID2X3                               # noqa: E402

OUT = Path(__file__).resolve().parents[1] / 'results' / 'grid2x3'
RUNS, HZ = OUT / 'runs.jsonl', OUT / 'horizon.jsonl'
TS = '+ts1.5'
CELLS = [c + TS for c in GRID2X3]
SEEDS, SEEDS_H = list(range(24)), list(range(12))
T_AT = (20, 40, 60, 80, 100, 120, 240, 360, 480, 600)
OURS = dict(T.OURS0)                                                     # window 50, ke 20, delta 0.05, w0 0.97
TUNED = {'oracle': dict(kappa=16.0, margin=0.0), 'reciprocal': dict(kappa=16.0, margin=0.2),
         'pcca': dict(kappa=1.0, margin=0.2), 'risk_ratio': dict(c_scale=2.0, kappa=4.0)}
W0S = (4.22, 2.1)
CONTACTS, CLOG = OUT / 'contacts', OUT / 'clog_main'
FULL_SEEDS = range(6)


def wstats(W):
    W = np.asarray(W, float)
    return dict(W_cv=float(W.std() / W.mean()), jain=float(W.sum() ** 2 / (len(W) * np.sum(W ** 2))),
                W_range=float(W.max() - W.min()))


def run(conf, cell, method, params, seed, horizon):
    t0 = time.time()
    log = evaluate(cell, method, seed, horizon, **params)
    f = 0.5 * log.weights[None] * np.sum((log.u - log.u_nom) ** 2, axis=2) * log.dt
    cum = np.cumsum(f, axis=0)
    slack = [np.sum(inf.get('slack', 0.0)) for inf in log.info]
    row = dict(conf=conf, cell=cell, method=method, params=params, seed=seed, horizon=horizon,
               wall_s=round(time.time() - t0, 1), W=[float(w) for w in cum[-1]], **wstats(cum[-1]),
               slack_frac=float(np.mean(np.array(slack) > 1e-6)), **Cost()(log), **Safety()(log), **Liveness()(log))
    if horizon > 120:
        row['at'] = {str(t): wstats(cum[int(round(t / log.dt)) - 1]) for t in T_AT if t <= horizon}
    elif method in ('ours', 'beta'):
        row.update(**AgreementGap()(log), **PriceImbalance()(log))
    if params.get('log_contacts'):
        row.update(save_contacts(log, f'{cell}_{conf}_seed{seed}', seed in FULL_SEEDS))
    return row


def savez(path, arr):
    tmp = path.with_name(path.stem + '.tmp.npz')
    np.savez_compressed(tmp, **arr)
    tmp.replace(path)


def save_contacts(log, name, full):
    """Per-contact aggregates (one row per (i, track, t0)): duration, constrained share (lam > 0), mean U, mean lam U,
    final r, final belief weights; with full, the per-step log as in info_cost_seed0. -> row fields."""
    tracks = np.asarray(log.meta['tracks'])
    body = np.empty_like(tracks); body[tracks] = np.arange(len(tracks))
    rows = [dict(c, t=t, k=int(body[c['track']]), w_inf=c['w'][-1])
            for t, inf in zip(log.t, log.info) for c in inf.get('clog', [])]
    N, K = log.x.shape[1], len(log.t)
    if not rows:
        return dict(info_cost=0.0, n_contacts=0, n_rows=0)
    arr = {k: np.array([r[k] for r in rows], dtype=np.float64) for k in FIELDS}
    for k in ('w', 'm', 'v', 'v_cap'):
        arr[k] = np.array([r[k] for r in rows], dtype=np.float64)
    if full:
        savez(CLOG / f'{name}.npz', arr)
    key = np.stack([arr['i'], arr['k'], arr['t0']], 1)
    _, inv = np.unique(key, axis=0, return_inverse=True)
    inv = inv.ravel()
    order = np.lexsort((arr['t'], inv))                     # by contact, then time
    starts = np.r_[0, np.flatnonzero(np.diff(inv[order])) + 1]
    last = np.r_[starts[1:], len(order)] - 1
    n = np.diff(np.r_[starts, len(order)])
    lamU = arr['lam'] * arr['U']
    red = lambda x: np.add.reduceat(x[order], starts) / n
    agg = dict(i=arr['i'][order][starts], k=arr['k'][order][starts], t0=arr['t0'][order][starts],
               t_first=arr['t'][order][starts], t_last=arr['t'][order][last], n_steps=n.astype(float),
               duration=(arr['t'][order][last] - arr['t'][order][starts] + log.dt),
               constrained=red((arr['lam'] > 0).astype(float)), U_mean=red(arr['U']), lamU_mean=red(lamU),
               lamU_sum=np.add.reduceat(lamU[order], starts), r_final=arr['r'][order][last], w_final=arr['w'][order][last])
    savez(CONTACTS / f'{name}.npz', agg)
    return dict(info_cost=float(lamU.sum() / (N * K)), n_contacts=int(len(starts)), n_rows=len(rows))


def load(path):
    rows = []
    for l in (path.read_text().splitlines() if path.exists() else []):
        try:
            rows.append(json.loads(l))
        except json.JSONDecodeError:                      # a line cut by a restart: that run is redone
            pass
    return rows


def execute(path, jobs, workers):
    have = {(r['conf'], r['cell'], r['seed'], r['horizon']) for r in load(path)}
    jobs = [j for j in jobs if (j[0], j[1], j[4], j[5]) not in have]
    print(f'{len(jobs)} runs -> {path.name}', flush=True)
    if path.exists() and path.stat().st_size and not path.read_bytes().endswith(b'\n'):
        with path.open('a') as fh:
            fh.write('\n')
    with ProcessPoolExecutor(workers) as ex, path.open('a') as fh:
        futs = [ex.submit(run, *j) for j in jobs]
        for n, fut in enumerate(as_completed(futs), 1):
            fh.write(json.dumps(fut.result()) + '\n'); fh.flush()
            if n % 50 == 0 or n == len(futs):
                print(f'{n}/{len(futs)} done', flush=True)


def cbar():
    rows = load(RUNS)
    cb = {}
    for c in CELLS:
        v = [r['cost'] for r in rows if r['conf'] == 'ours_eps0.1' and r['cell'] == c and r['horizon'] == 120.0]
        assert len(v) == len(SEEDS), (c, len(v))
        cb[c] = float(np.mean(v))
    (OUT / 'cbar.json').write_text(json.dumps(cb, indent=1))
    return cb


def main(workers):
    J = lambda conf, m, p, cells=CELLS: [(conf, c, m, p, s, 120.0) for c in cells for s in SEEDS]
    execute(RUNS, J('ours_eps0.1', 'ours', dict(OURS, eps=0.1, log_contacts=True)), workers)
    cb = cbar()
    jobs = []
    for w in W0S:
        lc = dict(log_contacts=True) if w == 4.22 else {}
        jobs += [(f'beta_W0{w:g}', c, 'beta', dict(OURS, eps=0.1, W0=w, cbar=cb[c], **lc), s, 120.0)
                 for c in CELLS for s in SEEDS]
    jobs += J('ours_nocover_eps0.1', 'ours', dict(OURS, eps=0.1, log_contacts=True, no_cover=True))
    for e in (0.2, 0.3):
        jobs += J(f'ours_eps{e:g}', 'ours', dict(OURS, eps=e))
    for m, p in TUNED.items():
        jobs += J(f'{m}_tuned', m, p)
    jobs += J('tan', 'tan', T.DEFAULT['tan'])
    execute(RUNS, jobs, workers)


def defaults(workers):
    execute(RUNS, [(f'{m}_default', c, m, T.DEFAULT[m], s, 120.0) for m in TUNED for c in CELLS for s in SEEDS], workers)


def horizon(workers):
    cb = json.loads((OUT / 'cbar.json').read_text())
    jobs = [('ours_eps0.1', c, 'ours', dict(OURS, eps=0.1), s, 600.0) for c in CELLS for s in SEEDS_H]
    jobs += [('beta_W04.22', c, 'beta', dict(OURS, eps=0.1, W0=4.22, cbar=cb[c]), s, 600.0) for c in CELLS for s in SEEDS_H]
    # fairness growth of two tuned baselines for comparison (2026-11-14), HOM-E8 and HET-E0 only
    jobs += [(f'{m}_tuned', c + TS, m, TUNED[m], s, 600.0) for m in ('oracle', 'pcca') for c in ('HOM-E8', 'HET-E0')
             for s in SEEDS_H]
    execute(HZ, jobs, workers)


def beta02(workers):
    """Centred beta (W0 4.22) at eps 0.2 (2026-11-15); c-bar per cell = mean cost of that cell's Ours eps 0.2 runs over
    the 24 seeds, summed in seed order -> cbar_eps0.2.json."""
    rows = load(RUNS)
    cb = {}
    for c in CELLS:
        v = sorted((r['seed'], r['cost']) for r in rows if r['conf'] == 'ours_eps0.2' and r['cell'] == c and r['horizon'] == 120.0)
        assert len(v) == len(SEEDS), (c, len(v))
        cb[c] = float(np.mean([x for _, x in v]))
    (OUT / 'cbar_eps0.2.json').write_text(json.dumps(cb, indent=1))
    execute(RUNS, [('beta_W04.22_eps0.2', c, 'beta', dict(OURS, eps=0.2, W0=4.22, cbar=cb[c]), s, 120.0)
                   for c in CELLS for s in SEEDS], workers)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=11)
    ap.add_argument('--phase', choices=('main', 'defaults', 'horizon', 'all', 'beta02'), default='all')
    a = ap.parse_args()
    for d in (OUT, CONTACTS, CLOG):
        d.mkdir(parents=True, exist_ok=True)
    if a.phase in ('main', 'all'):
        main(a.workers); print('MAIN DONE', flush=True)
    if a.phase in ('defaults', 'all'):
        defaults(a.workers); print('DEFAULTS DONE', flush=True)
    if a.phase == 'beta02':
        beta02(a.workers); print('BETA02 DONE', flush=True)
    if a.phase in ('horizon', 'all'):
        horizon(a.workers); print('HORIZON DONE', flush=True)
