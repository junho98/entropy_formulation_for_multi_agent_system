"""Lyu, Luo, Dolan, "Risk-aware Safe Control for Decentralized Multi-agent Systems via Dynamic Responsibility
Allocation", arXiv:2305.13467 (IROS 2023), deterministic case (no velocity noise, so the CVaR term vanishes).

    L_ik = -2 d_ik^T (u_i - u_k) - kappa h_ik + c            Eq. (3), u = observed current velocities
    R_i  = sum_{k sensed by i} L_ik                           Eq. (4)
    omega_ik = R_k / (R_i + R_k)                              Thm. 2
    -2 d_ik^T u_i <= omega_ik kappa h_ik                      Eq. (6)/(7)
Every agent computes R_k itself from the observed states and velocities of the bodies around k; outsiders are
treated like any other body. c only has to keep L > 0 (the paper gives no value); by default it is the smallest
constant that does so over the sensing range and the input bound.
"""
import numpy as np

from ..core import Solver
from ..utils.qp import soft_qp


class RiskRatio(Solver):
    name = 'risk_ratio'

    def __init__(self, c=None, M=1000.0):
        self.c, self.M = c, M

    def reset(self, scenario, dynamics, spec, dt):
        super().reset(scenario, dynamics, spec, dt)
        self.u_prev = None
        if self.c is None:
            r, v = spec.sensing_range, getattr(dynamics, 'u_max', 1.2)
            self.c = 2 * r * 2 * v + spec.kappa * r ** 2 + 1.0

    def risks(self, P, V):
        """R for every body from positions P (B, 2) and observed velocities V (B, 2)."""
        kappa, rho = self.spec.kappa, self.spec.rho
        D = P[:, None] - P[None]
        dist = np.linalg.norm(D, axis=2)
        L = -2 * np.einsum('ikd,ikd->ik', D, V[:, None] - V[None]) - kappa * (dist ** 2 - rho ** 2) + self.c
        near = (dist <= self.spec.sensing_range) & ~np.eye(len(P), dtype=bool)
        return np.where(near, L, 0.0).sum(axis=1)

    def act(self, obs):
        A, b = self.dynamics.input_polytope()
        N, n_u = obs.u_nom.shape
        kappa = self.spec.kappa
        u_prev = np.zeros_like(obs.u_nom) if self.u_prev is None else self.u_prev
        P = np.vstack([obs.x, obs.ext_x]) if len(obs.ext_x) else obs.x
        V = np.vstack([u_prev, obs.ext_u_prev]) if len(obs.ext_x) else u_prev
        R = self.risks(P, V)
        U, omega, mu = np.zeros_like(obs.u_nom), {}, {}
        for i in range(N):
            rows, rhs = [], []
            for nb in obs.neighbours[i]:
                j = nb.index if nb.index >= 0 else N + nb.ext_index
                om = R[j] / (R[i] + R[j])
                d = obs.x[i] - nb.x
                rows.append(-2 * d); rhs.append(om * kappa * (d @ d - self.spec.rho ** 2))
                omega[(i, j)] = float(om)
            w = obs.weights[i]
            U[i], _, lam = soft_qp(w * np.eye(n_u), -w * obs.u_nom[i], A, b, rows, rhs, self.M)
            mu.update({(i, nb.track): float(l) for nb, l in zip(obs.neighbours[i], lam)})
        self.u_prev = U.copy()
        return U, dict(omega=omega, mu=mu)
