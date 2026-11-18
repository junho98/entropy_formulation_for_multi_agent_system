"""Sec. 12.1 metrics: cost and safety toward externals / among agents."""
import numpy as np

from ..core import Analyzer


class Cost(Analyzer):
    """Mean of f_i = w_i/2 ||u_i - u0_i||^2 over agents and time."""
    name = 'cost'

    def __call__(self, log):
        f = 0.5 * log.weights[None, :] * np.sum((log.u - log.u_nom) ** 2, axis=2)
        return dict(cost=float(f.mean()))


class Safety(Analyzer):
    """Minimum distance and fraction of steps with some pair closer than `frac` * rho.

    The threshold is 0.95 rho toward externals (Sec. 12.1) and among agents alike, so contact at the boundary
    (distance ~rho within O(dt^2)) is not counted; minimum distances are reported separately."""
    name = 'safety'

    def __init__(self, frac_ext=0.95, frac_team=0.95):
        self.frac_ext = frac_ext
        self.frac_team = frac_team

    def __call__(self, log):
        X = log.x
        N = X.shape[1]
        dt = np.linalg.norm(X[:, :, None] - X[:, None, :], axis=3)
        dt[:, np.arange(N), np.arange(N)] = np.inf
        d_team = dt.min(axis=(1, 2))
        out = dict(min_dist_team=float(d_team.min()),
                   viol_team=float(np.mean(d_team < self.frac_team * log.rho)))
        if log.ext_x.shape[1]:
            de = np.linalg.norm(X[:, :, None] - log.ext_x[:, None, :], axis=3).min(axis=(1, 2))
            out.update(min_dist_ext=float(de.min()), viol_ext=float(np.mean(de < self.frac_ext * log.rho)))
        else:
            out.update(min_dist_ext=np.nan, viol_ext=np.nan)
        return out


class Liveness(Analyzer):
    """Fraction of agent-time spent nearly stopped (speed < v_stop, v40 Sec. 12.2 uses 0.15), and the longest
    continuous stop of any agent (deadlock indicator)."""
    name = 'liveness'

    def __init__(self, v_stop=0.15):
        self.v_stop = v_stop

    def __call__(self, log):
        stopped = np.linalg.norm(log.u, axis=2) < self.v_stop          # (K, N)
        longest = 0
        for col in stopped.T:
            run = 0
            for s in col:
                run = run + 1 if s else 0
                longest = max(longest, run)
        return dict(stop_frac=float(stopped.mean()), longest_stop_s=float(longest * log.dt))
