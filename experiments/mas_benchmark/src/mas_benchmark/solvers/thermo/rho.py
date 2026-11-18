"""Ablation (2026-11-15): exchange with transmissions, as in Thm 5.2 / Def. 5.1 (v42 sets rho = 1).

  r_ik <- r_ik - m_ik (lam_ik rho_ik - lam_hat_ki rho_hat_ki) / (2 k_e),
  rho_ik = dR_ik/dr_ik  (R_ik = A[max(c_k, r_ik)], own belief about k),
  rho_hat_ki = dR_ki/dr_ki at r_ki = -r_ik (replica of k's belief about i),
both by a central difference at the minimising theta (envelope theorem), from the rooms of the previous step. Both
members of a pair compute the same two numbers from the same windows, so the copies stay opposite. Everything else as
Thermo(law='mutual').
"""
import numpy as np
from scipy.special import log_ndtr

from .belief import TAUS
from .bound import THETAS, _logsumexp0, log_mgf_atom_exp_batch, log_mgf_uniform_max_batch
from .solver import Thermo

EPS_R = 1e-4


class ThermoRho(Thermo):
    def __init__(self, **kw):
        kw.setdefault('law', 'mutual')
        super().__init__(**kw)
        self.name += '_rho'

    def _rows(self, log_w, m, v, alpha, h, r, v_cap):
        g0 = -0.5 * self.spec.kappa * h
        mu = np.minimum(alpha[:, None] * m + g0[:, None], r[:, None])
        sd = alpha[:, None] * np.sqrt(TAUS[None] + v + self.sigma_o ** 2)
        log_q = log_ndtr((mu - r[:, None]) / sd)
        rows = log_mgf_atom_exp_batch(r, log_q, self.M / TAUS)
        unif = log_mgf_uniform_max_batch(r, g0 - alpha * v_cap, g0 + alpha * v_cap)
        return _logsumexp0(np.moveaxis(log_w[:, :, None] + np.concatenate([rows, unif[:, None]], 1), 1, 0))  # (P, T)

    def room_batch(self, beliefs, r, alpha, h, v_cap, delta=None):
        A, theta, fol = super().room_batch(beliefs, r, alpha, h, v_cap, delta)
        post = [b.posterior(v_cap) for b in beliefs]
        log_w = np.array([p[0] for p in post]); m = np.array([p[1] for p in post]); v = np.array([p[2] for p in post])
        j = np.searchsorted(THETAS, theta)                              # index of theta* on the grid
        idx = np.arange(len(r))
        lp = self._rows(log_w, m, v, alpha, h, r + EPS_R, v_cap)[idx, j]
        lm = self._rows(log_w, m, v, alpha, h, r - EPS_R, v_cap)[idx, j]
        self._rho = np.clip(theta * (lp - lm) / (2 * EPS_R), 0.0, 1.0)
        return A, theta, fol

    def act_local(self, i, view, info):
        self._rho = None
        u = super().act_local(i, view, info)
        if self._rho is not None:
            P = len(view.bodies)
            for j, b in enumerate(view.bodies):
                pr = self.memory[i][b.track].prev
                pr['rho_ik'], pr['rho_ki'] = float(self._rho[j]), float(self._rho[P + j])
                info.setdefault('rho', {})[(i, b.track)] = pr['rho_ik']
        return u

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
        from .belief import linearise
        pair.about_k.append(y_k, *linearise(s_k, P['R_ki'], alpha, h, kappa, self.eps, self.ke))
        pair.k_about_i.append(y_i, *linearise(s_i, P['R_ik'], alpha, h, kappa, self.eps, self.ke))
        m = P['follow_k'] * P['follow_ki']
        pair.r -= m * self.gain * (lam_i * P.get('rho_ik', 1.0) - lam_k * P.get('rho_ki', 1.0))
        return lam_i, lam_k
