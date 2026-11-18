import numpy as np
from scipy.linalg import block_diag

from ..core import Solver
from ..utils.qp import soft_qp


class Oracle(Solver):
    """One central QP over all team inputs (Sec. 12.1).

    Team pairs carry the full constraint c_ik <= 0; every external body is covered at its capability bound,
    max_{||u_e|| <= v_env} c_ie <= 0. Every row is softened by an exact penalty M z (z >= 0).
    """
    name = 'oracle'

    def __init__(self, M=1000.0):
        self.M = M

    def act(self, obs):
        A, b = self.dynamics.input_polytope()
        N, n_u = obs.u_nom.shape
        spec = self.spec
        track_of = {nb.index: nb.track for nbs in obs.neighbours for nb in nbs if not nb.external}
        rows, rhs, owners = [], [], []
        for i in range(N):
            for nb in obs.neighbours[i]:
                if nb.external:
                    g = spec.own_term(obs.x[i], nb.x)
                    worst = np.linalg.norm(spec.own_term(nb.x, obs.x[i]).a) * obs.v_env \
                        + spec.own_term(nb.x, obs.x[i]).b
                    row = np.zeros(N * n_u); row[i * n_u:(i + 1) * n_u] = g.a
                    rows.append(row); rhs.append(-(g.b + worst)); owners.append([(i, nb.track)])
                elif nb.index > i:
                    k = nb.index
                    gi, gk = spec.own_term(obs.x[i], obs.x[k]), spec.own_term(obs.x[k], obs.x[i])
                    row = np.zeros(N * n_u)
                    row[i * n_u:(i + 1) * n_u], row[k * n_u:(k + 1) * n_u] = gi.a, gk.a
                    rows.append(row); rhs.append(-(gi.b + gk.b))
                    owners.append([(i, nb.track), (k, track_of[i])])
        Abig = block_diag(*[A] * N)
        P = np.kron(np.diag(obs.weights), np.eye(n_u))
        q = -(obs.weights[:, None] * obs.u_nom).ravel()
        sol, z, lam = soft_qp(P, q, Abig, np.tile(b, N), rows, rhs, self.M)
        mu = {}
        for (keys, l) in zip(owners, lam):
            mu.update({key: float(l) for key in keys})
        return sol.reshape(N, n_u), dict(slack=float(z.sum()), mu=mu)
