from abc import ABC, abstractmethod


class Specification(ABC):
    """Pairwise coupled constraint c_ik = g_i(u_i) + g_k(u_k) <= 0, separable in the inputs.

    The state dependence is frozen at the current step, so each share g_i is affine in u_i.
    """
    sensing_range: float
    rho: float

    @abstractmethod
    def own_term(self, x_i, x_k):
        """-> Affine g_i with c_ik = g_i(u_i) + g_k(u_k), g_k = own_term(x_k, x_i)."""

    @abstractmethod
    def safety(self, x_i, x_k):
        """h_ik >= 0 on the safe set."""

    def value(self, x_i, u_i, x_k, u_k):
        return self.own_term(x_i, x_k)(u_i) + self.own_term(x_k, x_i)(u_k)
