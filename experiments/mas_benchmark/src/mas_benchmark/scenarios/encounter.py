"""Small hand-placed encounters (no randomness): agents go to fixed goals, externals move at constant velocity.

Used to reproduce the reference papers' examples (two-agent encounters, position swaps).
"""
from dataclasses import dataclass, field

import numpy as np

from ..core import Scenario


@dataclass
class EncounterConfig:
    name: str = 'encounter'
    starts: list = field(default_factory=list)       # team start positions
    goals: list = field(default_factory=list)        # team goals
    weights: tuple = (1.0,)
    ext_starts: list = field(default_factory=list)   # external start positions
    ext_vels: list = field(default_factory=list)     # external constant velocities
    v_env: float = 1.0
    speed: float = 1.0                               # nominal speed, slowed linearly inside distance `speed`


class Encounter(Scenario):
    def __init__(self, cfg: EncounterConfig):
        self.cfg = cfg
        self.name = cfg.name
        self.n_agents = len(cfg.starts)
        self.v_env = cfg.v_env

    def reset(self, rng):
        self.goals = np.array(self.cfg.goals, dtype=float)
        self.ext_x = np.array(self.cfg.ext_starts, dtype=float).reshape(-1, 2)
        self.ext_u = np.array(self.cfg.ext_vels, dtype=float).reshape(-1, 2)
        return np.array(self.cfg.starts, dtype=float)

    def weights(self):
        w = self.cfg.weights
        return np.array([w[i % len(w)] for i in range(self.n_agents)], dtype=float)

    def nominal_input(self, x):
        d = self.goals - x
        n = np.linalg.norm(d, axis=1, keepdims=True)
        return self.cfg.speed * d / np.maximum(n, self.cfg.speed)

    def externals(self):
        return self.ext_x, self.ext_u

    def advance(self, x, dt):
        self.ext_x = self.ext_x + dt * self.ext_u
