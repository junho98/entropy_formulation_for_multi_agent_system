"""Certified bound (Def. 2.4): A[X] = inf_theta theta ln E_w e^{X/theta} + theta ln(1/delta).

X = max(c_k, r) per hypothesis, with closed-form log-MGFs on a theta grid (Sec. 11: 400 log-spaced values in [1e-4, 50]).
"""
import numpy as np
from scipy.special import log_ndtr, logsumexp

THETAS = np.logspace(-4, np.log10(50.0), 400)


def certified_bound(log_w, log_mgf, delta, thetas=THETAS):
    """log_w (H,), log_mgf (H, T) = ln E_h e^{X/theta}. Returns (A, theta*)."""
    obj = thetas * (logsumexp(log_w[:, None] + log_mgf, axis=0) + np.log(1.0 / delta))
    j = int(np.argmin(obj))
    return float(obj[j]), float(thetas[j])


def log_mgf_atom_exp(r, log_q, rate, thetas=THETAS):
    """X = r + B * E, B ~ Bernoulli(q), E ~ Exp(rate): the agreement, exceeded with prob q by an exponential excess."""
    t = 1.0 / thetas
    out = np.full_like(t, np.inf)
    ok = t < rate
    log_ratio = np.log(rate) - np.log(rate - t[ok])           # ln E e^{tE} >= 0
    # ln((1-q) + q e^{log_ratio}) = ln(1 + q (e^{log_ratio} - 1))
    out[ok] = r * t[ok] + np.logaddexp(np.log1p(-np.exp(log_q)), log_q + log_ratio)
    return out


def log_mgf_uniform_max(r, gmin, gmax, thetas=THETAS):
    """X = max(U, r), U ~ Uniform[gmin, gmax]."""
    t = 1.0 / thetas
    if r >= gmax:
        return r * t
    L = gmax - gmin
    rr = max(r, gmin)
    atom = np.log((rr - gmin) / L) + rr * t if rr > gmin else np.full_like(t, -np.inf)
    cont = gmax * t + np.log(-np.expm1(-(gmax - rr) * t)) - np.log(L * t)
    return np.logaddexp(atom, cont)


def log_gauss_exceed(mu, sigma, r):
    """ln Pr(N(mu, sigma^2) > r)."""
    return float(log_ndtr((mu - r) / sigma))


# ---- batched versions: P bounds at once (same formulas as above) ----

def _logsumexp0(a):
    """logsumexp over axis 0 of (H, ...) with -inf entries allowed."""
    m = np.max(a, axis=0)
    m_safe = np.where(np.isfinite(m), m, 0.0)
    with np.errstate(divide='ignore', over='ignore', invalid='ignore'):
        return np.log(np.sum(np.exp(a - m_safe), axis=0)) + m_safe


def certified_bound_batch(log_w, log_mgf, delta, thetas=THETAS):
    """log_w (P, H), log_mgf (P, H, T), delta scalar or (P,). Returns (A (P,), theta* (P,))."""
    lse = _logsumexp0(np.moveaxis(log_w[:, :, None] + log_mgf, 1, 0))      # (P, T)
    S = np.broadcast_to(np.log(1.0 / np.asarray(delta, dtype=float)), (len(lse),))
    obj = thetas[None] * (lse + S[:, None])
    j = np.argmin(obj, axis=1)
    return obj[np.arange(len(j)), j], thetas[j]


def log_mgf_atom_exp_batch(r, log_q, rate, thetas=THETAS):
    """r (P,), log_q (P, H), rate (H,) -> (P, H, T)."""
    t = 1.0 / thetas
    ok = t[None, :] < rate[:, None]                                          # (H, T)
    with np.errstate(divide='ignore', invalid='ignore'):
        log_ratio = np.where(ok, np.log(rate)[:, None] - np.log(np.where(ok, rate[:, None] - t[None], 1.0)), 0.0)
    lq = log_q[:, :, None]
    out = r[:, None, None] * t[None, None] + np.logaddexp(np.log1p(-np.exp(lq)), lq + log_ratio[None])
    return np.where(ok[None], out, np.inf)


def log_mgf_uniform_max_batch(r, gmin, gmax, thetas=THETAS):
    """r, gmin, gmax (P,) -> (P, T) for X = max(U, r), U ~ Uniform[gmin, gmax]."""
    t = 1.0 / thetas
    L = gmax - gmin
    rr = np.maximum(r, gmin)
    with np.errstate(divide='ignore', invalid='ignore', over='ignore'):
        atom = np.where((rr > gmin)[:, None], np.log((rr - gmin) / L)[:, None] + rr[:, None] * t[None], -np.inf)
        cont = gmax[:, None] * t[None] + np.log(-np.expm1(-(gmax - rr)[:, None] * t[None])) - np.log(L[:, None] * t[None])
        out = np.logaddexp(atom, cont)
    return np.where((r >= gmax)[:, None], r[:, None] * t[None], out)
