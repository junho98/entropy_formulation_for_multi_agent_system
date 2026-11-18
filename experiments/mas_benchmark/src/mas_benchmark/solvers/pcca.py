"""Predictor-corrector collision avoidance (Jankovic & Santillo; arXiv:2012.10261 Eq. (18)-(19),
arXiv:2008.12092 Eq. (16)-(17), (21)), adapted to single integrators.

Agent i solves over its own input u_ii and copies u_ij of every sensed body j:
    min  ||u_ii - u0_i||^2 + sum_j ||u_ij||^2         (unit weights, as in Eq. (18); others' weights are unknown)
    s.t. a_ij + b_ij (u_ii - u_ij - w_j) >= 0                      (own pairs)
         a_jk + b_jk (u_ij + w_j - u_ik - w_k) >= 0                (pairs among the sensed bodies)
with a = kappa h, b = 2 d^T (relative degree one), and the corrector w_j = u_j - u*_ij from the previous step
(one-sample delay, Eq. (21)), u_j the observed velocity. Only u_ii is applied; it is held to the input polytope.
No communication; outsiders are treated like any other body; uses only agent i's LocalView.
Rows are softened by an exact penalty M.
"""
import numpy as np

from ..core import Solver
from ..utils.qp import soft_qp


class PCCA(Solver):
    name = 'pcca'

    def __init__(self, M=1000.0):
        self.M = M

    def reset(self, scenario, dynamics, spec, dt):
        super().reset(scenario, dynamics, spec, dt)
        self.copies = [dict() for _ in range(scenario.n_agents)]    # body id -> u*_ij of the previous step

    def act(self, obs):
        A, b = self.dynamics.input_polytope()
        n_u = self.dynamics.n_u
        kappa, rho = self.spec.kappa, self.spec.rho
        U, mu = np.zeros((obs.n_agents, n_u)), {}
        for i in range(obs.n_agents):
            v = obs.local(i)
            nbs = v.bodies
            ids = [nb.track for nb in nbs]
            prev = self.copies[i]
            W = [nb.u_prev - prev.get(j, np.zeros(n_u)) for j, nb in zip(ids, nbs)]
            K = len(nbs)
            n = n_u * (K + 1)
            sl = lambda j: slice(n_u * (j + 1), n_u * (j + 2))      # copy of the j-th sensed body
            P = np.eye(n)
            q = np.zeros(n); q[:n_u] = -v.u_nom
            rows, rhs = [], []
            # -(a + b (.)) <= 0  ->  -b (.) <= a
            for j, nb in enumerate(nbs):
                d = v.x - nb.x
                row = np.zeros(n); row[:n_u], row[sl(j)] = -2 * d, 2 * d
                rows.append(row); rhs.append(kappa * (d @ d - rho ** 2) - 2 * d @ W[j])
            for j in range(K):
                for k in range(j + 1, K):
                    d = nbs[j].x - nbs[k].x
                    row = np.zeros(n); row[sl(j)], row[sl(k)] = -2 * d, 2 * d
                    rows.append(row); rhs.append(kappa * (d @ d - rho ** 2) + 2 * d @ (W[j] - W[k]))
            Ah = np.hstack([A, np.zeros((len(b), n - n_u))])
            x, _, lam = soft_qp(P, q, Ah, b, rows, rhs, self.M)
            mu.update({(i, nb.track): float(l) for nb, l in zip(nbs, lam[:K])})
            U[i] = x[:n_u]
            self.copies[i] = {j: x[sl(m)].copy() for m, j in enumerate(ids)}
        return U, dict(mu=mu)
