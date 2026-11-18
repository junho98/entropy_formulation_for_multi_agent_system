"""Temperature belief (Def. 10.1, Sec. 11).

Hypotheses: behavioural temperature tau in {1e-4, 1e-2, 1e-1, 1, inf} with an intent u_bar held over the window.
Observations are approach speeds y_s, linearised in the intent as y_s = a_s u_bar + b_s by the regime of the
(modelled) response at that step. Prior u_bar ~ N(0, 1), noise variance tau + sigma_o^2; tau = inf is uniform
on the capability range of approach speeds.
"""
from collections import deque

import numpy as np

TAUS = np.array([1e-4, 1e-2, 1e-1, 1.0])
FINITE_SPLIT = np.array([0.4, 0.4, 0.15, 0.05])
FOLLOW_PRIOR = 0.97      # prior mass on the following (finite-temperature) hypotheses; tau = inf gets the rest


def linearise(s, R, alpha, h, kappa, eps, ke, tol=1e-6):
    """Regime of the self-model response along the pair axis -> (a, b).

    The responder minimises 1/2 (y - u_bar)^2 + ke/2 p^2, p = eps - s, s = -(alpha y - kappa h/2 + R) (unit weight):
    unconstrained (a, b) = (1, 0); layer a = 1/(1 + ke alpha^2); wall a = 0, y = (kappa h/2 - R)/alpha.
    """
    if s >= eps - tol:
        return 1.0, 0.0
    if s > tol:
        den = 1.0 + ke * alpha ** 2
        return 1.0 / den, -ke * alpha * (eps + R - 0.5 * kappa * h) / den
    return 0.0, (0.5 * kappa * h - R) / alpha


class TemperatureBelief:
    def __init__(self, window=50, sigma_o=0.01, follow_prior=FOLLOW_PRIOR):
        self.obs = deque(maxlen=window)
        self.sigma2 = sigma_o ** 2
        with np.errstate(divide='ignore'):
            self.log_prior = np.log(np.append(follow_prior * FINITE_SPLIT, 1.0 - follow_prior))

    def append(self, y, a, b):
        self.obs.append((y, a, b))

    def posterior(self, v_cap):
        """-> log weights (5,) [finite taus..., inf], posterior means m (4,) and variances v (4,) of u_bar."""
        log_w = self.log_prior.copy()
        m, v = np.zeros(len(TAUS)), np.ones(len(TAUS))
        if not self.obs:
            return log_w, m, v
        y, a, b = map(np.array, zip(*self.obs))
        e, n = y - b, len(y)
        s2 = TAUS + self.sigma2
        aa, ae = a @ a, a @ e
        # e ~ N(0, s2 I + a a^T): Sherman-Morrison and the determinant lemma
        quad = (e @ e) / s2 - ae ** 2 / (s2 ** 2 * (1.0 + aa / s2))
        logdet = n * np.log(s2) + np.log1p(aa / s2)
        ll = -0.5 * (quad + logdet + n * np.log(2 * np.pi))
        ll_inf = -n * np.log(2 * v_cap) if np.all(np.abs(y) <= v_cap + 1e-9) else -np.inf
        log_w = log_w + np.append(ll, ll_inf)
        log_w -= np.logaddexp.reduce(log_w)
        prec = 1.0 + aa / s2
        return log_w, (ae / s2) / prec, 1.0 / prec
