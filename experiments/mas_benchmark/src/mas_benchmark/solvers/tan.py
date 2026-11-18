"""Tan, Liu, Johansson, Dimarogonas, "A continuous-time violation-free multi-agent optimization algorithm and its
applications to safe distributed control", arXiv:2404.07571 (TAC 2025).

Sparse form, Eq. (18), one coupled constraint per team pair m = (i, k) within sensing range:
    local QP of i:  a_i^T u_i + (y_i^m - y_k^m) + b_i^m <= 0,  a_i = -2 d_ik,  b_i^m = -kappa h_ik / 2
    update (law='sat', default; the paper's safe-control setting, Sec. VII-B and VIII-B):
                    y_i^m <- y_i^m - k0 dt sat(c_i^m - c_k^m)     (Eq. (26), sign replaced by sat as in Sec. VIII-B)
    update (law='gradient', the static algorithm):
                    y_i^m <- y_i^m - k0 dt (c_i^m - c_k^m)        (forward Euler of Eq. (21))
with c^m the local multipliers, exchanged over the communication graph (here: the sensing graph).
External agents are identified and covered at their capability (Sec. 12.1 of v40):
    a_i^T u_i + max_{||u_e|| <= v_env} g_e(u_e) <= 0.
Rows are softened by an exact penalty M so the local QP stays solvable when Slater (Assumption 3) fails; an agent
whose local problem needed a slack reports no multipliers that step, and its pairs' y are held (its multipliers
would only be the penalty M and drive y without bound). k0 = 1 as in the paper's example.
"""
import numpy as np

from ..core import Solver
from ..utils.qp import soft_qp


class Tan(Solver):
    name = 'tan'

    def sat(self, v):
        """Sec. VIII-B: 1 if v > 0.1; 10 v on [-0.1, 0.1]; -1 if v < -0.1 (sat_width 0.1; tunable)."""
        return float(np.clip(v / self.sat_width, -1.0, 1.0))

    def __init__(self, k0=1.0, law='sat', M=1000.0, slack_tol=1e-6, sat_width=0.1):
        self.k0, self.law, self.M, self.slack_tol, self.sat_width = k0, law, M, slack_tol, sat_width
        self.name = 'tan' if law == 'sat' else f'tan_{law}'

    def reset(self, scenario, dynamics, spec, dt):
        super().reset(scenario, dynamics, spec, dt)
        self.y = {}         # (i, k) -> y_i^m for pair m = {i, k}
        self.c = {}         # (i, k) -> c_i^m from the previous solve

    def act(self, obs):
        A, b = self.dynamics.input_polytope()
        N, n_u = obs.u_nom.shape
        spec = self.spec
        # Eq. (21): exchange multipliers of the previous step and move y; pairs that left range are dropped
        live = {(i, nb.index) for i in range(N) for nb in obs.neighbours[i] if not nb.external}
        for key in [key for key in self.y if key not in live]:
            del self.y[key]
        for (i, k), ci in self.c.items():
            if (i, k) in live and (k, i) in self.c:
                g = ci - self.c[(k, i)]
                g = self.sat(g) if self.law == 'sat' else g
                self.y[(i, k)] = self.y.get((i, k), 0.0) - self.k0 * self.dt * g
        U, c_new, slack, mu, tracks = np.zeros_like(obs.u_nom), {}, np.zeros(N), {}, {}
        for i in range(N):
            rows, rhs, keys, row_tracks = [], [], [], []
            for nb in obs.neighbours[i]:
                row_tracks.append(nb.track)
                g = spec.own_term(obs.x[i], nb.x)
                if nb.external:
                    ge = spec.own_term(nb.x, obs.x[i])
                    rows.append(g.a); rhs.append(-(g.b + np.linalg.norm(ge.a) * obs.v_env + ge.b))
                else:
                    k = nb.index
                    tracks[k] = nb.track
                    shift = self.y.get((i, k), 0.0) - self.y.get((k, i), 0.0)
                    rows.append(g.a); rhs.append(-(g.b + shift)); keys.append((len(rows) - 1, k))
            w = obs.weights[i]
            u, z, lam = soft_qp(w * np.eye(n_u), -w * obs.u_nom[i], A, b, rows, rhs, self.M)
            U[i], slack[i] = u, z.sum()
            mu.update({(i, tr): float(l) for tr, l in zip(row_tracks, lam)})
            if slack[i] > self.slack_tol:
                continue
            for r, k in keys:
                c_new[(i, k)] = float(lam[r])
        self.c = c_new
        r = {(i, tracks[k]): v - self.y.get((k, i), 0.0) for (i, k), v in self.y.items() if k in tracks}
        return U, dict(r=r, mu=mu, slack=slack)
