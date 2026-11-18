"""Checks requested from the theory discussion (2026-11-12).

(1) Load transfer. For an agent with several active layer rows G (rows a_k = -2 d_k^T), the local QP gives
    d lam / d R = k_e w (w I + k_e G G^T)^{-1}   (inputs inside their bound),
    so the cross term between rows e and k has the sign of -<d_e, d_k>.
    (a) finite-difference check of this formula on the local QP; (b) closed-loop runs with an external pushing
    agent 0 toward teammate 1, orthogonally, and from 1's side.
(2) Frozen two-agent test (weights 1 vs 3): imbalance against exchange iterations, default vs 'region' step.

    python scripts/theory_checks.py  -> results/theory_checks.md
"""
from pathlib import Path

import numpy as np

from mas_benchmark.analyzers.agreement import body_of
from mas_benchmark.core import Observation, sense, simulate
from mas_benchmark.dynamics import SingleIntegrator
from mas_benchmark.scenarios import Encounter, EncounterConfig
from mas_benchmark.solvers import Thermo, make_solver
from mas_benchmark.specs import PairwiseBarrier
from mas_benchmark.utils.qp import solve_qp

RES = Path(__file__).resolve().parents[1] / 'results'
KE, EPS, M = 20.0, 0.1, 1000.0
out = ['# Theory checks', '']


def local_qp(u0, w, G, rhs):
    """Ours' local QP without the input bound: min w/2|u-u0|^2 + ke/2 |p|^2 + M 1'z, G u + rhs + eps - p <= 0,
    G u + rhs - z <= 0, p, z >= 0 (rhs = b_k + R_k). -> lam = ke p."""
    K, n_u = G.shape
    n = n_u + 2 * K
    P = np.zeros((n, n)); P[:n_u, :n_u] = w * np.eye(n_u); P[n_u:n_u + K, n_u:n_u + K] = KE * np.eye(K)
    q = np.concatenate([-w * u0, np.zeros(K), M * np.ones(K)])
    Gi = np.vstack([np.hstack([G, -np.eye(K), np.zeros((K, K))]), np.hstack([G, np.zeros((K, K)), -np.eye(K)]),
                    np.hstack([np.zeros((2 * K, n_u)), -np.eye(2 * K)])])
    h = np.concatenate([-(rhs + EPS), -rhs, np.zeros(2 * K)])
    sol, _ = solve_qp(P, q, Gi, h)
    return KE * sol[n_u:n_u + K]


# ---- (1a) formula vs finite differences ----
out += ['## (1a) d lam / d R: formula vs finite differences on the local QP', '',
        '| geometry | <d_e, d_1> | formula d lam_1/d R_e | finite diff. | formula d lam_e/d R_e | finite diff. |',
        '|---|---|---|---|---|---|']
w = 1.0
for name, de in [('external opposite to 1 (pushes 0 toward 1)', np.array([1.1, 0.0])),
                 ('external orthogonal', np.array([0.0, -1.1])),
                 ('external on 1\'s side (pushes 0 away from 1)', np.array([-0.55, -0.95]))]:
    d1 = np.array([-1.2, 0.0])                         # d_01 = p0 - p1
    G = np.vstack([-2 * de, -2 * d1])
    u0 = np.zeros(2)
    rhs = np.array([0.02, 0.02])                       # b_k + R_k chosen so both rows sit inside the layer at the optimum
    lam0 = local_qp(u0, w, G, rhs)
    pred = KE * w * np.linalg.inv(w * np.eye(2) + KE * G @ G.T)
    hstep = 1e-5
    fd = (local_qp(u0, w, G, rhs + np.array([hstep, 0])) - lam0) / hstep
    out.append(f'| {name} | {de @ d1:+.2f} | {pred[1, 0]:+.4f} | {fd[1]:+.4f} | {pred[0, 0]:+.4f} | {fd[0]:+.4f} |'
               + ('' if np.all(lam0 > 0) else ' (row inactive)'))
out.append('')

# ---- (1b) closed loop ----
# Teammates press on each other (goals on the other side), so the (0,1) price is already active; an external then
# pushes agent 0. Delta mu_01 = mean mu_01 with the external minus without, over the window where d_0e < 1.6.
out += ['## (1b) Closed loop: teammates 0 and 1 pressing each other (mu_01 > 0 at baseline); a non-yielding external '
        '(speed 0.5) pushes agent 0', '',
        '| push | method | mean mu_01 without | with | Delta mu_01 | mean mu_10 without | with | min d_0e | min d_01 |',
        '|---|---|---|---|---|---|---|---|---|']
pushes = {'toward 1 (from the left)': ([-5.0, 0.05], [0.5, 0.0]),
          'orthogonal (from below)': ([0.05, -5.0], [0.0, 0.5]),
          "from 1's side (60 deg)": ([2.5, 4.33], [-0.25, -0.433])}


def press(m, ext):
    cfg = dict(name='press', starts=[[0, 0], [1.3, 0]], goals=[[2.0, 0.0], [-0.7, 0.0]], v_env=0.6, speed=0.3)
    if ext:
        cfg.update(ext_starts=[ext[0]], ext_vels=[ext[1]])
    log = simulate(Encounter(EncounterConfig(**cfg)), SingleIntegrator(), PairwiseBarrier(), make_solver(m), 14.0, 0.02, 0)
    body = body_of(log); tr = {b: t for t, b in body.items()}
    mu01 = np.array([inf.get('mu', {}).get((0, tr[1]), 0.0) for inf in log.info])
    mu10 = np.array([inf.get('mu', {}).get((1, tr[0]), 0.0) for inf in log.info])
    return log, mu01, mu10


for pname, ext in pushes.items():
    for m in ['ours_eps0.1', 'ours_eps0.1_plain_region', 'oracle', 'reciprocal']:
        log, a01, a10 = press(m, ext)
        _, b01, b10 = press(m, None)
        win = np.linalg.norm(log.x[:, 0] - log.ext_x[:, 0], axis=1) < 1.6
        if not win.any():
            win = np.zeros(len(a01), bool); win[-50:] = True
        d0e = float(np.linalg.norm(log.x[:, 0] - log.ext_x[:, 0], axis=1).min())
        d01 = float(np.linalg.norm(log.x[:, 0] - log.x[:, 1], axis=1).min())
        out.append(f'| {pname} | {m} | {b01[win].mean():.3f} | {a01[win].mean():.3f} | {a01[win].mean() - b01[win].mean():+.3f} | '
                   f'{b10[win].mean():.3f} | {a10[win].mean():.3f} | {d0e:.2f} | {d01:.2f} |')
out.append('')

# ---- (2) frozen two-agent test ----
out += ['## (2) Frozen two agents (distance 1.4, head-on, weights 1 vs 3): imbalance after n exchange iterations', '',
        '| step | n=1 | 10 | 25 | 50 | 100 | 400 | final mu |', '|---|---|---|---|---|---|---|---|']
dyn, spec = SingleIntegrator(), PairwiseBarrier()
x = np.array([[0.0, 0.0], [1.4, 0.0]]); u0 = np.array([[1.0, 0.0], [-1.0, 0.0]])
for kw, label in [(dict(), '1/(2 ke), follow law (default)'), (dict(law='plain'), '1/(2 ke), plain law'),
                  (dict(step='region'), 'region, follow law'), (dict(step='region', law='plain'), 'region, plain law'),
                  (dict(step='newton'), 'newton, follow law')]:
    th = Thermo(eps=EPS, **kw); th.reset(type('S', (), {'n_agents': 2})(), dyn, spec, 0.02)
    U = np.zeros((2, 2)); E = np.zeros((0, 2)); hist = []
    for _ in range(400):
        obs = Observation(0.0, x, u0, np.array([1.0, 3.0]), sense(x, U, E, E, dyn, spec), E, E, 1.2)
        U, inf = th.act(obs)
        hist.append(list(inf['mu'].values()))
    h = np.array(hist); imb = np.abs(h[:, 0] - h[:, 1]) / (h[:, 0] + h[:, 1] + 1e-12)
    out.append(f'| {label} | ' + ' | '.join(f'{imb[j]:.3f}' for j in (0, 9, 24, 49, 99, 399)) + f' | {np.round(h[-1], 3)} |')
out.append('')
(RES / 'theory_checks.md').write_text('\n'.join(out) + '\n')
print('\n'.join(out))
