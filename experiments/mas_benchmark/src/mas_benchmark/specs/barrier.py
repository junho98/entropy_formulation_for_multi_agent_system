from ..core import Affine, Specification


class PairwiseBarrier(Specification):
    """Example 9.1: c_ik = -2 d_ik^T (u_i - u_k) - kappa h_ik <= 0,  d_ik = p_i - p_k,  h_ik = ||d_ik||^2 - rho^2.

    Shares g_i(u_i) = -2 d_ik^T u_i - (kappa/2) h_ik (single-integrator positions)."""

    def __init__(self, kappa=2.0, rho=1.0, sensing_range=5.0):
        self.kappa = kappa
        self.rho = rho
        self.sensing_range = sensing_range

    def safety(self, x_i, x_k):
        d = x_i[:2] - x_k[:2]
        return float(d @ d - self.rho ** 2)

    def own_term(self, x_i, x_k):
        d = x_i[:2] - x_k[:2]
        return Affine(-2.0 * d, -0.5 * self.kappa * self.safety(x_i, x_k))
