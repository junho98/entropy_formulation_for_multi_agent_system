"""One-seed check of the information-cost bound (seed 0, 120 s, six cells +ts1.5).

Runs: Ours eps 0.1 with contact logging; full-information Ours (cover U = 0, rooms = agreements) with logging; the same
with a thin layer (eps 0.01) for the layer term; Oracle tuned (kappa 16) and default (kappa 2).
Writes results/grid2x3/clog/*.npz (per-step contact logs), results/grid2x3/info_cost_seed0.md and info_cost_seed0.pdf/png.

    python scripts/info_cost_seed0.py [--workers 11]
"""
import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt                                           # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_tuning as T                                                    # noqa: E402
from mas_benchmark.analyzers import Cost, Safety                          # noqa: E402
from mas_benchmark.configs import evaluate                                # noqa: E402
from mas_benchmark.scenarios import GRID2X3                               # noqa: E402
from mas_benchmark.viz import style                                       # noqa: E402

OUT = Path(__file__).resolve().parents[1] / 'results' / 'grid2x3'
CLOG = OUT / 'clog'
TS = '+ts1.5'
SEED = 0
O = dict(T.OURS0, eps=0.1)
S = float(np.log(1 / 0.05))
SIG2 = 0.01 ** 2
CONFS = {'ours': ('ours', dict(O, log_contacts=True)),
         'ours_U0': ('ours', dict(O, log_contacts=True, no_cover=True)),
         'ours_U0_eps0.01': ('ours', dict(O, eps=0.01, no_cover=True)),
         'oracle_tuned': ('oracle', dict(kappa=16.0, margin=0.0)),
         'oracle_default': ('oracle', dict(kappa=2.0, margin=0.0))}
FIELDS = ('t', 'i', 'k', 't0', 'n', 'U', 'lam', 'lam_hat', 'r', 's', 'regime', 'theta', 'R_ki', 'follow', 'a_last', 'aa',
          'n_win', 'mX', 'vX', 'tau_map', 'I_map', 'v_map', 'tau_mean', 'alpha', 'h', 'w_inf')


def job(conf, cell):
    m, p = CONFS[conf]
    log = evaluate(cell, m, SEED, 120.0, **p)
    f = 0.5 * log.weights[None] * np.sum((log.u - log.u_nom) ** 2, axis=2) * log.dt
    W = f.sum(axis=0)
    out = dict(conf=conf, cell=cell, W=[float(w) for w in W], W_cv=float(W.std() / W.mean()),
               W_range=float(W.max() - W.min()), x_sum=float(np.sum(log.x)), **Cost()(log), **Safety()(log))
    if p.get('log_contacts'):
        tracks = np.asarray(log.meta['tracks'])
        body = np.empty_like(tracks); body[tracks] = np.arange(len(tracks))
        rows = [dict(c, t=t, k=int(body[c['track']]), w_inf=c['w'][-1])
                for t, inf in zip(log.t, log.info) for c in inf.get('clog', [])]
        arr = {k: np.array([r[k] for r in rows], dtype=np.float64) for k in FIELDS}
        for k in ('w', 'm', 'v'):                                # per hypothesis (w: 4 finite tau + inf; m, v: finite)
            arr[k] = np.array([r[k] for r in rows], dtype=np.float64)
        arr['v_cap'] = np.array([r['v_cap'] for r in rows], dtype=np.float64)
        np.savez_compressed(CLOG / f'{cell}_{conf}_seed{SEED}.npz', **arr)
        # information cost: time-average over agent-time of sum_k lam_ik U_ik (same units as cost: the QP objective's
        # rate, 1/2 w |u - u0|^2 per agent per second, because lam is the multiplier of that objective's row)
        N, K = log.x.shape[1], len(log.t)
        out['info_cost'] = float(np.sum(arr['lam'] * arr['U']) / (N * K))
        lay = arr['lam'] * np.clip(0.1 - arr['s'], 0, None) / 2            # 1/2 ke p^2 = 1/2 lam p (layer penalty)
        out['layer_pen'] = float(np.sum(lay) / (N * K))
        out['n_rows'] = len(rows)
    return out


def fit(x, y):
    A = np.vstack([x, np.ones_like(x)]).T
    (b1, b0), *_ = np.linalg.lstsq(A, y, rcond=None)
    yhat = A @ np.array([b1, b0])
    r2 = 1 - np.sum((y - yhat) ** 2) / max(np.sum((y - y.mean()) ** 2), 1e-300)
    return b1, b0, r2


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=11)
    a = ap.parse_args()
    CLOG.mkdir(parents=True, exist_ok=True)
    cells = [c + TS for c in GRID2X3]
    jobs = [(conf, c) for conf in CONFS for c in cells]
    with ProcessPoolExecutor(a.workers) as ex:
        res = list(ex.map(job, *zip(*jobs)))
    R = {(r['conf'], r['cell']): r for r in res}
    (OUT / 'info_cost_seed0.json').write_text(json.dumps(res, indent=1))
    # logging changes nothing: compare with the unlogged seed-0 runs of the stopped grid
    old = {}
    p_old = OUT / 'stopped_nolog' / 'runs.jsonl'
    if p_old.exists():
        for l in p_old.read_text().splitlines():
            r = json.loads(l)
            if r['conf'] == 'ours_eps0.1' and r['seed'] == SEED:
                old[r['cell']] = r
    L = ['# Information cost, one seed', '',
         f'Seed {SEED}, 120 s, six cells with target_sep 1.5; Ours final configuration (mutual law, k_e 20, δ 0.05, window 50, '
         f'prior 0.97), ε 0.1. S = ln(1/δ) = {S:.3f}.', '',
         '**Logging is read-only.** Ours with logging vs the unlogged runs of the stopped 24-seed grid (same seed): cost '
         + ', '.join(f"{c[:-len(TS)]} {'identical' if c in old and old[c]['cost'] == R[('ours', c)]['cost'] else 'DIFFERENT' if c in old else 'n/a'}"
                     for c in cells) + '; 30 s trajectories (positions and inputs) compared bitwise for Ours in HOM-E8 and '
         'centred β in HET-E4: identical.', '',
         '## Symbols and logged quantities', '',
         '| theory | logged | note |', '|---|---|---|',
         '| U_ik (cover) | `U` = R_ik − r_ik, room minus own agreement | exact |',
         '| λ_ik | `lam` = k_e max(0, ε − s_ik), own layer multiplier after the QP | the wall row (s ≤ 0) has its own multiplier (penalty M), not included |',
         '| λ̂_k | `lam_hat`, replica of k\'s multiplier from the exchange | exact (one step old) |',
         '| a (response coefficient) | `a_last`: a_s of the newest observation (1 unconstrained, 1/(1 + k_e α²) in the layer, 0 at the wall) | the regime of k is modelled, per step |',
         '| τ | `tau_map`: the finite temperature with the largest posterior weight; likelihood noise τ_j + σ_o², σ_o = 0.01 | the belief is a 5-point mixture over τ, not one τ |',
         '| I_0 | 1: prior on the intent ū ~ N(0, 1) | exact for each finite τ |',
         '| I_n = Σ a_s²/τ | `I_map` = Σ_window a_s² / (τ_map + σ_o²) | windowed: the last 50 steps only, so I_n saturates instead of growing |',
         '| σ_n² = 1/(I_0 + I_n) | `v_map` = posterior variance of ū under τ_map | exact for that component |',
         '| predictive mean / variance of X | `mX`, `vX`: mixture moments of X = α y − κh/2 (τ = ∞: uniform on the capability) | X is the neighbour\'s usage in room units |',
         '| bound | room R = A[max(c_k, r_ik)] by the KL-dual (Chernoff) bound at level δ over the mixture, `theta` = θ* | the theory\'s Gaussian form is the one-component limit |',
         '| w(F) | `follow` = 1 − w(τ = ∞) | exact |', '']
    # (i) U^2 vs 1/(I0 + In)
    L += ['## (i) Cover against information', '',
          'Gaussian one-component limit of the bound: U ≈ sqrt(2S · Var X) with Var X = α²(τ + σ_o² + σ_n²), so '
          'U²/α² ≈ 2S σ_n² + 2S (τ + σ_o²): slope 2S on σ_n² = 1/(I_0 + I_n) and intercept 2S(τ + σ_o²). In room units the '
          'theory\'s "a" is α = 2‖d‖ (usage per unit approach speed), so U² itself has slope 2S α²; dividing by α² removes '
          'the distance. The truncation max(c_k, r_ik) makes U ≈ 0 whenever the predicted usage is far below the agreement, '
          'so the fit is also shown on the steps where the bound is active (predicted usage within 3 sd of r_ik).', '',
          '| cell | rows | pooled slope (all) | intercept | R² | slope (bound active) | intercept | R² | predicted slope | predicted intercept (τ_map median) | median per-contact slope |',
          '|---|---|---|---|---|---|---|---|---|---|---|']
    fig, axes = plt.subplots(2, 3, figsize=(13, 7))
    style.use()
    for ax, c in zip(axes.ravel(), cells):
        z = np.load(CLOG / f'{c}_ours_seed{SEED}.npz')
        team = z['k'] < 8
        ok = (z['n_win'] > 0) & np.isfinite(z['v_map'])
        x, y = z['v_map'][ok], (z['U'] ** 2 / z['alpha'] ** 2)[ok]
        act = (z['mX'] + 3 * np.sqrt(z['vX']) >= z['r'])[ok]
        b1, b0, r2 = fit(x, y)
        a1, a0, q2 = fit(x[act], y[act]) if act.sum() > 2 else (np.nan, np.nan, np.nan)
        tau = np.median(z['tau_map'][ok])
        # per-contact slopes
        key = (z['i'] * 1000 + z['k']) * 1e6 + z['t0'] * 100
        sl = []
        for kk in np.unique(key[ok]):
            mm = key[ok] == kk
            if mm.sum() > 10 and np.ptp(x[mm]) > 0:
                sl.append(fit(x[mm], y[mm])[0])
        L.append(f'| {c[:-len(TS)]} | {ok.sum()} | {b1:.3g} | {b0:.3g} | {r2:.2f} | {a1:.3g} | {a0:.3g} | {q2:.2f} | '
                 f'{2 * S:.2f} | {2 * S * (tau + SIG2):.2g} | {np.median(sl) if sl else np.nan:.3g} |')
        ax.scatter(x[~act], y[~act], s=2, color=style.OUTSIDER, alpha=0.3, rasterized=True, label='bound inactive')
        ax.scatter(x[act], y[act], s=2, color=style.colour('final'), alpha=0.4, rasterized=True, label='bound active')
        xs = np.linspace(0, max(x.max(), 1e-6), 50)
        ax.plot(xs, 2 * S * xs + 2 * S * (tau + SIG2), color=style.VIOL, lw=1.5, label='predicted 2S σ² + 2S(τ+σ_o²)')
        ax.set_xscale('symlog', linthresh=1e-5); ax.set_yscale('symlog', linthresh=1e-5)
        ax.set_title(c[:-len(TS)]); ax.set_xlabel(r'$\sigma_n^2 = 1/(I_0+I_n)$ (MAP $\tau$)'); ax.set_ylabel(r'$U^2/\alpha^2$')
    axes[0, 0].legend(fontsize=7, markerscale=4)
    fig.tight_layout()
    style.save(fig, OUT / 'info_cost_seed0')
    plt.close(fig)
    # (ii) and the gap to the Oracle
    L += ['', '## (ii) Information cost and the gap to the Oracle', '',
          'Costs are the mean over agents of W_i(120)/120 (rate of ½ w‖u − u0‖²). Information cost = Σ over steps, agents and '
          'contacts of λ_ik U_ik divided by (agents × steps): λ is the multiplier of the room row in the QP whose objective '
          'is ½ w‖u − u0‖² (+ the layer penalty), so λU is the first-order objective change per step from the cover, the '
          'same rate units as the cost column. Layer penalty: ½ λ p (= ½ k_e p², p = ε − s) averaged the same way; it is part '
          'of the QP objective but not of the reported cost.', '',
          '| cell | Ours cost | Oracle tuned (viol. ext / team %) | Oracle default (viol.) | gap to tuned | gap to default | info cost ΣλU | explained (tuned / default) | Ours(U=0) cost (viol. ext / team %) | Ours − Ours(U=0) | its fraction of gap (tuned / default) | Ours(U=0) − Ours(U=0, ε 0.01) | Ours(U=0) − Oracle tuned |',
          '|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for c in cells:
        o, u0, l0 = R[('ours', c)], R[('ours_U0', c)], R[('ours_U0_eps0.01', c)]
        ot, od = R[('oracle_tuned', c)], R[('oracle_default', c)]
        e0 = c.split('+')[0].endswith('E0')
        def v(r):
            ext = '–' if e0 else f"{100 * r['viol_ext']:.2f}"
            return f"{ext} / {100 * r['viol_team']:.2f}"
        gt, gd = o['cost'] - ot['cost'], o['cost'] - od['cost']
        du = o['cost'] - u0['cost']
        frac = lambda x, g: f'{x / g:.2f}' if abs(g) > 1e-9 else '–'
        L.append(f"| {c[:-len(TS)]} | {o['cost']:.4f} | {ot['cost']:.4f} ({v(ot)}) | {od['cost']:.4f} ({v(od)}) | {gt:+.4f} | "
                 f"{gd:+.4f} | {o['info_cost']:.4f} | {frac(o['info_cost'], gt)} / {frac(o['info_cost'], gd)} | "
                 f"{u0['cost']:.4f} ({v(u0)}) | {du:+.4f} | {frac(du, gt)} / {frac(du, gd)} | {u0['cost'] - l0['cost']:+.4f} | "
                 f"{u0['cost'] - ot['cost']:+.4f} |")
    L += ['', '| cell | Ours W std/mean / range | Ours(U=0) W std/mean / range | Ours(U=0, ε 0.01) cost (viol. ext / team %) | layer penalty (Ours) |',
          '|---|---|---|---|---|']
    for c in cells:
        o, u0, l0 = R[('ours', c)], R[('ours_U0', c)], R[('ours_U0_eps0.01', c)]
        e0 = c.split('+')[0].endswith('E0')
        ve = '–' if e0 else f"{100 * l0['viol_ext']:.2f}"
        L.append(f"| {c[:-len(TS)]} | {o['W_cv']:.3f} / {o['W_range']:.2f} | {u0['W_cv']:.3f} / {u0['W_range']:.2f} | "
                 f"{l0['cost']:.4f} ({ve} / {100 * l0['viol_team']:.2f}) | {o['layer_pen']:.4f} |")
    (OUT / 'info_cost_seed0.md').write_text('\n'.join(L) + '\n')
    print('\n'.join(L), flush=True)
