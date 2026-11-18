"""Ours (Sec. 11): priced slack, certified room, costate reading and agreement exchange, with no messages.

Each agent acts on its own observation only (`Observation.local(i)`): its own state, nominal input and weight,
the bodies it senses under anonymous tracks (position, last velocity), and public constants. It never learns
whether a body is a team member, and every neighbour's price is read from i's replica of that neighbour.

Each step, per agent i and every sensed body k:
  (3, for the previous step) observe u_k, append both windows, read k's costate, update r_ik;
  (1) beliefs and rooms  R_ik = A[max(c_k, r_ik)]  and the replicated  R_ki = A[max(c_i, -r_ik)];
  (2) the local QP with one priced layer and one hard row per neighbour.

Exchange (transmissions set to one):
  law='follow' (default)  r_ik <- r_ik - step (lam_i - w_ik(f) lam_hat_k)
      w_ik(f) = i's posterior mass on k following (the finite temperatures). Under exact replicas
      d/dt (r_ik + r_ki) = -kappa [(1 - w_ki(f)) lam_i + (1 - w_ik(f)) lam_k] <= 0. NB Prop. 2.7 needs
      r_ik + r_ki >= 0: this drift lets the two allowances exceed the budget and is covered only through the
      coverage term (Remark 5.3), not by the agreements.
  law='plain'             r_ik <- r_ik - step (lam_i - lam_hat_k)          (v40 Sec. 11 as written)
  law='mutual'            r_ik <- r_ik - w_ik(f) w_ki(f) step (lam_i - lam_hat_k), w_ki(f) from i's replica of k's
                          belief: both copies move by the same number (r_ik + r_ki = 0 exactly)
  step='region'  Delta r = D/(ke (a_i + a_k)) with regime sensitivities a (1 at the wall / input bound, else
  w_bar/(w_bar + ke alpha^2)), clipped to the distance to the next regime breakpoint; damp_rows=True divides by the
  agent's own number of active rows (not replicable by the neighbour: copies then drift);
  step='half_ke' (default) 1/(2 ke), the largest step that never overshoots (inputs held);  step='kappa'  kappa dt
  (the continuous law's step);  step='newton'  local curvature step (see `gain_for`); step_scale multiplies any of
  them (sensitivity only; > 1 on 'half_ke' leaves the worst-case non-overshoot guarantee).

Agreement lifetime: by default an agreement is created at 0 when a body enters sensing range and dropped when it
leaves. agreement_memory=True keeps r_ik when the body leaves and restores it when the same track re-enters
(within memory_s seconds, or forever if None). This assumes re-identification by observation (the agent recognises
a body it has seen before); both members of a pair apply the same rule, so the copies keep r_ik + r_ki <= 0.
"""
from dataclasses import dataclass, field

import numpy as np

from ...core import Solver
from ...utils.qp import solve_qp
from .belief import FOLLOW_PRIOR, TAUS, TemperatureBelief, linearise
from scipy.special import log_ndtr

from .bound import (certified_bound, certified_bound_batch, log_gauss_exceed, log_mgf_atom_exp,
                    log_mgf_atom_exp_batch, log_mgf_uniform_max, log_mgf_uniform_max_batch)


@dataclass
class Pair:
    about_k: TemperatureBelief          # i's belief about k
    k_about_i: TemperatureBelief        # k's belief about i, replicated from i's own actions
    r: float = 0.0                      # r_ik, the share i leaves to k
    prev: dict = field(default_factory=dict)
    q: float = 0.0                      # lam_ik theta*_ik of the previous step (temperature allotment)
    delta: float = None                 # smoothed delta_ik (temperature allotment)
    t0: float = None                    # time the contact started (logging only)
    n: int = 0                          # exchange steps since the contact started (logging only)


class Thermo(Solver):
    def __init__(self, eps=0.1, ke=20.0, M=1000.0, delta=0.05, window=50, sigma_o=0.01,
                 follow_prior=FOLLOW_PRIOR, law='follow', step='half_ke', step_scale=1.0,
                 agreement_memory=False, memory_s=None, w_bar=3.0, region_floor=1e-3, damp_rows=False,
                 isolation=False, iso_r=2.0, projection=False, risk_allotment='per_neighbour', delta_ema=0.8,
                 log_contacts=False, no_cover=False):
        self.eps, self.ke, self.M, self.delta = eps, ke, M, delta
        # log_contacts: per step and active contact, append a row of diagnostics to info['clog'] (read-only: the
        # decision is unchanged). no_cover: the full-information reference, rooms R_ik = r_ik and R_ki = -r_ik (cover
        # U = R - r = 0), everything else unchanged.
        self.log_contacts, self.no_cover = log_contacts, no_cover
        self.window, self.sigma_o, self.follow_prior = window, sigma_o, follow_prior
        self.law, self.step, self.step_scale = law, step, step_scale
        self.agreement_memory, self.memory_s = agreement_memory, memory_s
        self.w_bar, self.region_floor, self.damp_rows = w_bar, region_floor, damp_rows
        self.isolation, self.iso_r = isolation, iso_r
        self.projection = projection
        self.risk_allotment, self.delta_ema = risk_allotment, delta_ema
        self.name = (f'ours_eps{eps:g}' + ('' if follow_prior == FOLLOW_PRIOR else f'_w{follow_prior:g}')
                     + ('' if law == 'follow' else f'_{law}') + ('' if step == 'half_ke' else f'_{step}')
                     + ('' if step_scale == 1.0 else f'_s{step_scale:g}')
                     + ('' if not agreement_memory else '_mem' + ('' if memory_s is None else f'{memory_s:g}'))
                     + ('_damp' if damp_rows else '') + ('_iso' if isolation else '') + ('_proj' if projection else '')
                     + {'per_neighbour': '', 'uniform': '_riskU', 'temperature': '_riskT'}[risk_allotment]
                     + ('_nocover' if no_cover else ''))

    def reset(self, scenario, dynamics, spec, dt):
        super().reset(scenario, dynamics, spec, dt)
        self.memory = [dict() for _ in range(scenario.n_agents)]    # agent i's own memory: track -> Pair
        self.archive = [dict() for _ in range(scenario.n_agents)]   # agreement_memory: track -> (r, time of exit)
        self.gain = self.step_scale * (spec.kappa * dt if self.step == 'kappa' else 1.0 / (2.0 * self.ke))
        A, b = dynamics.input_polytope()
        V = []                                            # vertices of the input polytope (faces ordered by angle)
        for j in range(len(b)):
            V.append(np.linalg.solve(A[[j, (j + 1) % len(b)]], b[[j, (j + 1) % len(b)]]))
        self.vertices = np.array(V)

    def belief(self):
        return TemperatureBelief(self.window, self.sigma_o, self.follow_prior)

    def room(self, belief, r, alpha, h, v_cap):
        """-> (A_w[max(c, r)], theta*, following mass), c = alpha y - kappa h/2, y the other's next approach speed."""
        kappa = self.spec.kappa
        log_w, m, v = belief.posterior(v_cap)
        rows = []
        for tau, mj, vj in zip(TAUS, m, v):
            mu = min(alpha * mj - 0.5 * kappa * h, r)
            sd = alpha * np.sqrt(tau + vj + self.sigma_o ** 2)
            rows.append(log_mgf_atom_exp(r, log_gauss_exceed(mu, sd, r), self.M / tau))
        g0 = -0.5 * kappa * h
        rows.append(log_mgf_uniform_max(r, g0 - alpha * v_cap, g0 + alpha * v_cap))
        A, theta = certified_bound(log_w, np.array(rows), self.delta)
        return A, theta, float(-np.expm1(log_w[-1]))

    def room_batch(self, beliefs, r, alpha, h, v_cap, delta=None):
        """`room` for P (belief, r, alpha, h) at once -> (A (P,), theta* (P,), following mass (P,)).
        delta: per-row risk levels (default: self.delta on every row)."""
        kappa = self.spec.kappa
        post = [b.posterior(v_cap) for b in beliefs]
        log_w = np.array([p[0] for p in post])                               # (P, 5)
        m = np.array([p[1] for p in post]); v = np.array([p[2] for p in post])   # (P, 4)
        g0 = -0.5 * kappa * h
        mu = np.minimum(alpha[:, None] * m + g0[:, None], r[:, None])
        sd = alpha[:, None] * np.sqrt(TAUS[None] + v + self.sigma_o ** 2)
        log_q = log_ndtr((mu - r[:, None]) / sd)
        rows = log_mgf_atom_exp_batch(r, log_q, self.M / TAUS)              # (P, 4, T)
        unif = log_mgf_uniform_max_batch(r, g0 - alpha * v_cap, g0 + alpha * v_cap)
        A, theta = certified_bound_batch(log_w, np.concatenate([rows, unif[:, None]], axis=1),
                                         self.delta if delta is None else delta)
        return A, theta, -np.expm1(log_w[:, -1])

    def allot(self, i, view, pairs):
        """Per-neighbour risk levels delta_ik with sum_k delta_ik = delta_i (= self.delta) for 'uniform' and
        'temperature'; 'per_neighbour' gives every neighbour self.delta (union risk K delta). 'temperature' (v41 Prop.
        6.4): delta_ik proportional to q_ik = lam_ik theta*_ik of the previous step, floored at 0.01 delta_i/K and
        smoothed by an EMA; uses only i's own quantities. -> (own deltas (K,), replica deltas (K,)).

        Replica rows (k's room toward i) need k's allotment, which depends on k's private quantities. They use the
        uniform allotment over the bodies i sees within sensing range of k (an estimate of K_k), so under 'uniform' /
        'temperature' the replicas, and with them the mutual copies, are no longer exact."""
        K = len(view.bodies)
        if self.risk_allotment == 'per_neighbour' or K == 0:
            d = np.full(K, self.delta)
            return d, d.copy()
        base = self.delta / K
        if self.risk_allotment == 'uniform':
            own = np.full(K, base)
        else:
            q = np.array([pairs[b.track].q for b in view.bodies])
            raw = self.delta * q / q.sum() if q.sum() > 0 else np.full(K, base)
            raw = np.maximum(raw, 0.01 * base)
            raw *= self.delta / raw.sum()
            prev = np.array([pairs[b.track].delta if pairs[b.track].delta is not None else base for b in view.bodies])
            own = self.delta_ema * prev + (1 - self.delta_ema) * raw
            own *= self.delta / own.sum()
            for b, dk in zip(view.bodies, own):
                pairs[b.track].delta = float(dk)
        rng = self.spec.sensing_range
        rep = np.array([self.delta / (1 + sum(1 for o in view.bodies if o.track != b.track
                                              and np.linalg.norm(o.x - b.x) <= rng)) for b in view.bodies])
        return own, rep

    def curvature(self, s, alpha):
        """d lam / d R of one side under the public self-model (unit weight): ke/(1 + ke alpha^2) inside the layer,
        0 when unconstrained or at the wall (where the input, not the penetration, absorbs a change of room)."""
        return self.ke / (1.0 + self.ke * alpha ** 2) if 0.0 < s < self.eps else 0.0

    def gain_for(self, s_i, s_k, alpha):
        """Exchange step. 'half_ke' / 'kappa': fixed (times step_scale). 'newton': 1 / (curv_i + curv_k), both sides
        under the public unit-weight self-model so that i and k compute the same number from the same observations
        (copies stay opposite); the curvature is floored at both sides' layer value, and the move is clipped to
        eps/2 per step so the agreement cannot cross the layer in one step."""
        if self.step != 'newton':
            return self.gain
        floor = 2.0 * self.ke / (1.0 + self.ke * alpha ** 2)
        return self.step_scale / max(self.curvature(s_i, alpha) + self.curvature(s_k, alpha), floor)

    def at_bound(self, u):
        A, b = self.dynamics.input_polytope()
        return bool(np.max(A @ u - b) > -1e-6)

    def sensitivity(self, s, bound, alpha):
        """a-bar of one side for step='region': 1 when the input cannot absorb a change of room (input bound or wall,
        s < 0), else w_bar/(w_bar + ke alpha^2) with the public weight bound w_bar."""
        if bound or s < 0.0:
            return 1.0
        return self.w_bar / (self.w_bar + self.ke * alpha ** 2)

    def breakpoint_distance(self, s):
        """Distance of a slack to the next regime breakpoint (0 or eps)."""
        return min(abs(s), abs(self.eps - s))

    def headroom(self, u):
        """Distance of an input to the boundary of the input polytope (min over faces of b - A u)."""
        A, b = self.dynamics.input_polytope()
        return max(0.0, float(np.min(b - A @ u)))

    def region_move(self, D, s_i, s_k, bound_i, bound_k, alpha, n_rows=1, isolated=True, u_i=None, u_k=None):
        """step='region': Delta r = D / (ke (a_i + a_k)), clipped to the trust region
        min(dist_i, dist_k) / max(a_i, a_k) (floored), optionally damped by 1/n_rows. Uses only quantities both members
        of the pair compute identically (own slack / replicated slack, own / observed input bound, alpha).
        isolation=True: the fast sensitivities are used only for an isolated pair (no third body within iso_r of either
        agent, neither at the input bound); otherwise a_i = a_k = 1 (the default step 1/(2 ke)). The radius is also
        capped by each agent's speed headroom, headroom * alpha / a (the speed-bound breakpoint)."""
        if self.isolation and not isolated:
            a_i = a_k = 1.0
        else:
            a_i, a_k = self.sensitivity(s_i, bound_i, alpha), self.sensitivity(s_k, bound_k, alpha)
        move = self.step_scale * D / (self.ke * (a_i + a_k))
        radius = min(self.breakpoint_distance(s_i), self.breakpoint_distance(s_k)) / max(a_i, a_k)
        if self.isolation and u_i is not None:
            radius = min(radius, self.headroom(u_i) * alpha / a_i, self.headroom(u_k) * alpha / a_k)
        radius = max(self.region_floor, radius)
        return float(np.clip(move, -radius, radius)) / max(1, n_rows)

    def isolated(self, x_i, body, bodies):
        """No third body within iso_r of i or of k. Both members evaluate the same expressions on the same positions
        (a body within iso_r of either is within sensing range of both while the pair is in contact range)."""
        for b in bodies:
            if b.track == body.track:
                continue
            if np.linalg.norm(b.x - x_i) <= self.iso_r or np.linalg.norm(b.x - body.x) <= self.iso_r:
                return False
        return True

    def capability(self, d, h):
        """G = max over the input set of -g(u) = 2 max_v d.v + kappa h/2: the most room this side can make."""
        return 2.0 * float(np.max(self.vertices @ d)) + 0.5 * self.spec.kappa * h

    def project(self, pair):
        """projection=True: keep r_ik in [U_ki - G_k, G_i - U_ik] so neither side is asked for more room than its
        speed bound allows (U = room - own agreement, from the last room computation; all public under Assumption
        4.1, and both members compute mirrored bounds). An empty interval (robustly infeasible pair) clamps to its
        midpoint."""
        P = pair.prev
        d, h = P['d'], P['h']
        U_ik = P['R_ik'] - P['r_used']
        U_ki = P['R_ki'] + P['r_used']
        lo = U_ki - self.capability(-d, h)
        hi = self.capability(d, h) - U_ik
        pair.r = 0.5 * (lo + hi) if lo > hi else min(max(pair.r, lo), hi)

    def exchange(self, body, pair):
        """Step (3) for the previous step: windows, costate reading, agreement update."""
        P = pair.prev
        d, alpha, h, kappa = P['d'], P['alpha'], P['h'], self.spec.kappa
        dhat = d / np.linalg.norm(d)
        y_k = float(dhat @ body.u_prev)             # k's approach speed toward i (observed)
        y_i = float(-dhat @ P['u_i'])               # i's own approach speed toward k
        s_k = -(alpha * y_k - 0.5 * kappa * h + P['R_ki'])     # k's slack under i's replica of k's room
        # i's own slack by the same expression k uses for its replica of i, so both sides of the pair compute
        # bitwise-identical numbers (regime switches and clipping are discontinuous in s)
        s_i = -(alpha * y_i - 0.5 * kappa * h + P['R_ik'])
        lam_k = self.ke * max(0.0, self.eps - s_k)
        lam_i = self.ke * max(0.0, self.eps - s_i)
        pair.about_k.append(y_k, *linearise(s_k, P['R_ki'], alpha, h, kappa, self.eps, self.ke))
        pair.k_about_i.append(y_i, *linearise(s_i, P['R_ik'], alpha, h, kappa, self.eps, self.ke))
        if self.law == 'mutual':
            # mutual trust: both copies move by the same number m (lam_i - lam_hat_k) h, m = w_ik(f) w_ki(f)
            # (a product, so i and k compute it identically); r_ik + r_ki = 0 exactly, the agreement freezes toward
            # a neighbour either side does not trust
            m = P['follow_k'] * P['follow_ki']
            D = lam_i - lam_k
            if self.step == 'region':
                pair.r -= m * self.region_move(D, s_i, s_k, self.at_bound(P['u_i']), self.at_bound(body.u_prev), alpha,
                                               isolated=P.get('iso', True), u_i=P['u_i'], u_k=body.u_prev)
            else:
                pair.r -= m * self.gain_for(s_i, s_k, alpha) * D
            return lam_i, lam_k
        weight = P['follow_k'] if self.law == 'follow' else 1.0
        if self.step == 'region':
            pair.r -= self.region_move(lam_i - weight * lam_k, s_i, s_k, self.at_bound(P['u_i']),
                                       self.at_bound(body.u_prev), alpha, P.get('n_rows', 1) if self.damp_rows else 1,
                                       isolated=P.get('iso', True), u_i=P['u_i'], u_k=body.u_prev)
            return lam_i, lam_k
        move = self.gain_for(s_i, s_k, alpha) * (lam_i - weight * lam_k)
        if self.step == 'newton':
            move = float(np.clip(move, -0.5 * self.eps, 0.5 * self.eps))
        pair.r -= move
        return lam_i, lam_k

    def act_local(self, i, view, info):
        """Agent i's decision from its own LocalView only."""
        A, b = self.dynamics.input_polytope()
        n_u = self.dynamics.n_u
        pairs = self.memory[i]
        tracks = [body.track for body in view.bodies]
        for key in [k for k in pairs if k not in tracks]:
            if self.agreement_memory:                    # keep r for a body seen before (re-identification)
                self.archive[i][key] = (pairs[key].r, view.t)
            del pairs[key]
        geo = []
        for body in view.bodies:
            pair = pairs.get(body.track)
            if pair is None:
                pair = pairs[body.track] = Pair(self.belief(), self.belief(), t0=view.t)
                old = self.archive[i].pop(body.track, None) if self.agreement_memory else None
                if old is not None and (self.memory_s is None or view.t - old[1] <= self.memory_s):
                    pair.r = old[0]                      # belief windows restart: they hold only the last T anyway
            elif pair.prev:
                _, lam_k = self.exchange(body, pair)
                pair.n += 1
                if self.projection:
                    self.project(pair)
                info['lam_hat'][(i, body.track)] = lam_k
            d = view.x - body.x
            geo.append((pair, d, 2.0 * np.linalg.norm(d), self.spec.safety(view.x, body.x)))
        rooms, rows = [], []
        if geo:
            P = len(geo)
            r = np.array([g[0].r for g in geo]); alpha = np.array([g[2] for g in geo]); h = np.array([g[3] for g in geo])
            d_own, d_rep = self.allot(i, view, pairs)
            A_, th_, fol_ = self.room_batch([g[0].about_k for g in geo] + [g[0].k_about_i for g in geo],
                                            np.concatenate([r, -r]), np.tile(alpha, 2), np.tile(h, 2), view.v_env,
                                            np.concatenate([d_own, d_rep]))
            if self.no_cover:
                A_ = np.concatenate([r, -r])
            clog = {}
            for j, (body, (pair, d, alpha_j, h_j)) in enumerate(zip(view.bodies, geo)):
                R_ik, R_ki, th, follow_k = float(A_[j]), float(A_[P + j]), float(th_[j]), float(fol_[j])
                follow_ki = float(fol_[P + j])           # k's following mass for i, from i's replica of k's belief
                g = self.spec.own_term(view.x, body.x)
                pair.prev = dict(d=d, alpha=alpha_j, h=h_j, R_ik=R_ik, R_ki=R_ki, follow_k=follow_k, follow_ki=follow_ki,
                                 r_used=pair.r,
                                 iso=self.isolated(view.x, body, view.bodies) if self.isolation else True)
                rooms.append(R_ik); rows.append(g)
                pair.prev['theta'], pair.prev['delta'] = th, float(d_own[j])
                info['r'][(i, body.track)], info['theta'][(i, body.track)] = pair.r, th
                info['delta'][(i, body.track)], info['cov'][(i, body.track)] = float(d_own[j]), R_ik - pair.r
                info['follow'][(i, body.track)] = follow_k
                if self.log_contacts:
                    clog[body.track] = self.contact_state(pair, alpha_j, h_j, view.v_env)
        # (2) variables [u (n_u), p (K), z (K)]
        K, w, u0 = len(view.bodies), view.weight, view.u_nom
        n = n_u + 2 * K
        Pm = np.zeros((n, n))
        Pm[:n_u, :n_u] = w * np.eye(n_u)
        Pm[n_u:n_u + K, n_u:n_u + K] = self.ke * np.eye(K)
        q = np.concatenate([-w * u0, np.zeros(K), self.M * np.ones(K)])
        G = [np.hstack([A, np.zeros((len(b), 2 * K))]), np.hstack([np.zeros((2 * K, n_u)), -np.eye(2 * K)])]
        h_ = [b, np.zeros(2 * K)]
        for k, (g, R) in enumerate(zip(rows, rooms)):
            layer = np.zeros(n); layer[:n_u], layer[n_u + k] = g.a, -1.0
            wall = np.zeros(n); wall[:n_u], wall[n_u + K + k] = g.a, -1.0
            G += [layer[None], wall[None]]
            h_ += [[-(g.b + R + self.eps)], [-(g.b + R)]]
        sol, how = solve_qp(Pm, q, np.vstack(G), np.concatenate(h_))
        info['slsqp'] += how == 'slsqp'
        u = sol[:n_u]
        n_active = sum(1 for g, R in zip(rows, rooms) if -(g(u) + R) < self.eps)
        for track, g, R in zip(tracks, rows, rooms):
            s_i = -(g(u) + R)
            pairs[track].prev.update(u_i=u.copy(), s_i=s_i, n_rows=n_active)
            info['mu'][(i, track)] = lam = self.ke * max(0.0, self.eps - s_i)
            pr = pairs[track].prev
            pairs[track].q = lam * pr.get('theta', 0.0)
            if lam > 0:
                info['nu'][(i, track)] = lam * pr.get('theta', 0.0) / pr.get('delta', self.delta)
            if self.log_contacts:
                pa = pairs[track]
                info.setdefault('clog', []).append(dict(
                    i=i, track=track, t0=pa.t0, n=pa.n, U=pr['R_ik'] - pr['r_used'], lam=lam,
                    lam_hat=info['lam_hat'].get((i, track), np.nan), r=pr['r_used'], s=s_i,
                    regime=0 if s_i >= self.eps else (1 if s_i > 0 else 2), theta=pr['theta'], delta=pr['delta'],
                    R_ki=pr['R_ki'], follow=pr['follow_k'], follow_rep=pr['follow_ki'], **clog[track]))
        return u

    def contact_state(self, pair, alpha, h, v_cap):
        """Belief diagnostics of i about k (pure: no state changes). a_last: response coefficient of the latest
        observation in the window; aa: sum of a_s^2 over the window; log_w over (tau finite..., inf); per finite tau
        the posterior variance of the intent v_j = 1/(1 + aa/(tau_j + sigma_o^2)); X = alpha y - kappa h/2 the
        neighbour's next usage, predictive mean / variance under the mixture (tau = inf: uniform on the capability)."""
        b = pair.about_k
        log_w, m, v = b.posterior(v_cap)
        obs = list(b.obs)
        a = np.array([o[1] for o in obs]) if obs else np.zeros(0)
        s2 = TAUS + self.sigma_o ** 2
        g0 = -0.5 * self.spec.kappa * h
        mu = np.append(alpha * m + g0, g0)
        var = np.append(alpha ** 2 * (TAUS + v + self.sigma_o ** 2), (alpha * v_cap) ** 2 / 3.0)
        w = np.exp(log_w)
        mX = float(w @ mu)
        jm = int(np.argmax(log_w[:-1]))
        return dict(a_last=float(a[-1]) if len(a) else np.nan, aa=float(a @ a), n_win=len(a),
                    w=[float(x) for x in w], mX=mX, vX=float(w @ (var + mu ** 2) - mX ** 2),
                    tau_map=float(TAUS[jm]), I_map=float(a @ a / s2[jm]), v_map=float(v[jm]),
                    tau_mean=float(w[:-1] @ TAUS / max(w[:-1].sum(), 1e-300)), alpha=float(alpha), h=float(h),
                    m=[float(x) for x in m], v=[float(x) for x in v], v_cap=float(v_cap))

    def act(self, obs):
        info = dict(r={}, mu={}, lam_hat={}, theta={}, follow={}, delta={}, cov={}, nu={}, slsqp=0)
        U = np.array([self.act_local(i, obs.local(i), info) for i in range(obs.n_agents)])
        return U, info
