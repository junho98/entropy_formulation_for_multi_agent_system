import numpy as np

from ..core import Solver
from ..utils.qp import soft_qp


class Reciprocal(Solver):
    """Fixed half split: each agent enforces its own share g_i(u_i) <= 0 toward every sensed body.

    Shares are softened with an exact penalty M z (z >= 0) so the local QP is always solvable.
    Uses only agent i's LocalView.
    """
    name = 'reciprocal'

    def __init__(self, M=1000.0):
        self.M = M

    def act(self, obs):
        A, b = self.dynamics.input_polytope()
        n_u = self.dynamics.n_u
        U, slack, mu = np.zeros((obs.n_agents, n_u)), [], {}
        for i in range(obs.n_agents):
            v = obs.local(i)
            gs = [self.spec.own_term(v.x, body.x) for body in v.bodies]
            U[i], z, lam = soft_qp(v.weight * np.eye(n_u), -v.weight * v.u_nom, A, b,
                                   [g.a for g in gs], [-g.b for g in gs], self.M)
            slack.append(float(z.sum()))
            mu.update({(i, body.track): float(l) for body, l in zip(v.bodies, lam)})
        return U, dict(slack=slack, mu=mu)
