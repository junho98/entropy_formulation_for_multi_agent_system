"""Truncated-excess law on the seed-0 contact logs (results/grid2x3/clog/*_ours_seed0.npz).

Under i's mixture at each contact-step (the same model the code's room uses):
  finite tau_j: mu_j = min(alpha m_j + g0, r), sd_j = alpha sqrt(tau_j + v_j + sigma_o^2), q_j = Phi((mu_j - r)/sd_j),
                conditional mean excess L_j = tau_j / M (exponential tail of rate M/tau_j beyond r);
  tau = inf:    usage uniform on [g0 - alpha v_cap, g0 + alpha v_cap]: q = P(usage > r), L = mean excess above r;
  g0 = -kappa h / 2;  p = sum_h w_h q_h;  Lbar = sum_h w_h q_h L_h / p.
Tests: (a) U >= Lbar q*(p, S), KL(Ber(q*) || Ber(p)) = S, q* > p (q* = 1 when ln(1/p) <= S);
(b) U ~ Lbar S / ln(1/p) for p << delta; (c) ln(1/pi_n) against constrained steps for team (follower) contacts.

    python scripts/truncated_excess.py  -> appends "Truncated-excess law" to results/grid2x3/info_cost_seed0.md,
                                           results/grid2x3/truncated_excess.pdf/.png
"""
from pathlib import Path

import numpy as np
from scipy.special import ndtr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt                                           # noqa: E402

from mas_benchmark.scenarios import GRID2X3                               # noqa: E402
from mas_benchmark.solvers.thermo.belief import TAUS                      # noqa: E402
from mas_benchmark.solvers.thermo.bound import THETAS                     # noqa: E402
from mas_benchmark.viz import style                                       # noqa: E402

OUT = Path(__file__).resolve().parents[1] / 'results' / 'grid2x3'
DELTA, M, SIG2, KAPPA = 0.05, 1000.0, 0.01 ** 2, 2.0
S = np.log(1 / DELTA)


def kl(q, p):
    with np.errstate(divide='ignore', invalid='ignore'):
        a = np.where(q > 0, q * np.log(q / p), 0.0)
        b = np.where(q < 1, (1 - q) * np.log((1 - q) / (1 - p)), 0.0)
    return a + b


def qstar(p):
    """KL(Ber(q) || Ber(p)) = S, q > p; 1 when ln(1/p) <= S (p >= delta)."""
    lo, hi = p.copy(), np.ones_like(p)
    done = np.log(1 / np.maximum(p, 1e-300)) <= S
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        big = kl(mid, p) > S
        hi = np.where(big, mid, hi); lo = np.where(big, lo, mid)
    return np.where(done, 1.0, 0.5 * (lo + hi))


def law(z):
    al, h, r = z['alpha'], z['h'], z['r']
    g0 = -0.5 * KAPPA * h
    mu = np.minimum(al[:, None] * z['m'] + g0[:, None], r[:, None])
    sd = al[:, None] * np.sqrt(TAUS[None] + z['v'] + SIG2)
    q_f = ndtr((mu - r[:, None]) / sd)
    L_f = np.broadcast_to(TAUS[None] / M, q_f.shape)
    gmin, gmax = g0 - al * z['v_cap'], g0 + al * z['v_cap']
    rr = np.clip(r, gmin, gmax)
    q_u = (gmax - rr) / (gmax - gmin)
    L_u = 0.5 * (gmax + rr) - r
    q = np.hstack([q_f, q_u[:, None]]); L = np.hstack([L_f, L_u[:, None]])
    wq = z['w'] * q
    p = wq.sum(1)
    Lbar = np.where(p > 0, (wq * L).sum(1) / np.maximum(p, 1e-300), 0.0)
    return p, Lbar


def lin(x, y):
    """OLS line y = b1 x + b0 in closed form (no LAPACK)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    xm, ym = x.mean(), y.mean()
    b1 = np.sum((x - xm) * (y - ym)) / np.sum((x - xm) ** 2)
    return b1, ym - b1 * xm


def fitlog(x, y):
    lx, ly = np.log(x), np.log(y)
    b1, b0 = lin(lx, ly)
    r2 = 1 - np.sum((ly - (b1 * lx + b0)) ** 2) / np.sum((ly - ly.mean()) ** 2)
    return b1, b0, r2


if __name__ == '__main__':
    style.use()
    floor = float(np.percentile(np.load(OUT / 'clog' / 'HOM-E8+ts1.5_ours_seed0.npz')['U'], 5))   # the common floor value
    L = ['', '## Truncated-excess law', '',
         'Computed per contact-step from the logged mixture (seed 0, Ours ε 0.1, target_sep 1.5; the logs were extended by the '
         'per-hypothesis weights w_h, intent means m_j and variances v_j and the public capability v_cap, and seed 0 rerun: '
         'costs identical to the earlier runs). Finite τ_j: μ_j = min(α m_j − κh/2, r), sd_j = α√(τ_j + v_j + σ_o²), '
         'q_j = Φ((μ_j − r)/sd_j), conditional mean excess L_j = τ_j/M (the code\'s exponential tail of rate M/τ_j beyond r). '
         'τ = ∞: usage uniform on [−κh/2 ∓ α v_cap], q = P(usage > r), L = mean excess above r. p = Σ_h w_h q_h, '
         'L̄ = Σ_h w_h q_h L_h / p. q* solves KL(Ber(q*)‖Ber(p)) = S with q* > p (q* = 1 when ln(1/p) ≤ S). '
         f'S = {S:.3f}. Floor: the value U takes on most steps when nothing is predicted to exceed the agreement, '
         f'{floor:.5f} (identical in every cell; it is set by the θ grid and the τ = ∞ term, not by p).', '',
         '| cell | steps | p median | share p < δ/10 | (a) share U ≥ L̄q* | (a) median U/(L̄q*) | (b) n (p < δ/10) | (b) log-log slope | R² | median U/(L̄S/ln(1/p)) | share at floor | (b) slope without floor | R² | (c) team contacts | (c) rate (nats per observed step, n ≤ 10) | (c) R² | (c) median ln(1/π_n), n 50–200 | (c) share of constrained steps |',
         '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.4))
    pooled = {'a': [], 'bx': [], 'by': [], 'c': []}
    L2 = ['', 'Closed form and product form (all contact-steps with 0 < p < 1 and L̄ > 0): (d) U ≥ L̄ (S − ln(1/(1−p)))/ln(1/p); '
          '(e) U ln(1/p) ≥ L̄ S (ΔE/λ = U to first order, information = ln(1/p) nats); (f) the same with the accumulated '
          'evidence ln(1/π_n), π_n the posterior weight of τ = ∞. Share holding · median ratio (left side / right side) '
          '[10th–90th percentile].', '',
          '| cell | steps | (d) holds | (d) ratio U/bound | (e) holds | (e) ratio U ln(1/p) / (L̄ S) | (f) holds | (f) ratio U ln(1/π_n) / (L̄ S) |',
          '|---|---|---|---|---|---|---|---|']
    allde = []
    for c0 in GRID2X3:
        z = dict(np.load(OUT / 'clog' / f'{c0}+ts1.5_ours_seed0.npz'))
        ok = (z['n_win'] > 0) & (z['U'] > 0)
        z = {k: v[ok] for k, v in z.items()}
        p, Lb = law(z)
        U = z['U']
        good = (p > 0) & (Lb > 0)
        bound_a = Lb * qstar(np.clip(p, 1e-300, 1))
        ra = U[good] / bound_a[good]
        small = good & (p < DELTA / 10) & (p > 1e-300)
        xb = Lb[small] * S / np.log(1 / p[small])
        yb = U[small]
        b1, b0, r2 = fitlog(xb, yb) if small.sum() > 2 else (np.nan, np.nan, np.nan)
        atf = np.isclose(yb, floor, rtol=0.05)
        c1, c0_, q2 = fitlog(xb[~atf], yb[~atf]) if (~atf).sum() > 2 else (np.nan, np.nan, np.nan)
        # (c) team contacts: ln(1/pi_n) vs constrained steps (a_s < 1) of the contact
        team = z['k'] < 8
        key = (z['i'] * 100 + z['k']) * 1e6 + np.round(z['t0'] * 50)
        X, Y, plateau, conshare = [], [], [], []
        for kk in np.unique(key[team]):
            mm = np.where((key == kk) & team)[0]
            mm = mm[np.argsort(z['n'][mm])]
            lpi = -np.log(np.maximum(z['w'][mm, -1], 1e-300))
            sel = z['n'][mm] <= 10                 # observed steps in the contact (the window is 50)
            X.append(z['n'][mm][sel]); Y.append(lpi[sel])
            plateau.append(lpi[(z['n'][mm] >= 50) & (z['n'][mm] <= 200)])
            conshare.append(np.mean(z['a_last'][mm] < 1))
        X, Y = np.concatenate(X), np.concatenate(Y)
        fin = np.isfinite(Y)
        X, Y = X[fin].astype(float), Y[fin]
        cs, ci = lin(X, Y) if np.ptp(X) > 0 else (np.nan, np.nan)
        yc = cs * X + ci if np.ptp(X) > 0 else Y
        cr2 = 1 - np.sum((Y - yc) ** 2) / max(np.sum((Y - Y.mean()) ** 2), 1e-300)
        L.append(f'| {c0} | {good.sum()} | {np.median(p[good]):.2g} | {np.mean(p[good] < DELTA / 10):.2f} | '
                 f'{np.mean(ra >= 1 - 1e-9):.2f} | {np.median(ra):.3g} | {small.sum()} | {b1:.2f} | {r2:.2f} | '
                 f'{np.median(yb / xb):.3g} | {np.mean(atf):.2f} | {c1:.2f} | {q2:.2f} | {len(np.unique(key[team]))} | '
                 f'{cs:.2f} | {cr2:.2f} | {np.median(np.concatenate(plateau)):.1f} | {np.mean(conshare):.2f} |')
        g2 = good & (p < 1) & (p > 1e-300)
        bd = Lb[g2] * (S - np.log(1 / (1 - p[g2]))) / np.log(1 / p[g2])
        rd = U[g2] / bd
        re = U[g2] * np.log(1 / p[g2]) / (Lb[g2] * S)
        rf = U[g2] * (-np.log(np.maximum(z['w'][g2, -1], 1e-300))) / (Lb[g2] * S)
        pr = lambda x: f'{np.median(x):.3g} [{np.percentile(x, 10):.3g}–{np.percentile(x, 90):.3g}]'
        L2.append(f'| {c0} | {g2.sum()} | {np.mean(rd >= 1 - 1e-9):.2f} | {pr(rd)} | {np.mean(re >= 1 - 1e-9):.2f} | {pr(re)} | '
                  f'{np.mean(rf >= 1 - 1e-9):.2f} | {pr(rf)} |')
        allde.append(np.c_[rd, re, rf])
        pooled['a'].append(np.c_[bound_a[good], U[good]]); pooled['bx'].append(xb); pooled['by'].append(yb)
        pooled['c'].append(np.c_[X, Y])
    A = np.vstack(pooled['a']); bx = np.concatenate(pooled['bx']); by = np.concatenate(pooled['by']); C = np.vstack(pooled['c'])
    b1, b0, r2 = fitlog(bx, by)
    atf = np.isclose(by, floor, rtol=0.05)
    c1, _, q2 = fitlog(bx[~atf], by[~atf])
    ra = A[:, 1] / A[:, 0]
    L.append(f'| pooled | {len(A)} | – | – | {np.mean(ra >= 1 - 1e-9):.2f} | {np.median(ra):.3g} | {len(bx)} | {b1:.2f} | '
             f'{r2:.2f} | {np.median(by / bx):.3g} | {np.mean(atf):.2f} | {c1:.2f} | {q2:.2f} | – | '
             f'{lin(C[:, 0], C[:, 1])[0]:.2f} | – | – | – |')
    D = np.vstack(allde)
    pr = lambda x: f'{np.median(x):.3g} [{np.percentile(x, 10):.3g}–{np.percentile(x, 90):.3g}]'
    L2.append(f'| pooled | {len(D)} | {np.mean(D[:, 0] >= 1 - 1e-9):.2f} | {pr(D[:, 0])} | {np.mean(D[:, 1] >= 1 - 1e-9):.2f} | '
              f'{pr(D[:, 1])} | {np.mean(D[:, 2] >= 1 - 1e-9):.2f} | {pr(D[:, 2])} |')
    L += L2
    rng = np.random.default_rng(0)
    i = rng.choice(len(A), min(len(A), 40000), replace=False)
    axes[0].scatter(A[i, 0], A[i, 1], s=2, alpha=0.3, color=style.colour('final'), rasterized=True)
    lim = [1e-8, 10]
    axes[0].plot(lim, lim, color=style.VIOL, lw=1.2, label='U = L̄ q*')
    axes[0].set_xscale('log'); axes[0].set_yscale('log'); axes[0].set_xlim(lim); axes[0].set_ylim(1e-4, 10)
    axes[0].set_xlabel(r'$\bar L\, q^*(p,S)$'); axes[0].set_ylabel('logged U'); axes[0].set_title('(a) lower bound'); axes[0].legend()
    j = rng.choice(len(bx), min(len(bx), 40000), replace=False)
    axes[1].scatter(bx[j], by[j], s=2, alpha=0.3, color=np.where(atf[j], style.OUTSIDER, style.colour('final')), rasterized=True)
    axes[1].plot(lim, lim, color=style.VIOL, lw=1.2, label='slope 1')
    axes[1].axhline(floor, color=style.INK2, lw=0.8, ls='--', label=f'θ-grid floor {floor:.4f}')
    axes[1].set_xscale('log'); axes[1].set_yscale('log'); axes[1].set_xlim(1e-12, 10); axes[1].set_ylim(1e-4, 10)
    axes[1].set_xlabel(r'$\bar L\,S/\ln(1/p)$  ($p<\delta/10$)'); axes[1].set_ylabel('logged U'); axes[1].set_title('(b) p ≪ δ'); axes[1].legend(fontsize=8)
    k = rng.choice(len(C), min(len(C), 40000), replace=False)
    axes[2].scatter(C[k, 0], C[k, 1], s=2, alpha=0.3, color=style.colour('final'), rasterized=True)
    axes[2].set_xlabel('observed steps in contact (n ≤ 10)'); axes[2].set_ylabel(r'$\ln(1/\pi_n)$, team contacts')
    axes[2].set_title('(c) evidence against τ = ∞')
    fig.tight_layout()
    style.save(fig, OUT / 'truncated_excess')
    plt.close(fig)
    with (OUT / 'info_cost_seed0.md').open('a') as fh:
        fh.write('\n'.join(L) + '\n')
    print('\n'.join(L))
