"""Paper table: load transfer between rows (agent 0 with an outsider row e and a teammate row 1), final configuration.

(a) d lam_01 / d R_0e: formula k_e w (w I + k_e G G^T)^{-1} vs finite differences on the local QP, at operating points
    where both rows are inside the layer.
(b) closed loop: teammates 0 and 1 pressing on each other, an outsider pushes agent 0 from three directions; Delta mu_01 =
    mean mu_01 with the outsider minus without, over the window d_0e < 1.6 (Ours = final config, and Oracle).
(c) virial pressure P_i = sum_k lam_ik |d_ik|^2 over agents in one S4 frame (Ours final config, eps 0.1, seed 0).

    python scripts/final_load_transfer.py  -> results/final_mutual/load_transfer.md, results/final_mutual/virial_S4.pdf
"""
from pathlib import Path

import numpy as np

from mas_benchmark.analyzers.agreement import body_of
from mas_benchmark.core import simulate
from mas_benchmark.dynamics import SingleIntegrator
from mas_benchmark.scenarios import Encounter, EncounterConfig, make_scenario
from mas_benchmark.solvers import make_solver
from mas_benchmark.specs import PairwiseBarrier
from mas_benchmark.utils.qp import solve_qp

OUT = Path(__file__).resolve().parents[1] / 'results' / 'final_mutual'
KE, EPS, M, W = 20.0, 0.1, 1000.0, 1.0
OURS = 'ours_eps0.1_mutual'


def local_lam(G, rhs):
    K, n_u = G.shape
    n = n_u + 2 * K
    P = np.zeros((n, n)); P[:n_u, :n_u] = W * np.eye(n_u); P[n_u:n_u + K, n_u:n_u + K] = KE * np.eye(K)
    q = np.concatenate([np.zeros(n_u), np.zeros(K), M * np.ones(K)])
    Gi = np.vstack([np.hstack([G, -np.eye(K), np.zeros((K, K))]), np.hstack([G, np.zeros((K, K)), -np.eye(K)]),
                    np.hstack([np.zeros((2 * K, n_u)), -np.eye(2 * K)])])
    h = np.concatenate([-(rhs + EPS), -rhs, np.zeros(2 * K)])
    return KE * solve_qp(P, q, Gi, h)[0][n_u:n_u + K]


GEOM = {'toward the teammate': (np.array([1.1, 0.0]), np.array([0.04, -0.19])),
        'orthogonal': (np.array([0.0, -1.1]), np.array([0.02, 0.02])),
        'same side': (np.array([-0.55, -0.95]), np.array([0.02, 0.02]))}
D1 = np.array([-1.2, 0.0])                                        # d_01 = p_0 - p_1


def partial_table():
    rows = []
    for name, (de, rhs) in GEOM.items():
        G = np.vstack([-2 * de, -2 * D1])
        lam = local_lam(G, rhs)
        assert np.all(lam > 0) and np.all(lam < KE * EPS), (name, lam)     # both rows inside the layer
        pred = KE * W * np.linalg.inv(W * np.eye(2) + KE * G @ G.T)[1, 0]
        fd = (local_lam(G, rhs + np.array([1e-5, 0.0]))[1] - lam[1]) / 1e-5
        rows.append((name, float(de @ D1), pred, fd))
    return rows


PUSH = {'toward the teammate': ([-5.0, 0.05], [0.5, 0.0]), 'orthogonal': ([0.05, -5.0], [0.0, 0.5]),
        'same side': ([2.5, 4.33], [-0.25, -0.433])}


def press(method, ext):
    cfg = dict(name='press', starts=[[0, 0], [1.3, 0]], goals=[[2.0, 0.0], [-0.7, 0.0]], v_env=0.6, speed=0.3)
    if ext:
        cfg.update(ext_starts=[ext[0]], ext_vels=[ext[1]])
    log = simulate(Encounter(EncounterConfig(**cfg)), SingleIntegrator(), PairwiseBarrier(), make_solver(method), 14.0, 0.02, 0)
    tr = {b: t for t, b in body_of(log).items()}
    mu01 = np.array([inf.get('mu', {}).get((0, tr[1]), 0.0) for inf in log.info])
    return log, mu01


def closed_loop():
    rows = []
    for name, ext in PUSH.items():
        for method in (OURS, 'oracle'):
            log, a = press(method, ext)
            _, b = press(method, None)
            win = np.linalg.norm(log.x[:, 0] - log.ext_x[:, 0], axis=1) < 1.6
            rows.append((name, method, float(b[win].mean()), float(a[win].mean()), float(a[win].mean() - b[win].mean())))
    return rows


def virial():
    log = simulate(make_scenario('S4'), SingleIntegrator(), PairwiseBarrier(), make_solver(OURS), 60.0, 0.02, 0)
    body = body_of(log)
    N = log.x.shape[1]
    P = np.zeros((len(log.info), N))
    for t, inf in enumerate(log.info):
        allx = np.vstack([log.x[t], log.ext_x[t]])
        for (i, tk), lam in inf.get('mu', {}).items():
            if lam > 0:
                P[t, i] += lam * float(np.sum((log.x[t, i] - allx[body[tk]]) ** 2))
    t = int(np.argmax(P.sum(axis=1)))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(4.6, 4.0))
    sc = ax.scatter(log.x[t, :, 0], log.x[t, :, 1], c=P[t], cmap='viridis', s=90, vmin=0, edgecolors='k', linewidths=0.4)
    ax.scatter(log.ext_x[t, :, 0], log.ext_x[t, :, 1], marker='x', c='tab:red', s=40, label='external')
    for i in range(N):
        ax.annotate(f'{P[t, i]:.2g}', log.x[t, i], fontsize=7, xytext=(5, 4), textcoords='offset points')
    ax.add_patch(plt.Circle((0, 0), 7.0, fill=False, ls=':', lw=0.6))
    ax.set_xlim(-7.5, 7.5); ax.set_ylim(-7.5, 7.5); ax.set_aspect('equal')
    ax.set_title(f'S4, t = {t * 0.02:.1f} s: virial pressure $P_i=\\sum_k\\lambda_{{ik}}\\|d_{{ik}}\\|^2$', fontsize=8)
    ax.legend(fontsize=7, loc='upper right')
    plt.colorbar(sc, ax=ax, fraction=0.046)
    fig.tight_layout()
    fig.savefig(OUT / 'virial_S4.pdf')
    return t * 0.02, P[t]


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    pt, cl = partial_table(), closed_loop()
    tv, Pv = virial()
    L = ['# Load transfer between rows (final configuration: Ours = pairwise, mutual law, default step, delta = 0.05)', '',
         '## Sensitivity of the teammate price to the outsider room', '',
         'd lam_01 / d R_0e at operating points with both rows inside the layer; formula k_e w (w I + k_e G G^T)^{-1}, '
         'G rows -2 d^T.', '',
         '| geometry | <d_0e, d_01> | predicted | finite difference |', '|---|---|---|---|']
    L += [f'| {n} | {ip:+.2f} | {p:+.4f} | {f:+.4f} |' for n, ip, p, f in pt]
    L += ['', '## Closed loop', '',
          'Teammates 0 and 1 press on each other; a non-yielding outsider (speed 0.5) pushes agent 0. Mean mu_01 over the '
          'window d_0e < 1.6, with and without the outsider.', '',
          '| push | method | mu_01 without | mu_01 with | Delta mu_01 |', '|---|---|---|---|---|']
    L += [f"| {n} | {'Ours' if m == OURS else 'Oracle'} | {b:.3f} | {a:.3f} | {d:+.3f} |" for n, m, b, a, d in cl]
    L += ['', f'## Virial pressure (S4, Ours eps 0.1, seed 0, frame of maximal total pressure t = {tv:.1f} s)', '',
          'P_i = ' + ', '.join(f'{p:.3g}' for p in Pv) + '. Figure: virial_S4.pdf.']
    (OUT / 'load_transfer.md').write_text('\n'.join(L) + '\n')
    print('\n'.join(L))
