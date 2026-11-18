"""Trajectory recording for plots and animations.

`record` runs one closed loop and keeps what the drawings need, in plain arrays:

  p (K, N, 2), q (K, E, 2)   agent and external positions
  targets (K, N, 2)          the target each agent heads to at step k
  W (K, N)                   accumulated base cost W_i(t) = int 1/2 w_i |u_i - u0_i|^2 dt
  lam                        active contacts: rows (k, i, b, lambda_ik) with b the body index (team 0..N-1, then
                             externals N..), from the solver's per-step `mu` diagnostics (Ours only; empty otherwise)
  weights (N,), rho, sensing, arena_radius, circle_radius

A `Trajectory` saves to / loads from one .npz file.
"""
from dataclasses import dataclass, asdict

import numpy as np

from ..core import simulate
from ..dynamics import SingleIntegrator
from ..scenarios import make_scenario
from ..solvers import make_solver
from ..specs import PairwiseBarrier


class _TargetLog:
    """Scenario proxy that copies the current targets each time the runner asks for nominal inputs."""

    def __init__(self, scenario):
        self._s, self.targets = scenario, []

    def __getattr__(self, name):
        return getattr(self._s, name)

    def nominal_input(self, x):
        self.targets.append(self._s.targets.copy())
        return self._s.nominal_input(x)


@dataclass
class Trajectory:
    scenario: str
    solver: str
    seed: int
    dt: float
    p: np.ndarray
    q: np.ndarray
    targets: np.ndarray
    W: np.ndarray
    lam: np.ndarray
    weights: np.ndarray
    rho: float
    sensing: float
    arena_radius: float
    circle_radius: float

    @property
    def t(self):
        return self.dt * np.arange(len(self.p))

    def bodies(self, k):
        """(N + E, 2) positions of all bodies at step k (team first)."""
        return np.concatenate([self.p[k], self.q[k]]) if self.q.shape[1] else self.p[k]

    def violations(self, k, frac=0.95):
        """Pairs (i, b) with i a team agent, b any other body, closer than frac * rho at step k."""
        P = self.bodies(k)
        N = self.p.shape[1]
        D = np.linalg.norm(self.p[k][:, None] - P[None], axis=2)
        D[np.arange(N), np.arange(N)] = np.inf
        i, b = np.where(D < frac * self.rho)
        return [(a, c) for a, c in zip(i, b) if c >= N or a < c]

    def save(self, path):
        np.savez_compressed(path, **{k: np.asarray(v) for k, v in asdict(self).items()})

    @classmethod
    def load(cls, path):
        z = np.load(path)
        kw = {k: z[k] for k in z.files}
        for k in ('scenario', 'solver'):
            kw[k] = str(kw[k])
        for k in ('seed',):
            kw[k] = int(kw[k])
        for k in ('dt', 'rho', 'sensing', 'arena_radius', 'circle_radius'):
            kw[k] = float(kw[k])
        return cls(**kw)


def record(scenario, solver, horizon, seed, dt=0.02, spec=None, rho=None, return_log=False):
    """solver: a make_solver name, or a solver object with its spec (as configs.build returns); rho: the true safety
    radius to draw and score against when the spec carries a margin; return_log: also return the runner's Log."""
    sc = make_scenario(scenario)
    proxy = _TargetLog(sc)
    spec = spec or PairwiseBarrier()
    sol = make_solver(solver) if isinstance(solver, str) else solver
    log = simulate(proxy, SingleIntegrator(), spec, sol, horizon, dt, seed)
    f = 0.5 * log.weights[None] * np.sum((log.u - log.u_nom) ** 2, axis=2) * log.dt
    tracks = np.asarray(log.meta['tracks'])
    body_of = np.empty_like(tracks)
    body_of[tracks] = np.arange(len(tracks))                     # track id -> body index
    lam = [(k, i, int(body_of[t]), float(v)) for k, inf in enumerate(log.info)
           for (i, t), v in inf.get('mu', {}).items() if v > 0]
    tr = Trajectory(scenario, sol.name, seed, log.dt, log.x[..., :2], log.ext_x[..., :2],
                    np.array(proxy.targets), np.cumsum(f, axis=0), np.array(lam, float).reshape(-1, 4),
                    log.weights, spec.rho if rho is None else rho, spec.sensing_range, sc.cfg.arena_radius, sc.cfg.circle_radius)
    return (tr, log) if return_log else tr
