"""Sec. 12.1 testbed: N agents travel between targets on a circle; external agents roam the arena."""
from dataclasses import dataclass

import numpy as np

from ..core import Scenario


@dataclass
class CircleConfig:
    name: str = 'circle'
    n_agents: int = 8
    circle_radius: float = 6.0
    arena_radius: float = 7.0         # externals reflect here
    weights: tuple = (1.0,)           # cycled over agents: (1, 3) gives the alternating fleet
    n_ext: int = 0
    ext_speed: float = 0.0
    heading_noise: float = 2.0        # rad / sqrt(s)
    reactive: bool = False            # externals avoid bodies on their own
    repulse_range: float = 2.0
    v_env: float = 1.0                # public capability of externals
    arrive_tol: float = 0.2
    nominal_speed: float = 1.0
    bias: float = 0.0                 # public right-hand bias of the nominal controller (0: off, as in every earlier run)
    bias_mode: str = 'always'         # 'always' | 'near': only while another body is within near_range and ahead |
                                      # 'body': b R(-90 deg) r_hat toward the nearest body ahead within near_range
    near_range: float = 5.0
    target_sep: float = 0.0           # a new target keeps at least this distance from the other agents' targets (0: off)


class CircleArena(Scenario):
    def __init__(self, cfg: CircleConfig):
        self.cfg = cfg
        self.name = cfg.name
        self.n_agents = cfg.n_agents
        self.v_env = cfg.v_env

    def _draw_target(self, p, others=()):
        c = self.cfg
        while True:
            a = self.rng.uniform(0, 2 * np.pi)
            tgt = c.circle_radius * np.array([np.cos(a), np.sin(a)])
            if np.linalg.norm(tgt - p) > c.circle_radius and all(np.linalg.norm(tgt - o) >= c.target_sep for o in others):
                return tgt

    def reset(self, rng):
        c = self.cfg
        self.rng = rng
        ang = 2 * np.pi * np.arange(c.n_agents) / c.n_agents
        x0 = c.circle_radius * np.stack([np.cos(ang), np.sin(ang)], axis=1)
        T = []
        for p in x0:
            T.append(self._draw_target(p, T if c.target_sep > 0 else ()))
        self.targets = np.array(T)
        ext = []
        while len(ext) < c.n_ext:
            r = c.arena_radius * np.sqrt(rng.uniform())
            a = rng.uniform(0, 2 * np.pi)
            q = r * np.array([np.cos(a), np.sin(a)])
            if np.min(np.linalg.norm(x0 - q, axis=1)) > 2.0 and all(np.linalg.norm(q - e) > 2.0 for e in ext):
                ext.append(q)
        self.ext_x = np.array(ext).reshape(-1, 2)
        self.ext_heading = rng.uniform(0, 2 * np.pi, c.n_ext)
        self.ext_u = np.zeros((c.n_ext, 2))
        return x0

    def weights(self):
        w = self.cfg.weights
        return np.array([w[i % len(w)] for i in range(self.n_agents)], dtype=float)

    def nominal_input(self, x):
        d = self.targets - x
        n = np.linalg.norm(d, axis=1, keepdims=True)
        g = d / np.maximum(n, 1e-9)
        c = self.cfg
        if c.bias == 0.0:
            return c.nominal_speed * g
        if c.bias_mode == 'body':
            P = np.vstack([x, self.ext_x]) if len(self.ext_x) else x
            v = g.copy()
            for i in range(len(x)):
                r = P - x[i]
                dist = np.linalg.norm(r, axis=1)
                dist[i] = np.inf
                ok = (dist <= c.near_range) & (r @ g[i] > 0)
                if ok.any():
                    j = np.argmin(np.where(ok, dist, np.inf))
                    rh = r[j] / dist[j]
                    v[i] = g[i] + c.bias * np.array([rh[1], -rh[0]])    # sidestep to the right of that body
            return c.nominal_speed * v / np.linalg.norm(v, axis=1, keepdims=True)
        b = np.full(len(x), c.bias)
        if c.bias_mode == 'near':
            P = np.vstack([x, self.ext_x]) if len(self.ext_x) else x
            for i in range(len(x)):
                r = P - x[i]
                dist = np.linalg.norm(r, axis=1)
                dist[i] = np.inf
                b[i] *= np.any((dist <= c.near_range) & (r @ g[i] > 0))
        v = g + b[:, None] * np.stack([g[:, 1], -g[:, 0]], axis=1)      # g + b R(-90 deg) g: turn slightly clockwise
        return c.nominal_speed * v / np.linalg.norm(v, axis=1, keepdims=True)

    def externals(self):
        return self.ext_x, self.ext_u

    def advance(self, x, dt):
        c = self.cfg
        for i in range(self.n_agents):
            if np.linalg.norm(self.targets[i] - x[i]) < c.arrive_tol:
                others = [t for k, t in enumerate(self.targets) if k != i] if c.target_sep > 0 else ()
                self.targets[i] = self._draw_target(x[i], others)
        if c.n_ext == 0:
            return
        self.ext_heading += c.heading_noise * np.sqrt(dt) * self.rng.standard_normal(c.n_ext)
        v = np.stack([np.cos(self.ext_heading), np.sin(self.ext_heading)], axis=1)
        if c.reactive:
            bodies = np.vstack([x, self.ext_x])
            for e in range(c.n_ext):
                d = self.ext_x[e] - bodies
                n = np.linalg.norm(d, axis=1)
                m = (n > 1e-9) & (n < c.repulse_range)
                v[e] = v[e] + (d[m] / n[m, None] ** 2).sum(axis=0)
        v = c.ext_speed * v / np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-9)
        q = self.ext_x + dt * v
        r = np.linalg.norm(q, axis=1)
        out = r > c.arena_radius
        if out.any():
            nrm = q[out] / r[out, None]
            v[out] = v[out] - 2 * (v[out] * nrm).sum(axis=1, keepdims=True) * nrm
            q[out] = nrm * (2 * c.arena_radius - r[out, None])
            self.ext_heading[out] = np.arctan2(v[out, 1], v[out, 0])
        self.ext_u = v
        self.ext_x = q
