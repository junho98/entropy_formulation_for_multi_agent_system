"""'Gas' specification: one shared constraint over the fleet.

    Z = sum_pairs phi(|d_ik|) exp(-h_ik / tau),  h_ik = |d_ik|^2 - rho^2,  safe set Z <= 1,
    CBF  Z' <= gamma (1 - Z),  Z' = sum_pairs <grad_d Z_ik, u_i - u_k>,
    grad_d Z_ik = exp(-h_ik/tau) (phi'(|d|) d/|d| - (2 phi / tau) d)   (parallel to d).

phi is a smooth cutoff: 1 for |d| <= r_in, 0 for |d| >= r_c, cos^2 in between. Agent i's term is
    c_i(u_i) = sum_k [<grad_d Z_ik, u_i> + (gamma/2) Z_ik] - gamma / N_bar,
and the other half of each pair (the neighbour's velocity term and its gamma/2 Z_ik) is covered by i's room for that
contact. Summed over a team of N agents with exact agreements, sum_i (c_i + R_i) >= Z' - gamma (1 - Z) + gamma (1 - N/N_bar):
exact for N = N_bar, conservative for N < N_bar.
"""
import numpy as np

from ..core import Affine, Specification


class GasBarrier(Specification):
    def __init__(self, tau=0.1, rho=1.0, r_in=1.5, r_c=3.0, gamma=2.0, n_bar=8, sensing_range=5.0):
        self.tau, self.rho, self.r_in, self.r_c = tau, rho, r_in, r_c
        self.gamma, self.kappa, self.n_bar = gamma, gamma, n_bar
        self.sensing_range = sensing_range

    def phi(self, r):
        if r <= self.r_in:
            return 1.0, 0.0
        if r >= self.r_c:
            return 0.0, 0.0
        x = (r - self.r_in) / (self.r_c - self.r_in) * np.pi / 2
        return float(np.cos(x) ** 2), float(-np.sin(2 * x) * np.pi / (2 * (self.r_c - self.r_in)))

    def safety(self, x_i, x_k):
        d = x_i[:2] - x_k[:2]
        return float(d @ d - self.rho ** 2)

    def pair(self, x_i, x_k):
        """-> (Z_ik, beta) with grad_d Z_ik = beta * d/|d| (beta <= 0 near contact)."""
        d = x_i[:2] - x_k[:2]
        r = float(np.linalg.norm(d))
        ph, dph = self.phi(r)
        if ph == 0.0:
            return 0.0, 0.0
        e = float(np.exp(-(r * r - self.rho ** 2) / self.tau))
        return ph * e, e * (dph - 2.0 * ph * r / self.tau)

    def contact(self, x_i, x_k):
        return float(np.linalg.norm(x_i[:2] - x_k[:2])) < self.r_c

    def own_term(self, x_i, x_k):
        """Pair share of i: <grad_d Z_ik, u_i> + (gamma/2) Z_ik (the agent constant -gamma/N_bar is added once per agent)."""
        Z, beta = self.pair(x_i, x_k)
        d = x_i[:2] - x_k[:2]
        return Affine(beta * d / max(np.linalg.norm(d), 1e-12), 0.5 * self.gamma * Z)

    def constant(self):
        return -self.gamma / self.n_bar
