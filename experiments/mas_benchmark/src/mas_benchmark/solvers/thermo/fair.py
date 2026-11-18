"""Fairness over time: own cost memory in the exchange (extension of the final configuration).

Final configuration (pairwise, mutual trust, step 1/(2 k_e), delta = 0.05 per neighbour) plus:
  W_i      accumulated own cost, W_i += f_i(u_i) dt, f_i = w_i/2 |u_i - u0_i|^2 (own quantities only);
  mu_ik    = W_i / W0, frozen for contact k when the agreement starts (first exchange of the contact);
  exchange r_ik <- r_ik - m_ik / (2 k_e) [(1 + mu_ik) lam_i - (1 + mu_hat_k) lam_hat_k];
  belief   k's weight w_hat in {1, 3}: MAP of the window likelihood over the first 25 exchange steps, then fixed;
           k's memory mu in {0, .5, 1, 2, 4}: for each hypothesis a shadow r_ki^(mu) of k's copy, evolved by k's rule
           (k's price under that shadow against i's price weighted by i's true (1 + mu_ik)), started at 0 with the
           agreement; window likelihood (50 steps) of k's observed approach speed under k's local problem with that
           room and w_hat; mu_hat = posterior mean;
  cover    under the following hypotheses the agreement atom r_ik is replaced by r_ik + (-r_ki^(mu) - r_ik)_+, mixed
           over the mu posterior (the gap between k's actual allowance -r_ki and the one i assumes, r_ik);
  replica  k's room toward i uses the posterior-mean shadow instead of -r_ik.
Choices where the spec is open are listed in results/cost_memory.md.
"""
from collections import deque

import numpy as np

from .belief import TAUS
from .bound import certified_bound_batch, log_mgf_atom_exp_batch, log_mgf_uniform_max_batch
from .solver import Thermo
from scipy.special import log_ndtr

MUS = np.array([0.0, 0.5, 1.0, 2.0, 4.0])
WS = (1.0, 3.0)


def lin_w(s, R, alpha, h, kappa, eps, ke, w, tol=1e-6):
    """linearise() with the responder's weight w: layer a = w/(w + ke alpha^2), b = -ke alpha c0/(w + ke alpha^2)."""
    if s >= eps - tol:
        return 1.0, 0.0
    if s > tol:
        den = w + ke * alpha ** 2
        return w / den, -ke * alpha * (eps + R - 0.5 * kappa * h) / den
    return 0.0, (0.5 * kappa * h - R) / max(alpha, 1e-9)


def marginal_ll(y, a, b, s2):
    """ln N(y; b, s2 I + a a^T) (intent u_bar ~ N(0, 1) integrated out)."""
    e = y - b
    n, aa, ae = len(y), a @ a, a @ e
    quad = (e @ e) / s2 - ae ** 2 / (s2 ** 2 * (1.0 + aa / s2))
    return -0.5 * (quad + n * np.log(s2) + np.log1p(aa / s2) + n * np.log(2 * np.pi))


class ThermoFair(Thermo):
    def __init__(self, eps=0.1, W0=np.inf, w_fix_steps=25, window=50, s2=1e-2 + 1e-4, fix=None, mu_max=4.0, **kw):
        """fix=None: as first specified. fix='fixed' / 'adaptive' (follow-up (a)+(b)): mu likelihood and w_hat only on
        constrained steps (s_i < eps or s_k < eps), no sliding window, posterior frozen otherwise; mu clipped to
        [0, mu_max] on both sides; exchange (and shadow) step 1/(2 k_e (1 + mu_max)) ('fixed') or
        1/(2 k_e (1 + max(mu_i, mu_k))) ('adaptive')."""
        kw.setdefault('law', 'mutual')
        super().__init__(eps=eps, **kw)
        self.W0, self.w_fix_steps, self.win, self.s2 = W0, w_fix_steps, window, s2
        self.fix, self.mu_max = fix, mu_max
        self.name = f'fair_eps{eps:g}_W0{W0:g}' + ('' if fix is None else f'_{fix}')

    def reset(self, scenario, dynamics, spec, dt):
        super().reset(scenario, dynamics, spec, dt)
        self.W = np.zeros(scenario.n_agents)
        self._cur = None

    # ---- per-contact state stored on the Pair object ----
    def _init_fair(self, pair, i):
        pair.mu_own = self.W[i] / self.W0 if np.isfinite(self.W0) else 0.0
        if self.fix is not None:
            pair.mu_own = min(max(pair.mu_own, 0.0), self.mu_max)
        pair.ever_constrained = False
        pair.n_ex = 0
        pair.wlog = {w: [] for w in WS}            # (y, a, b) per weight hypothesis, first w_fix_steps steps
        pair.w_hat = None
        pair.shadow = np.zeros(len(MUS))           # r_ki^(mu)
        pair.muwin = deque(maxlen=self.win if self.fix is None else None)   # (y, a, b_mu (len MUS))
        pair.mu_post = np.full(len(MUS), 1.0 / len(MUS))

    def mu_hat(self, pair):
        return float(pair.mu_post @ MUS) if hasattr(pair, 'mu_post') else 0.0

    def exchange(self, body, pair):
        i = self._cur
        if not hasattr(pair, 'mu_own'):
            self._init_fair(pair, i)
        P = pair.prev
        d, alpha, h, kappa = P['d'], P['alpha'], P['h'], self.spec.kappa
        dhat = d / np.linalg.norm(d)
        y_k = float(dhat @ body.u_prev)
        y_i = float(-dhat @ P['u_i'])
        s_k = -(alpha * y_k - 0.5 * kappa * h + P['R_ki'])
        s_i = -(alpha * y_i - 0.5 * kappa * h + P['R_ik'])
        lam_k = self.ke * max(0.0, self.eps - s_k)
        lam_i = self.ke * max(0.0, self.eps - s_i)
        # temperature belief windows as in the final configuration (weight from w_hat once fixed)
        wk = pair.w_hat if pair.w_hat is not None else 1.0
        pair.about_k.append(y_k, *lin_w(s_k, P['R_ki'], alpha, h, kappa, self.eps, self.ke, wk))
        pair.k_about_i.append(y_i, *lin_w(s_i, P['R_ik'], alpha, h, kappa, self.eps, self.ke, 1.0))
        constrained = (s_i < self.eps) or (s_k < self.eps)
        pair.ever_constrained = pair.ever_constrained or constrained
        informative = constrained if self.fix is not None else True
        # weight hypotheses: first w_fix_steps (informative) exchange steps, then MAP fixed
        if pair.w_hat is None and informative:
            for w in WS:
                pair.wlog[w].append((y_k, *lin_w(s_k, P['R_ki'], alpha, h, kappa, self.eps, self.ke, w)))
            if len(pair.wlog[WS[0]]) >= self.w_fix_steps:
                lls = {w: marginal_ll(*map(np.array, zip(*pair.wlog[w])), self.s2) for w in WS}
                pair.w_hat = max(lls, key=lls.get)
        # mu hypotheses: shadows of k's copy, k's slack and predicted response under each
        R_sh = P['R_ki_bar'] + (pair.shadow - P['r_ki_bar'])           # room of k toward i under each shadow
        s_sh = -(alpha * y_k - 0.5 * kappa * h + R_sh)
        lam_sh = self.ke * np.maximum(0.0, self.eps - s_sh)
        ab = [lin_w(s, R, alpha, h, kappa, self.eps, self.ke, wk) for s, R in zip(s_sh, R_sh)]
        if informative:
            pair.muwin.append((y_k, np.array([x[0] for x in ab]), np.array([x[1] for x in ab])))
        if informative and len(pair.muwin) >= 2:
            y = np.array([o[0] for o in pair.muwin])
            A_ = np.array([o[1] for o in pair.muwin]); B_ = np.array([o[2] for o in pair.muwin])
            ll = np.array([marginal_ll(y, A_[:, m], B_[:, m], self.s2) for m in range(len(MUS))])
            ll -= ll.max()
            pair.mu_post = np.exp(ll) / np.exp(ll).sum()
        m_tr = P['follow_k'] * P['follow_ki'] if self.law == 'mutual' else 1.0
        # k's rule for each shadow: k moves its copy by its own weighted price against i's (true) weighted price
        mu_k = self.mu_hat(pair)
        if self.fix is None:
            g_sh = g_own = self.gain
        elif self.fix == 'fixed':
            g_sh = g_own = self.gain / (1.0 + self.mu_max)
        else:                                                      # adaptive: 1/(2 ke (1 + max(mu_i, mu_k)))
            g_sh = self.gain / (1.0 + np.maximum(MUS, pair.mu_own))
            g_own = self.gain / (1.0 + max(pair.mu_own, mu_k))
        pair.shadow -= m_tr * g_sh * ((1.0 + MUS) * lam_sh - (1.0 + pair.mu_own) * lam_i)
        # own exchange
        pair.r -= m_tr * g_own * ((1.0 + pair.mu_own) * lam_i - (1.0 + mu_k) * lam_k)
        pair.n_ex += 1
        return lam_i, lam_k

    def room_batch(self, beliefs, r, alpha, h, v_cap, delta=None):
        """Own rows: finite-temperature atoms mixed over the mu posterior with the gap added. Replica rows: the
        posterior-mean shadow of k's copy replaces -r_ik."""
        P2 = len(beliefs)
        P = P2 // 2
        r = np.array(r, dtype=float)
        pairs = self._batch_pairs
        for j in range(P):
            pr = pairs[j]
            if hasattr(pr, 'mu_post'):
                r[P + j] = float(pr.mu_post @ pr.shadow)
        kappa = self.spec.kappa
        post = [b.posterior(v_cap) for b in beliefs]
        log_w = np.array([p[0] for p in post]); m = np.array([p[1] for p in post]); v = np.array([p[2] for p in post])
        g0 = -0.5 * kappa * h
        mu_ = np.minimum(alpha[:, None] * m + g0[:, None], r[:, None])
        sd = alpha[:, None] * np.sqrt(TAUS[None] + v + self.sigma_o ** 2)
        log_q = log_ndtr((mu_ - r[:, None]) / sd)
        rows = log_mgf_atom_exp_batch(r, log_q, self.M / TAUS)                        # (P2, 4, T)
        for j in range(P):
            pr = pairs[j]
            if not hasattr(pr, 'mu_post'):
                continue
            gaps = np.maximum(-pr.shadow - r[j], 0.0)
            if not np.any(gaps > 0):
                continue
            mix = np.stack([log_mgf_atom_exp_batch(np.array([r[j] + g]), log_q[j:j + 1], self.M / TAUS)[0] for g in gaps])
            with np.errstate(divide='ignore'):
                lp = np.log(pr.mu_post)[:, None, None]
            mx = np.max(mix + lp, axis=0)
            mx_s = np.where(np.isfinite(mx), mx, 0.0)
            rows[j] = np.log(np.sum(np.exp(mix + lp - mx_s), axis=0)) + mx_s
        unif = log_mgf_uniform_max_batch(r, g0 - alpha * v_cap, g0 + alpha * v_cap)
        A, theta = certified_bound_batch(log_w, np.concatenate([rows, unif[:, None]], axis=1),
                                         self.delta if delta is None else delta)
        self._last_rep_r = r[P:].copy()
        return A, theta, -np.expm1(log_w[:, -1])

    def act_local(self, i, view, info):
        self._cur = i
        self._last_rep_r = None
        pairs = self.memory[i]
        # the order of view.bodies is the order of the batch rows
        self._batch_pairs = [pairs.get(b.track) for b in view.bodies]
        # pairs may be created inside super().act_local before room_batch; resolve lazily
        orig = self.room_batch

        def rb(beliefs, r, alpha, h, v_cap, delta=None):
            self._batch_pairs = [pairs[b.track] for b in view.bodies]
            return orig(beliefs, r, alpha, h, v_cap, delta)
        self.room_batch = rb
        try:
            u = super().act_local(i, view, info)
        finally:
            self.room_batch = orig
        rep = getattr(self, '_last_rep_r', None)
        for j, b in enumerate(view.bodies):
            pr = pairs[b.track]
            if rep is not None and j < len(rep) and pr.prev:
                pr.prev['r_ki_bar'] = float(rep[j]); pr.prev['R_ki_bar'] = pr.prev['R_ki']
            if hasattr(pr, 'mu_own'):
                info['mu_hat'][(i, b.track)] = self.mu_hat(pr)
                info['w_hat'][(i, b.track)] = pr.w_hat
                info['mu_own'][(i, b.track)] = pr.mu_own
                info['shadow_mean'][(i, b.track)] = float(pr.mu_post @ pr.shadow)
                info['ever_c'][(i, b.track)] = pr.ever_constrained
        f = 0.5 * view.weight * float(np.sum((u - view.u_nom) ** 2))
        self.W[i] += f * self.dt
        return u

    def act(self, obs):
        info = dict(r={}, mu={}, lam_hat={}, theta={}, follow={}, delta={}, cov={}, nu={}, slsqp=0,
                    mu_hat={}, w_hat={}, mu_own={}, shadow_mean={}, ever_c={})
        U = np.array([self.act_local(i, obs.local(i), info) for i in range(obs.n_agents)])
        info['W'] = self.W.copy()
        return U, info
