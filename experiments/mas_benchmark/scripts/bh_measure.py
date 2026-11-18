"""Bretagnolle-Huber measurement (theory discussion, 2026-11-12): P_fairfail + P_ext >= 1/2 exp(-n D).

Per variant (default / iso / region; Ours, eps 0.1 and 0.3), from re-simulated runs (current code, 6 seeds x 120 s):
  D_hat  per tested step decrease of the log-odds ln(w(F)/(1-w(F))) of i's following mass for an outsider, over
         agent-outsider encounters in S4 (tested step: i's share toward the outsider is active, slack s < eps);
  n_T    e-folding time of the 1-vs-3 price imbalance after activation, in steps (S1 isolated encounters; the
         frozen two-agent test is reported alongside);
  P_ext  fraction of S4 agent-outsider encounters (contiguous stays within sensing range) with a distance < 0.95 rho;
  P_fairfail  fraction of S1 isolated team encounters (longer than 0.4 s) whose imbalance is still > 0.1 at the end,
         read as the median over the second half of the encounter without its last 0.2 s (at the very last step one
         price has just switched off, so the imbalance is ~1 by construction; that literal version is P_fairfail_last).

    python scripts/bh_measure.py [--workers 11]  -> results/bh_measure.{jsonl,md}, results/figures/bh_scatter.png
"""
import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from mas_benchmark.analyzers import encounters
from mas_benchmark.analyzers.agreement import body_of
from mas_benchmark.core import Observation, sense, simulate
from mas_benchmark.dynamics import SingleIntegrator
from mas_benchmark.scenarios import make_scenario
from mas_benchmark.solvers import make_solver
from mas_benchmark.specs import PairwiseBarrier

RES = Path(__file__).resolve().parents[1] / 'results'
DT, KE = 0.02, 20.0
VARIANTS = {'default': 'ours_eps{e}', 'iso': 'ours_eps{e}_mutual_region_iso', 'region': 'ours_eps{e}_mutual_region'}
EPS = ['0.1', '0.3']


def s4_run(solver, seed, eps):
    log = simulate(make_scenario('S4'), SingleIntegrator(), PairwiseBarrier(), make_solver(solver), 120.0, DT, seed)
    body = body_of(log); tr = {b: t for t, b in body.items()}
    N, E = log.x.shape[1], log.ext_x.shape[1]
    D = np.linalg.norm(log.x[:, :, None] - log.ext_x[:, None], axis=3)          # (K, N, E)
    out = []
    for i in range(N):
        for e in range(E):
            inside = D[:, i, e] <= 5.0
            t = 0
            while t < len(inside):
                if not inside[t]:
                    t += 1; continue
                s = t
                while t < len(inside) and inside[t]:
                    t += 1
                key = (i, tr[N + e])
                w = np.array([log.info[k]['follow'].get(key, np.nan) for k in range(s, t)])
                mu = np.array([log.info[k]['mu'].get(key, 0.0) for k in range(s, t)])
                tested = mu > 0.0                                   # share active: slack < eps
                out.append(dict(violated=bool((D[s:t, i, e] < 0.95).any()), w=w.tolist(), tested=tested.tolist()))
    return dict(kind='S4', solver=solver, seed=seed, eps=eps, enc=out)


def s1_run(solver, seed, eps):
    log = simulate(make_scenario('S1'), SingleIntegrator(), PairwiseBarrier(), make_solver(solver), 120.0, DT, seed)
    w = log.weights
    out = []
    for e in encounters(log):
        imb = np.abs(e['mu_i'] - e['mu_k']) / (e['mu_i'] + e['mu_k'])
        out.append(dict(diff=bool(w[e['i']] != w[e['k']]), imb=imb.tolist()))
    return dict(kind='S1', solver=solver, seed=seed, eps=eps, enc=out)


def job(kind, solver, seed, eps):
    return (s4_run if kind == 'S4' else s1_run)(solver, seed, eps)


def d_hat(encs, min_tested=5):
    """Mean per-tested-step decrease of the log-odds of w(F) over encounters with enough tested steps."""
    slopes, frac_t, n_t = [], [], []
    for e in encs:
        w = np.clip(np.array(e['w'], float), 1e-12, 1 - 1e-12)
        t = np.array(e['tested'], bool)
        ok = ~np.isnan(w)
        frac_t.append(t[ok].mean() if ok.any() else 0.0)
        if t[ok].sum() < min_tested:
            continue
        L = np.log(w[ok] / (1 - w[ok]))
        c = np.cumsum(t[ok])
        sel = t[ok]
        if np.ptp(c[sel]) == 0:
            continue
        slopes.append(-np.polyfit(c[sel], L[sel], 1)[0]); n_t.append(t[ok].sum())
    return (float(np.mean(slopes)) if slopes else np.nan, float(np.mean(frac_t)) if frac_t else np.nan,
            len(slopes), float(np.mean(n_t)) if n_t else np.nan)


def e_fold(encs, horizon=50):
    """Pooled e-folding time (steps) of the 1-vs-3 imbalance after activation: fit ln(mean imbalance) against the
    step index over the first `horizon` steps, using diff-weight encounters at least that long."""
    curves = [np.array(e['imb'][:horizon]) for e in encs if e['diff'] and len(e['imb']) >= horizon]
    if len(curves) < 3:
        return np.nan, len(curves)
    m = np.mean(curves, axis=0)
    slope = np.polyfit(np.arange(horizon), np.log(np.maximum(m, 1e-12)), 1)[0]
    return (float(-1.0 / slope) if slope < 0 else np.inf), len(curves)


def frozen_e_fold(solver):
    dyn, spec = SingleIntegrator(), PairwiseBarrier()
    th = make_solver(solver); th.reset(type('S', (), {'n_agents': 2})(), dyn, spec, DT)
    x = np.array([[0.0, 0.0], [1.4, 0.0]]); u0 = np.array([[1.0, 0.0], [-1.0, 0.0]])
    U = np.zeros((2, 2)); Z = np.zeros((0, 2)); imb = []
    for _ in range(400):
        obs = Observation(0.0, x, u0, np.array([1.0, 3.0]), sense(x, U, Z, Z, dyn, spec), Z, Z, 1.2)
        U, inf = th.act(obs)
        m = list(inf['mu'].values()); imb.append(abs(m[0] - m[1]) / (m[0] + m[1] + 1e-12))
    imb = np.array(imb)
    below = np.where(imb < imb[0] / np.e)[0]
    return float(below[0]) if len(below) else np.inf


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=11)
    ap.add_argument('--seeds', nargs='+', type=int, default=list(range(6)))
    args = ap.parse_args()
    jobs = [(k, VARIANTS[v].format(e=e), s, e) for v in VARIANTS for e in EPS for k in ('S4', 'S1') for s in args.seeds]
    with ProcessPoolExecutor(args.workers) as ex:
        res = list(ex.map(job, *zip(*jobs)))
    rows = []
    for v, pat in VARIANTS.items():
        for e in EPS:
            name = pat.format(e=e)
            s4 = [enc for r in res if r['kind'] == 'S4' and r['solver'] == name for enc in r['enc']]
            s1 = [enc for r in res if r['kind'] == 'S1' and r['solver'] == name for enc in r['enc']]
            D, frac, n_d, n_tested = d_hat(s4)
            T, n_curves = e_fold(s1)
            Tf = frozen_e_fold(name)
            P_ext = float(np.mean([enc['violated'] for enc in s4])) if s4 else np.nan
            P_ff_last = float(np.mean([enc['imb'][-1] > 0.1 for enc in s1])) if s1 else np.nan
            long_ = [np.array(enc['imb']) for enc in s1 if len(enc['imb']) > 20]
            P_ff = float(np.mean([np.median(c[len(c) // 2:-10]) > 0.1 for c in long_])) if long_ else np.nan
            rows.append(dict(variant=v, eps=e, solver=name, D_hat=D, tested_frac=frac, n_enc_D=n_d, mean_tested=n_tested,
                             n_T=T, n_T_curves=n_curves, n_T_frozen=Tf, P_ext=P_ext, n_ext_enc=len(s4),
                             P_fairfail=P_ff, P_fairfail_last=P_ff_last, n_team_enc=len(s1), n_team_long=len(long_)))
    for r in rows:
        r['nD'] = r['n_T'] * r['D_hat']
        r['nD_frozen'] = r['n_T_frozen'] * r['D_hat']
        r['sum'] = r['P_fairfail'] + r['P_ext']
        r['bound'] = 0.5 * np.exp(-r['nD'])
        r['bound_frozen'] = 0.5 * np.exp(-r['nD_frozen'])
    (RES / 'bh_measure.jsonl').write_text('\n'.join(json.dumps(r) for r in rows) + '\n')
    keys = ['D_hat', 'tested_frac', 'n_T', 'n_T_frozen', 'nD', 'nD_frozen', 'P_fairfail', 'P_fairfail_last', 'P_ext', 'sum',
            'bound', 'bound_frozen']
    lines = ['# Bretagnolle-Huber measurement: P_fairfail + P_ext >= 1/2 exp(-n_T D)', '',
             'D_hat: per tested step decrease of the log-odds of w(F) for outsiders (S4). n_T: e-folding of the '
             '1-vs-3 imbalance in steps (S1 isolated encounters; frozen two-agent test alongside). '
             'P_ext: S4 agent-outsider encounters with a violation. P_fairfail: S1 isolated encounters ending with '
             'imbalance > 0.1. Re-simulated with the current code, 6 seeds x 120 s.', '',
             '| variant | eps | ' + ' | '.join(keys) + ' |', '|---|---|' + '---|' * len(keys)]
    for r in rows:
        lines.append(f"| {r['variant']} | {r['eps']} | " + ' | '.join(f'{r[k]:.3g}' for k in keys) + ' |')
    lines += ['', 'Counts: ' + '; '.join(f"{r['variant']}/{r['eps']}: D from {r['n_enc_D']} enc (mean {r['mean_tested']:.0f} tested steps), "
                                          f"n_T from {r['n_T_curves']} curves, {r['n_ext_enc']} outsider enc, {r['n_team_enc']} team enc ({r['n_team_long']} > 0.4 s)"
                                          for r in rows)]
    (RES / 'bh_measure.md').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(5.5, 4))
    xs = np.linspace(0, max([r['nD'] for r in rows if np.isfinite(r['nD'])] + [r['nD_frozen'] for r in rows if np.isfinite(r['nD_frozen'])] + [1.0]) * 1.1, 200)
    ax.plot(xs, 0.5 * np.exp(-xs), 'k--', label=r'$\frac{1}{2}e^{-x}$')
    for r in rows:
        for x, mk, lab in [(r['nD'], 'o', 'closed-loop n_T'), (r['nD_frozen'], 's', 'frozen n_T')]:
            if np.isfinite(x):
                ax.scatter(x, r['sum'], marker=mk)
                ax.annotate(f"{r['variant']} ε{r['eps']}" + ('' if mk == 'o' else ' (frozen)'), (x, r['sum']), fontsize=7,
                            xytext=(3, 3), textcoords='offset points')
    ax.set_xlabel(r'$n_T \hat D$')
    ax.set_ylabel(r'$P_{fairfail} + P_{ext}$')
    ax.legend(fontsize=8)
    fig.tight_layout()
    (RES / 'figures').mkdir(exist_ok=True)
    fig.savefig(RES / 'figures' / 'bh_scatter.png', dpi=150)
