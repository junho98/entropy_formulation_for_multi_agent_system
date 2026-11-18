"""Method configurations with tunable knobs: build(method, **params) -> (solver, spec).

Knobs shared by the CBF-based methods live in the specification the method runs with: the class-K gain `kappa` and a
safety `margin` (the method keeps rho_ctrl = rho (1 + margin)). Evaluation always uses the true rho (see `evaluate`).
Method knobs: Tan `k0`, `sat_width` (Eq. 26 law unchanged); Risk ratio `c_scale` (c = c_scale x its default for that
kappa); Ours / centred beta: `ke`, `delta`, `window`, `follow_prior`, `eps` (+ `W0`, `cbar`, `beta_max`).
"""
from .core import simulate
from .dynamics import SingleIntegrator
from .scenarios import make_scenario
from .solvers import Oracle, PCCA, Reciprocal, RiskRatio, Tan, Thermo, ThermoBeta, ThermoRho
from .specs import PairwiseBarrier

RHO = 1.0


def build(method, kappa=2.0, margin=0.0, **p):
    spec = PairwiseBarrier(kappa=kappa, rho=RHO * (1.0 + margin))
    if method == 'oracle':
        sol = Oracle()
    elif method == 'reciprocal':
        sol = Reciprocal()
    elif method == 'pcca':
        sol = PCCA()
    elif method == 'tan':
        sol = Tan(k0=p.get('k0', 1.0), sat_width=p.get('sat_width', 0.1))
    elif method == 'risk_ratio':
        c = (2 * spec.sensing_range * 2 * 1.2 + kappa * spec.sensing_range ** 2 + 1.0) * p.get('c_scale', 1.0)
        sol = RiskRatio(c=c)
    elif method == 'ours':
        sol = Thermo(law='mutual', **p)
    elif method == 'ours_rho':
        sol = ThermoRho(**p)
    elif method == 'beta':
        q = dict(p); q.setdefault('beta_max', 8.0); q.setdefault('tau_leak', float('inf'))
        q.setdefault('per_step', True)          # 2026-11-15: beta updated every step (paper v42); pass per_step=False for the old per-contact freeze
        sol = ThermoBeta(**q)
    else:
        raise ValueError(method)
    return sol, spec


def evaluate(scenario, method, seed, horizon=120.0, dt=0.02, **params):
    """Run once; the returned Log carries the true rho, so analyzers score against it whatever margin was used."""
    sol, spec = build(method, **params)
    log = simulate(make_scenario(scenario), SingleIntegrator(), spec, sol, horizon, dt, seed)
    log.rho = RHO
    return log
