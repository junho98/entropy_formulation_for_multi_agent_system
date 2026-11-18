"""Data passed between scenario, solver, runner and analyzers."""
from dataclasses import dataclass, field

import numpy as np


@dataclass
class Affine:
    """g(u) = a @ u + b."""
    a: np.ndarray
    b: float

    def __call__(self, u):
        return float(self.a @ u + self.b)


@dataclass
class Neighbour:
    """One body sensed by agent i (privileged form).

    `track` is an anonymous id, randomly permuted per run, stable while the body is sensed.
    `index` (team index, -1 for externals), `external` and `ext_index` are ground truth: only methods that
    identify outsiders (Tan, oracle) or that assume global observation may read them.
    """
    index: int
    x: np.ndarray
    u_prev: np.ndarray
    external: bool
    ext_index: int = -1
    track: int = -1


@dataclass(frozen=True)
class Body:
    """What agent i observes about one sensed body: an anonymous track, its position and its last velocity."""
    track: int
    x: np.ndarray
    u_prev: np.ndarray


@dataclass(frozen=True)
class LocalView:
    """Everything agent i may use under the convention: its own state, nominal input and weight, the bodies
    it senses (anonymous), and public constants. No identities, no others' intents, no messages."""
    t: float
    x: np.ndarray
    u_nom: np.ndarray
    weight: float
    bodies: tuple
    v_env: float


@dataclass
class Observation:
    t: float
    x: np.ndarray              # (N, n_x) team states
    u_nom: np.ndarray          # (N, n_u) nominal inputs u0_i
    weights: np.ndarray        # (N,)    cost weights w_i
    neighbours: list           # neighbours[i] = list[Neighbour] within sensing range
    ext_x: np.ndarray          # (E, n_x) external states (ground truth, for oracle / Tan)
    ext_u_prev: np.ndarray     # (E, n_u)
    v_env: float               # public capability of external agents

    @property
    def n_agents(self):
        return len(self.x)

    def local(self, i):
        """Agent i's own observation; decentralised methods without identification use only this."""
        return LocalView(self.t, self.x[i].copy(), self.u_nom[i].copy(), float(self.weights[i]),
                         tuple(Body(nb.track, nb.x.copy(), nb.u_prev.copy()) for nb in self.neighbours[i]),
                         self.v_env)


@dataclass
class Log:
    dt: float
    t: np.ndarray              # (K,)
    x: np.ndarray              # (K, N, n_x)
    u: np.ndarray              # (K, N, n_u)
    u_nom: np.ndarray          # (K, N, n_u)
    ext_x: np.ndarray          # (K, E, n_x)
    weights: np.ndarray        # (N,)
    rho: float
    info: list = field(default_factory=list)   # per-step solver diagnostics (dicts)
    meta: dict = field(default_factory=dict)
