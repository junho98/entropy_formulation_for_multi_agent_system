"""Controlled two-hypothesis encounter for the fairness-exposure (Bretagnolle-Huber) bound.

Agent i (index 0, weight 1) runs the solver under test. Its neighbour k is, under
  H_F   a follower: the same solver with weight 3 (both agents controlled by one solver instance, N = 2);
  H_out a non-yielder: k applies its nominal velocity (what H_F's k does while unconstrained), and is sensed by i as
        an external body (N = 1).
In both, k's applied velocity is its command plus Gaussian noise sigma_v per step from the same seeded sequence,
and i observes k's applied velocity. k keeps the same anonymous track id, so i's local view is identical under both
hypotheses until i's share toward k activates. i only ever sees its LocalView.
"""
import numpy as np

from ..core import Observation, sense
from ..dynamics import SingleIntegrator
from ..specs import PairwiseBarrier

GEOMETRIES = {'head-on': 180.0, '90deg': 90.0, '45deg': 45.0}     # angle between the two headings
DT = 0.02


def setup(geometry, offset=0.2, dist=4.0):
    """-> starts, goals for i and k crossing near the origin. k is shifted sideways by `offset`."""
    th = np.deg2rad(GEOMETRIES[geometry])
    hi = np.array([1.0, 0.0])
    hk = np.array([np.cos(th), np.sin(th)])
    nk = np.array([-hk[1], hk[0]])
    return (np.array([-dist * hi, -dist * hk + offset * nk]), np.array([dist * hi, dist * hk + offset * nk]))


def nominal(x, goal, speed=1.0):
    d = goal - x
    n = np.linalg.norm(d)
    return speed * d / max(n, speed)


def run(solver, hypothesis, geometry, sigma, seed, n_max=200, pre_max=600, v_env=1.2, w=(1.0, 3.0)):
    """Simulate one encounter. -> dict with, from i's activation on (n = 0 .. n_max):
    r (i's agreement r_ik), mu_i, and under H_F the cumulative chain-rule KL of k's behaviour, under H_out the
    feasibility margin G_i - U_ik (largest r_ik keeping i's walled problem feasible). None if no activation."""
    dyn, spec = SingleIntegrator(), PairwiseBarrier()
    starts, goals = setup(geometry)
    n_team = 2 if hypothesis == 'F' else 1
    solver.reset(type('S', (), {'n_agents': n_team})(), dyn, spec, DT)
    noise = np.random.default_rng(seed).normal(0.0, sigma, size=(pre_max + n_max + 2, 2))
    tracks = np.array([0, 1])
    x_i, x_k = starts[0].copy(), starts[1].copy()
    u_i, v_k = np.zeros(2), np.zeros(2)
    out = dict(r=[], mu=[], kl=[], margin=[], dist=[])
    kl, t_act = 0.0, None
    for t in range(pre_max + n_max + 1):
        u0_i, u0_k = nominal(x_i, goals[0]), nominal(x_k, goals[1])
        if hypothesis == 'F':
            X = np.array([x_i, x_k]); P = np.array([u_i, v_k]); E = np.zeros((0, 2))
            obs = Observation(t * DT, X, np.array([u0_i, u0_k]), np.array(w), sense(X, P, E, E, dyn, spec, tracks),
                              E, E, v_env)
            U, info = solver.act(obs)
            cmd_k = U[1]
        else:
            X = np.array([x_i]); E = np.array([x_k]); EU = np.array([v_k])
            obs = Observation(t * DT, X, np.array([u0_i]), np.array(w[:1]), sense(X, np.array([u_i]), E, EU, dyn, spec,
                              tracks), E, EU, v_env)
            U, info = solver.act(obs)
            cmd_k = u0_k
        mu = info.get('mu', {}).get((0, 1), 0.0)
        if t_act is None and mu > 0.0:
            t_act = t
        if hypothesis == 'F':
            kl += float(np.sum((cmd_k - u0_k) ** 2)) / (2.0 * sigma ** 2)       # mu_F vs mu_out at this state
        if t_act is not None:
            out['r'].append(info.get('r', {}).get((0, 1), np.nan))
            out['mu'].append(mu)
            out['kl'].append(kl)
            out['dist'].append(float(np.linalg.norm(x_i - x_k)))
            pair = getattr(solver, 'memory', [{}])[0].get(1)
            if hypothesis == 'out' and pair is not None and pair.prev and hasattr(solver, 'capability'):
                P_ = pair.prev
                out['margin'].append(solver.capability(P_['d'], P_['h']) - (P_['R_ik'] - P_['r_used']))
            if len(out['r']) > n_max:
                break
        u_i = U[0]
        v_k = cmd_k + noise[t]
        x_i = dyn.step(x_i, u_i, DT)
        x_k = dyn.step(x_k, v_k, DT)
    if t_act is None:
        return None
    out['t_act'] = t_act
    return out


def frozen_equilibrium(solver, geometry, iters=2000, w=(1.0, 3.0), v_env=1.2, at=1.4):
    """Delta*: i's agreement r_ik after `iters` exchange steps with both agents held at distance `at` on the
    geometry's crossing configuration (H_F, no noise), velocities fed back as observations."""
    dyn, spec = SingleIntegrator(), PairwiseBarrier()
    starts, goals = setup(geometry)
    hk = (goals[1] - starts[1]) / np.linalg.norm(goals[1] - starts[1])
    hi = np.array([1.0, 0.0])
    # place them so that each is heading into the other at distance `at`
    x = np.array([np.zeros(2), np.zeros(2)])
    x[1] = x[0] + at * (hi - hk) / max(np.linalg.norm(hi - hk), 1e-9)
    u0 = np.array([hi, hk])
    solver.reset(type('S', (), {'n_agents': 2})(), dyn, spec, DT)
    U = np.zeros((2, 2)); E = np.zeros((0, 2)); r = np.nan
    for _ in range(iters):
        obs = Observation(0.0, x, u0, np.array(w), sense(x, U, E, E, dyn, spec, np.array([0, 1])), E, E, v_env)
        U, info = solver.act(obs)
        r = info.get('r', {}).get((0, 1), r)
    return float(r)
