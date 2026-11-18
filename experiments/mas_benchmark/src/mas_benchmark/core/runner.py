"""Closed loop: scenario + dynamics + specification + solver -> Log."""
import numpy as np

from .types import Log, Neighbour, Observation


def sense(x, u_prev, ext_x, ext_u_prev, dynamics, spec, tracks=None):
    """neighbours[i] = bodies within spec.sensing_range of agent i (team first, then externals).

    tracks[b] is the anonymous track id of body b (team 0..N-1, then externals); identity by default."""
    tracks = np.arange(len(x) + len(ext_x)) if tracks is None else tracks
    p = dynamics.position(x)
    q = dynamics.position(ext_x) if len(ext_x) else np.zeros((0, 2))
    out = []
    for i in range(len(x)):
        nb = []
        for k in range(len(x)):
            if k != i and np.linalg.norm(p[i] - p[k]) <= spec.sensing_range:
                nb.append(Neighbour(k, x[k], u_prev[k], external=False, track=int(tracks[k])))
        for e in range(len(ext_x)):
            if np.linalg.norm(p[i] - q[e]) <= spec.sensing_range:
                nb.append(Neighbour(-1, ext_x[e], ext_u_prev[e], external=True, ext_index=e,
                                     track=int(tracks[len(x) + e])))
        out.append(nb)
    return out


def simulate(scenario, dynamics, spec, solver, horizon, dt, seed):
    rng = np.random.default_rng(seed)
    x = scenario.reset(rng)
    w = scenario.weights()
    n_bodies = len(x) + len(scenario.externals()[0])
    tracks = np.random.default_rng([seed, 7]).permutation(n_bodies)    # separate stream: the world is unchanged
    solver.reset(scenario, dynamics, spec, dt)
    n_steps = int(round(horizon / dt))
    u_prev = np.zeros((len(x), dynamics.n_u))
    T, X, U, U0, E, info = [], [], [], [], [], []
    for s in range(n_steps):
        t = s * dt
        ext_x, ext_u = scenario.externals()
        u_nom = scenario.nominal_input(x)
        obs = Observation(t, x.copy(), u_nom, w, sense(x, u_prev, ext_x, ext_u, dynamics, spec, tracks),
                          ext_x.copy(), ext_u.copy(), scenario.v_env)
        u, inf = solver.act(obs)
        T.append(t); X.append(x.copy()); U.append(u.copy()); U0.append(u_nom); E.append(ext_x.copy())
        info.append(inf)
        x = dynamics.step(x, u, dt)
        scenario.advance(x, dt)
        u_prev = u
    return Log(dt, np.array(T), np.array(X), np.array(U), np.array(U0), np.array(E), w, spec.rho,
               info, dict(scenario=scenario.name, solver=solver.name, seed=seed, horizon=horizon,
                        tracks=[int(k) for k in tracks]))
