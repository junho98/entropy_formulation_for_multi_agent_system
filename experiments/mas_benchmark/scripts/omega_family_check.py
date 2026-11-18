"""Internal check (2026-11-16): a belief over the neighbour's cost weight omega_k.

The hypothesis family (tau, u_bar) becomes (tau, u_bar, omega) with omega in a public set OMEGAS and an equal prior;
the self-model response in the layer uses omega: a = omega/(omega + k_e alpha^2), b scaled by (1 + k_e alpha^2)/
(omega + k_e alpha^2) (free and wall regimes do not depend on omega). The EVaR room is the same certified bound over the
enlarged family (4 |OMEGAS| finite rows + tau = inf). With beta on, the neighbour's effective weight beta_k omega_k is
NOT modelled; only the public set {1, 3}. Nothing here is a package option: the classes are subclasses in this script;
with OMEGAS = (1,) they reproduce the package classes (checked by --sanity).

    python scripts/omega_family_check.py [--sanity] [--workers 9]   -> results/grid2x3/diag/omega_family.jsonl
"""
import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
from scipy.special import log_ndtr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_grid2x3_ts as G                                                # noqa: E402
from mas_benchmark.analyzers import Cost, Safety                          # noqa: E402
from mas_benchmark.analyzers.agreement import encounters                  # noqa: E402
from mas_benchmark.configs import RHO, build                              # noqa: E402
from mas_benchmark.core import simulate                                   # noqa: E402
from mas_benchmark.dynamics import SingleIntegrator                       # noqa: E402
from mas_benchmark.scenarios import make_scenario                         # noqa: E402
from mas_benchmark.solvers.thermo import Thermo                           # noqa: E402
from mas_benchmark.solvers.thermo.beta import ThermoBeta                  # noqa: E402
from mas_benchmark.solvers.thermo.belief import TAUS, TemperatureBelief   # noqa: E402
from mas_benchmark.solvers.thermo.bound import (certified_bound_batch, log_mgf_atom_exp_batch,  # noqa: E402
                                                log_mgf_uniform_max_batch)

OUT = G.OUT / 'diag' / 'omega_family.jsonl'


class OmegaBelief(TemperatureBelief):
    """Posterior over (omega, tau) with the intent integrated out; rows ordered omega-major."""
    omegas = (1.0, 3.0)

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        no = len(self.omegas)
        self.log_prior = np.append(np.tile(self.log_prior[:-1] - np.log(no), no), self.log_prior[-1])

    def posterior(self, v_cap):
        no = len(self.omegas)
        if not self.obs:
            return self.log_prior.copy(), np.zeros(no * len(TAUS)), np.ones(no * len(TAUS))
        y, a1, b1 = map(np.array, zip(*self.obs))
        n = len(y)
        s2 = TAUS + self.sigma2
        lls, ms, vs = [], [], []
        layer = (a1 > 0) & (a1 < 1)
        K = np.where(layer, 1.0 / np.where(layer, a1, 1.0) - 1.0, 0.0)          # k_e alpha^2 in the layer
        for w in self.omegas:
            if w == 1.0:
                a, b = a1, b1
            else:
                a = np.where(layer, w / (w + K), a1)
                b = np.where(layer, b1 * (1.0 + K) / (w + K), b1)
            e = y - b
            aa, ae = a @ a, a @ e
            quad = (e @ e) / s2 - ae ** 2 / (s2 ** 2 * (1.0 + aa / s2))
            logdet = n * np.log(s2) + np.log1p(aa / s2)
            lls.append(-0.5 * (quad + logdet + n * np.log(2 * np.pi)))
            prec = 1.0 + aa / s2
            ms.append((ae / s2) / prec); vs.append(1.0 / prec)
        ll_inf = -n * np.log(2 * v_cap) if np.all(np.abs(y) <= v_cap + 1e-9) else -np.inf
        log_w = self.log_prior + np.append(np.concatenate(lls), ll_inf)
        log_w -= np.logaddexp.reduce(log_w)
        return log_w, np.concatenate(ms), np.concatenate(vs)

    def omega_mass(self, v_cap):
        log_w, _, _ = self.posterior(v_cap)
        w = np.exp(log_w[:-1]).reshape(len(self.omegas), len(TAUS)).sum(1)
        return w / max(w.sum(), 1e-300)


class OmegaMixin:
    omegas = (1.0, 3.0)

    def belief(self):
        b = OmegaBelief(self.window, self.sigma_o, self.follow_prior) if self.omegas != (1.0,) else super().belief()
        if self.omegas != (1.0,):
            b.omegas = self.omegas
            no = len(self.omegas)
            b.log_prior = np.append(np.tile(TemperatureBelief(self.window, self.sigma_o, self.follow_prior).log_prior[:-1]
                                            - np.log(no), no), b.log_prior[-1])
        return b

    def room_batch(self, beliefs, r, alpha, h, v_cap, delta=None):
        if self.omegas == (1.0,):
            return super().room_batch(beliefs, r, alpha, h, v_cap, delta)
        taus = np.tile(TAUS, len(self.omegas))
        kappa = self.spec.kappa
        post = [b.posterior(v_cap) for b in beliefs]
        log_w = np.array([p[0] for p in post])
        m = np.array([p[1] for p in post]); v = np.array([p[2] for p in post])
        g0 = -0.5 * kappa * h
        mu = np.minimum(alpha[:, None] * m + g0[:, None], r[:, None])
        sd = alpha[:, None] * np.sqrt(taus[None] + v + self.sigma_o ** 2)
        log_q = log_ndtr((mu - r[:, None]) / sd)
        rows = log_mgf_atom_exp_batch(r, log_q, self.M / taus)
        unif = log_mgf_uniform_max_batch(r, g0 - alpha * v_cap, g0 + alpha * v_cap)
        A, theta = certified_bound_batch(log_w, np.concatenate([rows, unif[:, None]], axis=1),
                                         self.delta if delta is None else delta)
        return A, theta, -np.expm1(log_w[:, -1])

    def act_local(self, i, view, info):
        u = super().act_local(i, view, info)
        if self.omegas != (1.0,):
            om = info.setdefault('omega_post', {})
            for t, pr in self.memory[i].items():
                om[(i, t)] = pr.about_k.omega_mass(view.v_env).tolist()
        return u


class ThermoOmega(OmegaMixin, Thermo):
    pass


class ThermoBetaOmega(OmegaMixin, ThermoBeta):
    pass


def solver_for(method, family, cell):
    _, spec = build('ours', **G.OURS)
    om = (1.0,) if family in ('current', 'omega1') else (1.0, 3.0)
    if method == 'ours':
        s = ThermoOmega(law='mutual', **dict(G.OURS, eps=0.1))
    else:
        cb = json.loads((G.OUT / 'cbar.json').read_text())[cell]
        s = ThermoBetaOmega(**dict(G.OURS, eps=0.1, W0=4.22, cbar=cb, per_step=True, beta_max=8.0,
                                   tau_leak=float('inf')))
    s.omegas = om
    return s, spec


def run(method, family, cell, seed):
    t0 = time.time()
    sol, spec = solver_for(method, family, cell)
    log = simulate(make_scenario(cell), SingleIntegrator(), spec, sol, 120.0, 0.02, seed)
    log.rho = RHO
    f = 0.5 * log.weights[None] * np.sum((log.u - log.u_nom) ** 2, axis=2) * log.dt
    W = f.sum(0)
    N = log.x.shape[1]
    wall = time.time() - t0
    row = dict(method=method, family=family, cell=cell, seed=seed, wall_s=round(wall, 1),
               ms_per_step=round(1000 * wall / len(log.info), 2), W_cv=float(W.std() / W.mean()),
               W_range=float(np.ptp(W)), **Cost()(log), **Safety()(log))
    row['imb_end'] = float(np.median([abs(e['mu_i'][-1] - e['mu_k'][-1]) / (e['mu_i'][-1] + e['mu_k'][-1])
                                      for e in encounters(log, 1e-6)] or [np.nan]))
    cov = [c for inf in log.info for c in inf.get('cov', {}).values()]
    room = [inf['r'][k] + inf['cov'][k] for inf in log.info for k in inf.get('cov', {})]
    row['mean_U'], row['mean_R'] = float(np.mean(cov)), float(np.mean(room))
    if family == 'omega':
        tracks = np.asarray(log.meta['tracks'])
        body = np.empty_like(tracks); body[tracks] = np.arange(len(tracks))
        w_true = np.asarray(log.weights)
        mass = []
        for inf in log.info:
            for (i, t), p in inf.get('omega_post', {}).items():
                b = int(body[t])
                if b < N:
                    mass.append(p[0] if w_true[b] == 1.0 else p[1])
        row['mass_true_omega'] = float(np.mean(mass)) if mass else np.nan
    return row


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--sanity', action='store_true')
    ap.add_argument('--workers', type=int, default=9)
    a = ap.parse_args()
    OUT.parent.mkdir(exist_ok=True)
    if a.sanity:
        J = [('ours', 'omega1', 'HET-E0+ts1.5', 0), ('beta', 'omega1', 'HET-E0+ts1.5', 0)]
    else:
        J = [(m, fam, c + '+ts1.5', 0) for c in ('HET-E0', 'HET-E8') for m in ('ours', 'beta')
             for fam in ('current', 'omega')] + [('ours', 'omega', 'HOM-E8+ts1.5', 0)]
    print(len(J), 'runs', flush=True)
    with ProcessPoolExecutor(min(a.workers, len(J))) as ex, OUT.open('a') as fh:
        for fut in as_completed([ex.submit(run, *j) for j in J]):
            r = fut.result()
            fh.write(json.dumps(r) + '\n'); fh.flush()
            print(r['method'], r['family'], r['cell'], r['wall_s'], flush=True)
    print('done', flush=True)
