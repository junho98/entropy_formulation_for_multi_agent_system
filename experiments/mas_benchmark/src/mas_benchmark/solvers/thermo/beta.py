"""'Beta': the final configuration with one change, agent i weighs its own cost by beta_i.

  W_i      ledger of the base cost: dW_i/dt = 1/2 w_i |u_i - u0_i|^2 - kappa_W W_i (kappa_W = 0: no leak);
  beta_ik  = min(exp(W_i / W0), beta_max), evaluated when contact k starts (agreement created) and frozen for it;
  QP       the local problem uses the weight w_i * beta_i^QP with beta_i^QP = max over i's current contacts of the
           frozen beta_ik (the current exp(W_i/W0), capped, when i has no contact);
           per_step=True (2026-11-15, paper v42 Def. 6.5): beta_i^QP = the current value at every step, no freezing
           (the freeze served only the w~ reading, which is off by default);
  belief   default: neighbours at the public w = 1 (no reading). Options: read=True reads the neighbour's effective
           weight w~_k = w_k beta_k from the first `read_steps` exchange steps of the contact (MAP over a grid, ties to the
           smallest), then freezes it; read_constrained=True reads on the first constrained steps. The in-layer
           coefficient uses w~: a = w~/(w~ + k_e alpha^2).
           i replicates k's reading of i by running the same rule on i's own actions (same observations), so the
           replicated belief of k about i uses the w~_i that k decides.
Exchange (mutual law, default step 1/(2 k_e)), room and covers are unchanged; no mu anywhere.
"""
import dataclasses

import numpy as np

from .fair import lin_w, marginal_ll
from .solver import Thermo

GRID = (1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0)


class ThermoBeta(Thermo):
    def __init__(self, eps=0.1, W0=np.inf, tau_leak=np.inf, beta_max=4.0, read_steps=25, s2=1e-2 + 1e-4,
                 read_constrained=False, read=False, cbar=None, per_step=False, **kw):
        kw.setdefault('law', 'mutual')
        super().__init__(eps=eps, **kw)
        self.W0, self.tau_leak, self.beta_max, self.read_steps, self.s2 = W0, tau_leak, beta_max, read_steps, s2
        # default (decision of 2026-11-13): no w~ reading, neighbours stay at the public w = 1. read=True restores the
        # reading on the first read_steps steps of a contact; read_constrained=True reads on constrained steps only.
        self.per_step = per_step
        self.cbar = cbar          # centred beta: clip(exp((W_i - cbar t)/W0), 1/beta_max, beta_max); cbar is public
        self.read_on = read or read_constrained
        self.read_constrained = read_constrained
        self.name = (f'beta_eps{eps:g}_W0{W0:g}_leak{tau_leak:g}' + ('_rc' if read_constrained else '')
                     + ('_read' if read and not read_constrained else '') + ('' if beta_max == 4.0 else f'_bmax{beta_max:g}')
                     + ('' if cbar is None else f'_cbar{cbar:g}') + ('_step' if per_step else ''))

    def reset(self, scenario, dynamics, spec, dt):
        super().reset(scenario, dynamics, spec, dt)
        self.W = np.zeros(scenario.n_agents)

    def beta_now(self, i):
        if not np.isfinite(self.W0):
            return 1.0
        if self.cbar is not None:
            x = (self.W[i] - self.cbar * self._t) / self.W0
            return float(np.clip(np.exp(x), 1.0 / self.beta_max, self.beta_max))
        return float(min(np.exp(self.W[i] / self.W0), self.beta_max))

    @staticmethod
    def read(log, s2):
        """MAP effective weight over GRID from a list of (y, s, R, alpha, h, kappa, eps, ke) records; ties to the smallest."""
        if not log:
            return 1.0
        y = np.array([o[0] for o in log])
        best, best_ll = GRID[0], -np.inf
        for w in GRID:
            ab = [lin_w(o[1], o[2], o[3], o[4], o[5], o[6], o[7], w) for o in log]
            ll = marginal_ll(y, np.array([a for a, _ in ab]), np.array([b for _, b in ab]), s2)
            if ll > best_ll + 1e-9:
                best, best_ll = w, ll
        return best

    def exchange(self, body, pair):
        P = pair.prev
        d, alpha, h, kappa = P['d'], P['alpha'], P['h'], self.spec.kappa
        dhat = d / np.linalg.norm(d)
        y_k = float(dhat @ body.u_prev)
        y_i = float(-dhat @ P['u_i'])
        s_k = -(alpha * y_k - 0.5 * kappa * h + P['R_ki'])
        s_i = -(alpha * y_i - 0.5 * kappa * h + P['R_ik'])
        lam_k = self.ke * max(0.0, self.eps - s_k)
        lam_i = self.ke * max(0.0, self.eps - s_i)
        # effective-weight reading (i's of k, and i's replica of k's reading of i), first read_steps steps
        if self.read_on and pair.wt_k is None and (not self.read_constrained or s_i < self.eps or s_k < self.eps):
            pair.rlog_k.append((y_k, s_k, P['R_ki'], alpha, h, kappa, self.eps, self.ke))
            pair.rlog_i.append((y_i, s_i, P['R_ik'], alpha, h, kappa, self.eps, self.ke))
            if len(pair.rlog_k) >= self.read_steps:
                pair.wt_k = self.read(pair.rlog_k, self.s2)
                pair.wt_i_rep = self.read(pair.rlog_i, self.s2)
        wk = pair.wt_k if pair.wt_k is not None else 1.0
        wi = pair.wt_i_rep if pair.wt_i_rep is not None else 1.0
        pair.about_k.append(y_k, *lin_w(s_k, P['R_ki'], alpha, h, kappa, self.eps, self.ke, wk))
        pair.k_about_i.append(y_i, *lin_w(s_i, P['R_ik'], alpha, h, kappa, self.eps, self.ke, wi))
        m = P['follow_k'] * P['follow_ki'] if self.law == 'mutual' else 1.0
        pair.r -= m * self.gain * (lam_i - lam_k)
        return lam_i, lam_k

    def act_local(self, i, view, info):
        pairs = self.memory[i]
        tracks = {b.track for b in view.bodies}
        self._t = view.t
        b_now = self.beta_now(i)
        betas = [pairs[t].beta if t in pairs and hasattr(pairs[t], 'beta') else b_now for t in tracks]
        b_qp = b_now if self.per_step else (max(betas) if betas else b_now)
        new = tracks - set(pairs)
        u = super().act_local(i, dataclasses.replace(view, weight=view.weight * b_qp), info)
        for t in tracks:
            pr = pairs[t]
            if t in new or not hasattr(pr, 'beta'):
                pr.beta = b_now
                pr.wt_k, pr.wt_i_rep, pr.rlog_k, pr.rlog_i = None, None, [], []
            if pr.wt_k is not None:
                info['wt_hat'][(i, t)] = pr.wt_k
        info['w_eff'][i] = view.weight * b_qp
        info['beta'][i] = b_qp
        info['n_contacts'][i] = len(tracks)
        for t in tracks:
            info['beta_pair'][(i, t)] = pairs[t].beta
        f = 0.5 * view.weight * float(np.sum((u - view.u_nom) ** 2))
        leak = 0.0 if not np.isfinite(self.tau_leak) else self.W[i] / self.tau_leak
        self.W[i] += (f - leak) * self.dt
        return u

    def act(self, obs):
        info = dict(r={}, mu={}, lam_hat={}, theta={}, follow={}, delta={}, cov={}, nu={}, slsqp=0,
                    wt_hat={}, w_eff={}, beta={}, n_contacts={}, beta_pair={})
        U = np.array([self.act_local(i, obs.local(i), info) for i in range(obs.n_agents)])
        info['W'] = self.W.copy()
        return U, info
