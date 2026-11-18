"""Internal exploration (2026-11-16): can a regime-dependent exchange step shrink the 'rest' of the cost gap to the
Oracle in E0 (rest = Ours no cover - tuned Oracle)? Nothing here is a package option: the variants are subclasses
defined in this script, and with mode=None they reproduce the package classes bitwise (checked against the grid rows).

A  regime-dependent step: when both sides of a pair are in the in-layer regime of the modelled response
   (0 < s < eps for i's own slack and for i's replica of k's slack; both members compute the same two numbers), the
   exchange step 1/(2 k_e) is multiplied by 4, 16 or 64, or replaced by the Newton-like step
   D / (k_e (a_i + a_k)), a = 1/(1 + k_e alpha^2) (public unit weight), clipped to the trust region
   min(distance of s_i, s_k to the next breakpoint 0 or eps) / max(a_i, a_k) (floored at region_floor) - the clipping
   rule of the package's step='region', applied only in the layer. Otherwise the default step.
B  diagnostic, privileged (not a method): the central problem with the same layer, i.e. the limit of a perfect
   exchange. At exchange equilibrium both sides of a pair have equal slack, so the pair costs
   k_e (eps + c/2)_+^2 + 2 M (c/2)_+ ; one central QP over all inputs, team pairs within sensing range.
C  references on the same seed.

    python scripts/exchange_step_test.py [--seeds 0] [--only best]   -> results/grid2x3/diag/exchange_step.jsonl
"""
import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
from scipy.linalg import block_diag

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_grid2x3_ts as G                                                # noqa: E402
import run_tuning as T                                                    # noqa: E402
from mas_benchmark.analyzers import AgreementGap, Cost, Safety            # noqa: E402
from mas_benchmark.analyzers.agreement import encounters                  # noqa: E402
from mas_benchmark.configs import RHO, build                              # noqa: E402
from mas_benchmark.core import Solver, simulate                           # noqa: E402
from mas_benchmark.dynamics import SingleIntegrator                       # noqa: E402
from mas_benchmark.scenarios import make_scenario                         # noqa: E402
from mas_benchmark.solvers.thermo import Thermo                           # noqa: E402
from mas_benchmark.solvers.thermo.beta import ThermoBeta                  # noqa: E402
from mas_benchmark.solvers.thermo.fair import lin_w                       # noqa: E402
from mas_benchmark.utils.qp import solve_qp                               # noqa: E402

OUT = G.OUT / 'diag' / 'exchange_step.jsonl'
MODES = ('x4', 'x16', 'x64', 'newton')     # also 'x8', 'x32', 'pub', 'sec' via --only


class StepMixin:
    """gain_for with a larger step inside the layer (mode None: the package's fixed step).
    'pub': public-bound step D / (2 k_e a_pub w_max). 'sec': measured stiffness, step D / G_hat with G_hat the mean of
    the last SEC_N secants (D_t - D_t-1)/(r_t - r_t-1) clipped to [2 k_e a_pub w_min, 2 k_e a_pub w_max], reset to the
    upper end at contact start, after a step out of the layer, or when |r_t - r_t-1| < SEC_TOL. D and r are known
    identically (mirrored) to both members, so both compute the same G. Both clip the move to the regime breakpoint."""
    mode = None
    W_MIN, W_MAX = 1.0, 3.0
    SEC_N, SEC_TOL = 3, 1e-4
    _cur = None

    def exchange(self, body, pair):
        self._cur = pair
        return super().exchange(body, pair)

    def _clip(self, move, s_i, s_k, a):
        radius = max(self.region_floor, min(self.breakpoint_distance(s_i), self.breakpoint_distance(s_k)) / a)
        return float(np.clip(move, -radius, radius))

    def gain_for(self, s_i, s_k, alpha):
        layer = 0.0 < s_i < self.eps and 0.0 < s_k < self.eps
        pr = self._cur
        if self.mode == 'sec' and pr is not None:
            D = self.ke * (max(0.0, self.eps - s_i) - max(0.0, self.eps - s_k))
            hist = getattr(pr, 'sec', None)
            if not layer:
                pr.sec = None
            else:
                pr.sec = dict(D=D, r=pr.r, G=[] if hist is None else hist['G'])
                if hist is not None and abs(pr.r - hist['r']) >= self.SEC_TOL:
                    pr.sec['G'] = (hist['G'] + [(D - hist['D']) / (pr.r - hist['r'])])[-self.SEC_N:]
                elif hist is not None:
                    pr.sec['G'] = []
        if self.mode is None or not layer:
            return self.gain
        if self.mode[0] == 'x':
            return self.gain * float(self.mode[1:])
        D = self.ke * (max(0.0, self.eps - s_i) - max(0.0, self.eps - s_k))
        if D == 0.0:
            return self.gain
        a = 1.0 / (1.0 + self.ke * alpha ** 2)
        if self.mode == 'pub':
            return self._clip(D / (2.0 * self.ke * a * self.W_MAX), s_i, s_k, a) / D
        if self.mode == 'sec':
            lo, hi = 2.0 * self.ke * a * self.W_MIN, 2.0 * self.ke * a * self.W_MAX
            G_hat = float(np.clip(np.mean(pr.sec['G']), lo, hi)) if pr.sec['G'] else hi
            return self._clip(D / G_hat, s_i, s_k, a) / D
        D = self.ke * (max(0.0, self.eps - s_i) - max(0.0, self.eps - s_k))
        if D == 0.0:
            return self.gain
        a = 1.0 / (1.0 + self.ke * alpha ** 2)
        move = D / (self.ke * 2.0 * a)
        radius = max(self.region_floor, min(self.breakpoint_distance(s_i), self.breakpoint_distance(s_k)) / a)
        return float(np.clip(move, -radius, radius)) / D


class ThermoStep(StepMixin, Thermo):
    def __init__(self, mode=None, **kw):
        self.mode = mode
        super().__init__(law='mutual', **kw)


class ThermoBetaStep(StepMixin, ThermoBeta):
    W_MIN, W_MAX = 1.0 / 8.0, 24.0

    def __init__(self, mode=None, **kw):
        self.mode = mode
        super().__init__(**kw)

    def exchange(self, body, pair):
        """ThermoBeta.exchange with self.gain replaced by self.gain_for(s_i, s_k, alpha) (identical for mode None)."""
        self._cur = pair
        P = pair.prev
        d, alpha, h, kappa = P['d'], P['alpha'], P['h'], self.spec.kappa
        dhat = d / np.linalg.norm(d)
        y_k = float(dhat @ body.u_prev)
        y_i = float(-dhat @ P['u_i'])
        s_k = -(alpha * y_k - 0.5 * kappa * h + P['R_ki'])
        s_i = -(alpha * y_i - 0.5 * kappa * h + P['R_ik'])
        lam_k = self.ke * max(0.0, self.eps - s_k)
        lam_i = self.ke * max(0.0, self.eps - s_i)
        assert not self.read_on
        pair.about_k.append(y_k, *lin_w(s_k, P['R_ki'], alpha, h, kappa, self.eps, self.ke, 1.0))
        pair.k_about_i.append(y_i, *lin_w(s_i, P['R_ik'], alpha, h, kappa, self.eps, self.ke, 1.0))
        m = P['follow_k'] * P['follow_ki'] if self.law == 'mutual' else 1.0
        pair.r -= m * self.gain_for(s_i, s_k, alpha) * (lam_i - lam_k)
        return lam_i, lam_k


class CentralLayer(Solver):
    """B (diagnostic, privileged): one QP over all team inputs with the layer of Ours at an equal split,
    sum_i w_i/2 |u_i - u0_i|^2 + sum_pairs [k_e p^2 + 2 M z], c/2 - p <= -eps, c/2 - z <= 0, p, z >= 0."""
    name = 'central_layer'

    def __init__(self, eps=0.1, ke=20.0, M=1000.0):
        self.eps, self.ke, self.M = eps, ke, M

    def act(self, obs):
        A, b = self.dynamics.input_polytope()
        N, n_u = obs.u_nom.shape
        pairs = sorted({(min(i, nb.index), max(i, nb.index)) for i in range(N) for nb in obs.neighbours[i]
                        if not nb.external})
        P_, nv = len(pairs), N * n_u + 2 * len(pairs)
        H = np.zeros((nv, nv)); q = np.zeros(nv)
        H[:N * n_u, :N * n_u] = np.kron(np.diag(obs.weights), np.eye(n_u))
        q[:N * n_u] = -(obs.weights[:, None] * obs.u_nom).ravel()
        H[N * n_u:N * n_u + P_, N * n_u:N * n_u + P_] = 2.0 * self.ke * np.eye(P_)
        q[N * n_u + P_:] = 2.0 * self.M
        Gs, hs = [np.hstack([block_diag(*[A] * N), np.zeros((N * len(b), 2 * P_))]),
                  np.hstack([np.zeros((2 * P_, N * n_u)), -np.eye(2 * P_)])], [np.tile(b, N), np.zeros(2 * P_)]
        for j, (i, k) in enumerate(pairs):
            gi, gk = self.spec.own_term(obs.x[i], obs.x[k]), self.spec.own_term(obs.x[k], obs.x[i])
            c = np.zeros(nv); c[i * n_u:(i + 1) * n_u], c[k * n_u:(k + 1) * n_u] = 0.5 * gi.a, 0.5 * gk.a
            cb = 0.5 * (gi.b + gk.b)
            lay = c.copy(); lay[N * n_u + j] = -1.0
            wal = c.copy(); wal[N * n_u + P_ + j] = -1.0
            Gs += [lay[None], wal[None]]; hs += [[-(cb + self.eps)], [-cb]]
        x, _ = solve_qp(H, q, np.vstack(Gs), np.concatenate(hs))
        p = x[N * n_u:N * n_u + P_]
        track = {nb.index: nb.track for nbs in obs.neighbours for nb in nbs if not nb.external}
        mu = {}
        for (i, k), pj in zip(pairs, p):
            lam = float(2.0 * self.ke * pj) / 2.0 if pj > 1e-12 else 0.0     # per-side multiplier k_e p
            mu[(i, track.get(k, k))] = mu[(k, track.get(i, i))] = lam
        return x[:N * n_u].reshape(N, n_u), dict(mu=mu)


LOG = True                    # contact logging (read-only); the confirmation runs switch it off


def solver_for(conf, cell):
    base, _, mode = conf.partition('@')
    mode = mode or None
    cb = json.loads((G.OUT / 'cbar.json').read_text())[cell]
    if base == 'oracle_tuned':
        return build('oracle', **G.TUNED['oracle'])
    _, spec = build('ours', **G.OURS)
    if base == 'central_layer':
        return CentralLayer(eps=0.1), spec
    if base.startswith('nocover'):
        eps = float(base.split('_eps')[1]) if '_eps' in base else 0.1
        return ThermoStep(mode, **dict(G.OURS, eps=eps, no_cover=True, log_contacts=LOG)), spec
    if base == 'ours':
        return ThermoStep(mode, **dict(G.OURS, eps=0.1, log_contacts=LOG)), spec
    if base == 'beta':
        return ThermoBetaStep(mode, **dict(G.OURS, eps=0.1, W0=4.22, cbar=cb, per_step=True, beta_max=8.0,
                                           tau_leak=float('inf'), log_contacts=LOG)), spec
    raise ValueError(conf)


def contact_end(log):
    """price imbalance |lam_i - lam_k|/(lam_i + lam_k) and |s_ik - s_ki|/2 at the last step of each team contact."""
    imb = [abs(e['mu_i'][-1] - e['mu_k'][-1]) / (e['mu_i'][-1] + e['mu_k'][-1]) for e in encounters(log, 1e-6)]
    N = log.x.shape[1]
    tracks = np.asarray(log.meta['tracks'])
    body = np.empty_like(tracks); body[tracks] = np.arange(len(tracks))
    last = {}
    for k, inf in enumerate(log.info):
        for c in inf.get('clog', []):
            b = int(body[c['track']])
            if b < N:
                last[(c['i'], b, c['t0'])] = (k, c['s'])
    gaps = []
    for (i, b, _), (k, s) in last.items():
        if i < b:
            other = [v for (ii, bb, _), v in last.items() if ii == b and bb == i and v[0] == k]
            if other:
                gaps.append(abs(s - other[0][1]) / 2.0)
    return (float(np.median(imb)) if imb else np.nan), (float(np.median(gaps)) if gaps else np.nan)


def team_episodes(log, frac=0.95):
    """Team-violation episodes: (i, k, start s, duration s, min distance) for runs of steps with |p_i - p_k| < frac rho."""
    X = log.x[..., :2]
    N = X.shape[1]
    out = []
    for i in range(N):
        for k in range(i + 1, N):
            d = np.linalg.norm(X[:, i] - X[:, k], axis=1)
            v = d < frac * log.rho
            if not v.any():
                continue
            e = np.flatnonzero(np.diff(np.r_[0, v.astype(int), 0]))
            for a, b in zip(e[::2], e[1::2]):
                out.append((i, k, float(log.t[a]), float((b - a) * log.dt), float(d[a:b].min())))
    return out


def run(conf, cell, seed):
    t0 = time.time()
    sol, spec = solver_for(conf, cell)
    log = simulate(make_scenario(cell), SingleIntegrator(), spec, sol, 120.0, 0.02, seed)
    log.rho = RHO
    f = 0.5 * log.weights[None] * np.sum((log.u - log.u_nom) ** 2, axis=2) * log.dt
    W = f.sum(0)
    N = log.x.shape[1]
    con = np.mean([[any(v > 0 for (i, _), v in inf.get('mu', {}).items() if i == a) for a in range(N)] for inf in log.info])
    row = dict(conf=conf, cell=cell, seed=seed, wall_s=round(time.time() - t0, 1), W_cv=float(W.std() / W.mean()),
               constrained=float(con), **Cost()(log), **Safety()(log))
    if 'r' in log.info[0]:
        row.update(AgreementGap()(log))
    if cell.startswith(('HOM-E0', 'HET-E0')) and conf not in ('oracle_tuned',) and LOG:
        row['imb_end'], row['split_end'] = contact_end(log)
    if not LOG and conf != 'oracle_tuned':
        row['imb_end'] = float(np.median([abs(e['mu_i'][-1] - e['mu_k'][-1]) / (e['mu_i'][-1] + e['mu_k'][-1])
                                          for e in encounters(log, 1e-6)] or [np.nan]))
    f = 0.5 * log.weights[None] * np.sum((log.u - log.u_nom) ** 2, axis=2) * log.dt
    row['W_range'] = float(np.ptp(f.sum(0)))
    row['episodes'] = team_episodes(log)
    return row


def jobs(seeds, only=None, cells=None):
    J = []
    if only is not None and cells is not None:
        return [(c, c0 + '+ts1.5', s) for c0 in cells for s in seeds for c in only]
    for c0 in ('HOM-E0', 'HET-E0'):
        refs = ['oracle_tuned', 'ours', 'nocover', 'nocover_eps0.05', 'nocover_eps0.02', 'beta', 'central_layer']
        var = [f'{b}@{m}' for b in ('ours', 'nocover', 'beta') for m in MODES]
        J += [(c, c0 + '+ts1.5', s) for s in seeds for c in (only or refs + var)]
    if only is None:
        for c0 in ('HOM-E8', 'HET-E8'):
            J += [(c, c0 + '+ts1.5', s) for s in seeds
                  for c in ['oracle_tuned', 'ours', 'beta'] + [f'{b}@{m}' for b in ('ours', 'beta') for m in MODES]]
    return J


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--seeds', type=int, nargs='+', default=[0])
    ap.add_argument('--only', nargs='+', default=None)
    ap.add_argument('--cells', nargs='+', default=None)
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--out', default=None)
    ap.add_argument('--nolog', action='store_true')
    a = ap.parse_args()
    if a.out:
        OUT = Path(a.out)
    LOG = not a.nolog
    OUT.parent.mkdir(exist_ok=True)
    have = {(r['conf'], r['cell'], r['seed']) for r in G.load(OUT)}
    todo = [j for j in jobs(a.seeds, a.only, a.cells) if j not in have]
    print(len(todo), 'runs', flush=True)
    with ProcessPoolExecutor(a.workers) as ex, OUT.open('a') as fh:
        for fut in as_completed([ex.submit(run, *j) for j in todo]):
            fh.write(json.dumps(fut.result()) + '\n'); fh.flush()
    print('done', flush=True)
