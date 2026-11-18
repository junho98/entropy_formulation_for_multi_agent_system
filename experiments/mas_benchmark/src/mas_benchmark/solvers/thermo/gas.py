"""Ours on the 'gas' specification (specs/gas.py): one row, one slack and one scalar costate per agent.

Per agent i (LocalView only), with contacts C_i = sensed bodies within r_c:
  row      c_i(u) = <G_i, u> + sum_k (gamma/2) Z_ik - gamma/N_bar,   G_i = sum_k grad_d Z_ik
  room     R_i = sum_k R_ik,  R_ik = A_w[max(c_k^pair, r_ik)] (Def. 2.8, per contact)
           c_k^pair = <grad_d Z_ki, u_k> + (gamma/2) Z_ik = |beta| y_k + (gamma/2) Z_ik (y_k: k's approach speed)
           coverage='closest': the coverage part is kept only when i is the closest body to k among those i sees
           (otherwise R_ik = r_ik); coverage='pair': every contact is covered (Def. 2.8).
  slack    s_i = -(c_i(u) + R_i), lam_i = ke_Z (eps_Z - s_i)_+
  exchange on contact edges, mutual law, step 1/(2 ke_Z).

Scaling to Z units (stated choice): near contact |grad_d Z| = 2 rho / tau, against 2 rho for the pairwise barrier, so
  ke_Z = ke tau^2 (same layer stiffness ke_Z |grad Z|^2 = ke |grad h|^2 at contact),  M_Z = M tau,
  eps_Z = eps * gamma / N_bar (the layer is a fraction eps of the per-agent budget gamma/N_bar, so an idle agent,
          whose slack is gamma/N_bar, sits outside the layer for eps < 1).
Step bound: s_i is 1-Lipschitz in each r_ik (R_i is a sum of rooms, each with slope <= 1 in r_ik), so the pair's
costate difference is 2 ke_Z-Lipschitz and 1/(2 ke_Z) does not overshoot (inputs held). Interior sensitivity
(single row): d lam_i / d R_i = ke_Z w / (w + ke_Z |G_i|^2).

Reading k's scalar costate needs k's whole row and room, which depend on k's other contacts and agreements. i can
evaluate k's row only over the contacts of k it sees, and does not hold k's other agreements: the estimate uses
  s_hat_k = -(sum_{l in C_k seen by i} c_kl(u_k) - gamma/N_bar + R_ki + sum_{l != i} 0),
i.e. k's other agreements and coverages are taken as 0. Prop. 4.4 does not hold (observation is not closed), so the
mutual copies are not exactly opposite; the gap is measured. replica='pair' restricts the estimate to the (k, i) pair
(s_hat_k = -(c_ki(u_k) - gamma/N_bar + R_ki)), ignoring the load k carries from its other contacts.
"""
import numpy as np

from ...utils.qp import solve_qp
from .belief import linearise
from .solver import Pair, Thermo


class ThermoGas(Thermo):
    def __init__(self, eps=0.1, coverage='closest', replica='seen', **kw):
        kw.setdefault('law', 'mutual')
        super().__init__(eps=eps, **kw)
        self.eps_nominal = eps
        self.coverage, self.replica = coverage, replica
        self.name = f'gas_eps{eps:g}' + ('' if coverage == 'closest' else f'_{coverage}') + ('' if replica == 'seen' else f'_rep{replica}')

    def reset(self, scenario, dynamics, spec, dt):
        super().reset(scenario, dynamics, spec, dt)
        tau = spec.tau
        self.ke = 20.0 * tau ** 2
        self.M = 1000.0 * tau
        self.eps = self.eps_nominal * spec.gamma / spec.n_bar
        self.gain = 1.0 / (2.0 * self.ke)

    # ---- geometry helpers (same expressions on both sides of a pair) ----
    def pair_geo(self, x_a, x_b):
        Z, beta = self.spec.pair(x_a, x_b)
        d = x_a - x_b
        n = float(np.linalg.norm(d))
        return Z, abs(beta), d / max(n, 1e-12), d, n

    def row_of(self, x_a, u_a, others):
        """sum over contacts of a (among `others` positions) of <grad_d Z_ab, u_a> + (gamma/2) Z_ab, plus the constant."""
        tot = self.spec.constant()
        for x_b in others:
            if np.linalg.norm(x_a - x_b) < self.spec.r_c:
                Z, beta = self.spec.pair(x_a, x_b)
                d = x_a - x_b
                tot += beta * float(d @ u_a) / max(np.linalg.norm(d), 1e-12) + 0.5 * self.spec.gamma * Z
        return tot

    def closest(self, x_self, body, bodies):
        """True if the agent at x_self is the closest, among itself and the bodies it sees (other than `body`), to `body`."""
        dm = float(np.linalg.norm(body.x - x_self))
        return all(np.linalg.norm(body.x - o.x) > dm for o in bodies if o.track != body.track)

    def act_local(self, i, view, info):
        A, b = self.dynamics.input_polytope()
        n_u = self.dynamics.n_u
        pairs = self.memory[i]
        contacts = [bd for bd in view.bodies if np.linalg.norm(bd.x - view.x) < self.spec.r_c]
        tracks = [bd.track for bd in contacts]
        for key in [k for k in pairs if k not in tracks]:
            del pairs[key]
        # (3) exchange on contact edges, from the previous step
        for bd in contacts:
            pair = pairs.get(bd.track)
            if pair is None or not pair.prev:
                continue
            P = pair.prev
            alpha, Z, dhat = P['alpha'], P['Z'], P['dhat']
            y_k = float(dhat @ bd.u_prev)
            y_i = float(-dhat @ P['u_i'])
            s_i = P['s_i']
            s_k = -(P['row_k'] + P['R_ki'])
            lam_k = self.ke * max(0.0, self.eps - s_k)
            lam_i = self.ke * max(0.0, self.eps - s_i)
            h_eff = -Z * self.spec.gamma / self.spec.kappa              # so that -kappa h_eff / 2 = (gamma/2) Z
            # pair-axis linearisation with the agent slack: R_eff makes -(alpha y + gamma Z / 2 + R_eff) = s
            Rk_eff = -s_k - alpha * y_k - 0.5 * self.spec.gamma * Z
            Ri_eff = -s_i - alpha * y_i - 0.5 * self.spec.gamma * Z
            pair.about_k.append(y_k, *linearise(s_k, Rk_eff, max(alpha, 1e-9), h_eff, self.spec.kappa, self.eps, self.ke))
            pair.k_about_i.append(y_i, *linearise(s_i, Ri_eff, max(alpha, 1e-9), h_eff, self.spec.kappa, self.eps, self.ke))
            m = P['follow_k'] * P['follow_ki'] if self.law == 'mutual' else 1.0
            pair.r -= m * self.gain * (lam_i - lam_k)
            info['lam_hat'][(i, bd.track)] = lam_k
        # (1) rooms per contact
        geo = []
        for bd in contacts:
            pair = pairs.get(bd.track)
            if pair is None:
                pair = pairs[bd.track] = Pair(self.belief(), self.belief())
            Z, alpha, dhat, _, _ = self.pair_geo(view.x, bd.x)
            geo.append((bd, pair, Z, alpha, dhat))
        G = np.zeros(n_u); const = self.spec.constant(); R_i = 0.0
        if geo:
            P_ = len(geo)
            r = np.array([g[1].r for g in geo]); alpha = np.array([g[3] for g in geo])
            h_eff = np.array([-g[2] * self.spec.gamma / self.spec.kappa for g in geo])
            A_, th_, fol_ = self.room_batch([g[1].about_k for g in geo] + [g[1].k_about_i for g in geo],
                                            np.concatenate([r, -r]), np.tile(alpha, 2), np.tile(h_eff, 2), view.v_env)
            for j, (bd, pair, Z, alpha_j, dhat) in enumerate(geo):
                R_ik, R_ki = float(A_[j]), float(A_[P_ + j])
                if self.coverage == 'closest':
                    if not self.closest(view.x, bd, view.bodies):
                        R_ik = pair.r
                    # replica of k's rule: is k the closest to i among the bodies i sees (approximation of k's view)
                    if not all(np.linalg.norm(view.x - o.x) > np.linalg.norm(view.x - bd.x)
                               for o in view.bodies if o.track != bd.track):
                        R_ki = -pair.r
                # k's row over the contacts of k that i sees (i itself included)
                # replica='seen': all contacts of k that i sees (k's other rooms taken as 0);
                # replica='pair': k's row restricted to the (k, i) pair (k's other contacts ignored, constant kept)
                others = [view.x] + ([o.x for o in view.bodies if o.track != bd.track] if self.replica == 'seen' else [])
                row_k = self.row_of(bd.x, bd.u_prev, others)
                pair.prev = dict(alpha=alpha_j, Z=Z, dhat=dhat, R_ik=R_ik, R_ki=R_ki, follow_k=float(fol_[j]),
                                 follow_ki=float(fol_[P_ + j]), row_k=row_k)
                G += -alpha_j * dhat                      # grad_d Z_ik = beta * dhat, beta = -alpha
                const += 0.5 * self.spec.gamma * Z
                R_i += R_ik
                info['r'][(i, bd.track)], info['theta'][(i, bd.track)] = pair.r, float(th_[j])
                info['follow'][(i, bd.track)] = float(fol_[j])
        # (2) one-row QP: [u, p, z]
        w, u0 = view.weight, view.u_nom
        Pm = np.zeros((n_u + 2, n_u + 2)); Pm[:n_u, :n_u] = w * np.eye(n_u); Pm[n_u, n_u] = self.ke
        q = np.concatenate([-w * u0, [0.0, self.M]])
        Gm = [np.hstack([A, np.zeros((len(b), 2))]), np.hstack([np.zeros((2, n_u)), -np.eye(2)]),
              np.concatenate([G, [-1.0, 0.0]])[None], np.concatenate([G, [0.0, -1.0]])[None]]
        hm = [b, np.zeros(2), [-(const + R_i + self.eps)], [-(const + R_i)]]
        sol, how = solve_qp(Pm, q, np.vstack(Gm), np.concatenate(hm))
        info['slsqp'] += how == 'slsqp'
        u = sol[:n_u]
        s_i = -(float(G @ u) + const + R_i)
        lam = self.ke * max(0.0, self.eps - s_i)
        info['lam_agent'][i] = lam
        info['slack_agent'][i] = s_i
        for bd, pair, *_ in geo:
            pair.prev.update(u_i=u.copy(), s_i=s_i)
            info['mu'][(i, bd.track)] = lam
        return u

    def act(self, obs):
        info = dict(r={}, mu={}, lam_hat={}, theta={}, follow={}, delta={}, cov={}, nu={}, lam_agent={}, slack_agent={}, slsqp=0)
        U = np.array([self.act_local(i, obs.local(i), info) for i in range(obs.n_agents)])
        return U, info
