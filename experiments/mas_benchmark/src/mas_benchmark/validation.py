"""Small reproductions of the reference papers' claims for the baseline implementations.

Each check returns dict(method, claim, source, measured, passed). scripts/validate_refs.py writes the table,
tests/test_references.py asserts it.
"""
import numpy as np

from .core import Observation, sense, simulate
from .dynamics import SingleIntegrator
from .scenarios import Encounter, EncounterConfig
from .solvers import PCCA, Oracle, RiskRatio, Tan
from .specs import PairwiseBarrier


def _row(method, claim, source, measured, passed, note=''):
    return dict(method=method, claim=claim, source=source, measured=measured, passed=bool(passed), note=note)


def _min_team_dist(log):
    X = log.x
    N = X.shape[1]
    D = np.linalg.norm(X[:, :, None] - X[:, None], axis=3)
    D[:, np.arange(N), np.arange(N)] = np.inf
    return float(D.min())


def _min_ext_dist(log):
    return float(np.linalg.norm(log.x[:, :, None] - log.ext_x[:, None], axis=3).min())


def _swap(n=6, radius=4.0, weights=(1.0,)):
    ang = 2 * np.pi * np.arange(n) / n + 0.05 * np.arange(n)      # small asymmetry against symmetric deadlock
    starts = radius * np.stack([np.cos(ang), np.sin(ang)], 1)
    return Encounter(EncounterConfig(name='swap', starts=list(starts), goals=list(-starts), weights=weights))


def _frozen_obs(x, u_nom, weights, dyn, spec):
    E = np.zeros((0, 2))
    return Observation(0.0, x, u_nom, weights, sense(x, np.zeros_like(x), E, E, dyn, spec), E, E, 1.0)


def tan_frozen_convergence(weights=(1.0, 3.0, 1.0), iters=4000, k0=10.0, dt=0.02):
    """Thm 1 (2),(3) / Prop 5: at a fixed state, y converges to the central optimum and every iterate is feasible."""
    dyn, spec = SingleIntegrator(), PairwiseBarrier()
    x = np.array([[0.0, 0.0], [1.6, 0.0], [0.8, 1.3]])
    c = x.mean(0)
    u_nom = (c - x) / np.linalg.norm(c - x, axis=1, keepdims=True)
    w = np.array(weights)
    obs = _frozen_obs(x, u_nom, w, dyn, spec)
    oracle = Oracle(); oracle.reset(None, dyn, spec, dt)
    u_star, _ = oracle.act(obs)
    tan = Tan(k0=k0, law='gradient'); tan.reset(type('S', (), {'n_agents': 3})(), dyn, spec, dt)
    worst = -np.inf
    for _ in range(iters):
        u, _ = tan.act(obs)
        for i in range(3):
            for k in range(i + 1, 3):
                worst = max(worst, spec.value(x[i], u[i], x[k], u[k]))
    err = float(np.abs(u - u_star).max())
    return [
        _row('Tan', 'every iterate satisfies the coupled constraints (violation-free)', 'arXiv:2404.07571 Prop. 5, Thm. 1(3)',
             f'max c_ik over {iters} iterates = {worst:.2e}', worst <= 1e-6),
        _row('Tan', 'iterates converge to the centralised optimum (weights %s, static law Eq. (21))' % (tuple(weights),),
             'arXiv:2404.07571 Thm. 1(2)', f'max |u - u*| = {err:.2e}', err < 1e-3),
    ]


def pcca_noncooperating(dts=(0.02, 0.005)):
    """2008.12092 Prop. 1: against an agent that keeps u = u0, h >= O(dt): the host takes full responsibility."""
    out = []
    for dt in dts:
        sc = Encounter(EncounterConfig(name='pcca_nc', starts=[[-4.0, 0.0]], goals=[[4.0, 0.0]],
                                       ext_starts=[[4.0, 0.3]], ext_vels=[[-0.8, 0.0]]))
        log = simulate(sc, SingleIntegrator(), PairwiseBarrier(), PCCA(), horizon=10.0, dt=dt, seed=0)
        out.append((dt, _min_ext_dist(log)))
    (dt0, d0), (dt1, d1) = out
    pen0, pen1 = max(0.0, 1 - d0), max(0.0, 1 - d1)
    return [_row('PCCA', 'host alone keeps h >= O(dt) against a non-cooperating agent; the gap shrinks with dt',
                 'arXiv:2008.12092 Prop. 1',
                 f'min dist {d0:.4f} (dt={dt0}), {d1:.4f} (dt={dt1})',
                 pen0 < 0.05 and pen1 <= pen0 + 1e-9)]


def pcca_matches_central(dt=0.02):
    """2012.10261 Sec. V: PCCA performs as the centralised QP (two cooperating agents, head-on)."""
    def sc():
        return Encounter(EncounterConfig(name='pcca_hd', starts=[[-4.0, 0.0], [4.0, 0.2]], goals=[[4.0, 0.0], [-4.0, 0.2]]))
    lp = simulate(sc(), SingleIntegrator(), PairwiseBarrier(), PCCA(), horizon=12.0, dt=dt, seed=0)
    lo = simulate(sc(), SingleIntegrator(), PairwiseBarrier(), Oracle(), horizon=12.0, dt=dt, seed=0)
    dev = float(np.abs(lp.x - lo.x).max())
    return [_row('PCCA', 'two cooperating PCCA agents follow the centralised solution', 'arXiv:2012.10261 Sec. V; 2008.12092 Eq. (19)',
                 f'max |p_pcca - p_central| = {dev:.3f}, min dist {_min_team_dist(lp):.4f}',
                 dev < 0.1 and _min_team_dist(lp) > 1 - 0.01)]


def risk_ratio_shares(dt=0.02):
    """2305.13467 Thm. 2: omega_ij + omega_ji = 1, so the two halves sum to the central constraint; safe swap."""
    log = simulate(_swap(), SingleIntegrator(), PairwiseBarrier(), RiskRatio(), horizon=15.0, dt=dt, seed=0)
    s = max(abs(om + inf['omega'][(k, i)] - 1) for inf in log.info for (i, k), om in inf['omega'].items()
            if (k, i) in inf['omega'])
    d = _min_team_dist(log)
    return [
        _row('RiskRatio', 'pairwise responsibility weights sum to one', 'arXiv:2305.13467 Thm. 2, Eq. (8)-(10)',
             f'max |omega_ij + omega_ji - 1| = {s:.1e}', s < 1e-12),
        _row('RiskRatio', 'cooperating agents stay collision-free (6-agent position swap)', 'arXiv:2305.13467 Thm. 2, Example 2',
             f'min dist {d:.4f}', d > 1 - 0.01),
    ]


def swaps(dt=0.02):
    """Position swap (2305.13467 Example 2; 2012.10261 Sec. V uses 5 agents): no collisions among cooperating agents."""
    out = []
    for name, solver, src in [('Tan', Tan(), 'arXiv:2404.07571 Thm. 1(3)'), ('PCCA', PCCA(), 'arXiv:2012.10261 Prop. 1, Sec. V')]:
        log = simulate(_swap(weights=(1.0, 3.0)), SingleIntegrator(), PairwiseBarrier(), solver, horizon=15.0, dt=dt, seed=0)
        d = _min_team_dist(log)
        reached = float(np.linalg.norm(log.x[-1] - (-log.x[0]), axis=1).max())
        measured, note = f'min dist {d:.4f}, max distance to goal at 15 s {reached:.2f}', ''
        if name == 'Tan':
            X = log.x
            D = np.linalg.norm(X[:, :, None] - X[:, None], axis=3)
            D[:, np.arange(X.shape[1]), np.arange(X.shape[1])] = np.inf
            bad = np.where(D.min(axis=(1, 2)) < 1 - 1e-3)[0]
            infeasible = np.array([log.info[t]['slack'].sum() > 1e-6 for t in range(len(log.info))])
            if len(bad):
                note = (f'violation at {len(bad)} steps; the local QP was infeasible (Assumption 3, Slater, fails: '
                        f'up to 5 active pair rows on 2 inputs) at {infeasible[bad].mean():.0%} of them')
        out.append(_row(name, 'cooperating agents stay collision-free (6-agent position swap)', src, measured,
                        d > 1 - 0.01, note))
    return out


def all_checks():
    return tan_frozen_convergence() + pcca_noncooperating() + pcca_matches_central() + risk_ratio_shares() + swaps()
