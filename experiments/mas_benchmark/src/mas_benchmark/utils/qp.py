"""Small dense QPs: min 1/2 x^T P x + q^T x  s.t.  G x <= h.

Goldfarb-Idnani active-set (quadprog), as in Sec. 11; SLSQP as a fallback.
"""
import numpy as np
import quadprog
from scipy.optimize import minimize

REG = 1e-7   # quadprog needs P strictly positive definite (slack blocks are linear)


def solve_qp(P, q, G, h, x0=None):
    P = P + REG * np.eye(len(q))
    try:
        x = quadprog.solve_qp(P, -q, -G.T, -h)[0]
        return x, 'quadprog'
    except ValueError:
        x0 = np.zeros(len(q)) if x0 is None else x0
        res = minimize(lambda x: 0.5 * x @ P @ x + q @ x, x0, jac=lambda x: P @ x + q,
                       constraints=[dict(type='ineq', fun=lambda x: h - G @ x, jac=lambda _: -G)],
                       method='SLSQP', options=dict(ftol=1e-10, maxiter=200))
        return res.x, 'slsqp'


def soft_qp(P, q, A, b, rows, rhs, M):
    """min 1/2 x^T P x + q^T x + M sum(z)  s.t.  A x <= b (hard),  rows x - z <= rhs,  z >= 0.

    -> (x, z, multipliers of the soft rows). Multipliers are capped at M by the exact penalty."""
    n, K = len(q), len(rhs)
    Pb = np.zeros((n + K, n + K)); Pb[:n, :n] = P
    qb = np.concatenate([q, M * np.ones(K)])
    rows = np.asarray(rows, dtype=float).reshape(K, n)
    G = np.vstack([np.hstack([A, np.zeros((len(b), K))]),
                   np.hstack([rows, -np.eye(K)]),
                   np.hstack([np.zeros((K, n)), -np.eye(K)])])
    h = np.concatenate([b, np.asarray(rhs, dtype=float), np.zeros(K)])
    Pb = Pb + REG * np.eye(n + K)
    try:
        sol = quadprog.solve_qp(Pb, -qb, -G.T, -h)
        x, lam = sol[0], sol[4][len(b):len(b) + K]
    except ValueError:
        x, _ = solve_qp(Pb, qb, G, h)
        lam = np.zeros(K)
    return x[:n], x[n:], lam
