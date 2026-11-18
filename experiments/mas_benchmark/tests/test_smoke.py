import numpy as np

from mas_benchmark.analyzers import AgreementGap, Cost, Safety
from mas_benchmark.core import simulate
from mas_benchmark.dynamics import SingleIntegrator
from mas_benchmark.scenarios import make_scenario
from mas_benchmark.solvers import Reciprocal, Thermo, make_solver
from mas_benchmark.specs import PairwiseBarrier


def run(name, seed=0, solver=None):
    return simulate(make_scenario(name), SingleIntegrator(), PairwiseBarrier(), solver or Reciprocal(),
                    horizon=1.0, dt=0.02, seed=seed)


def test_shares_sum_to_constraint():
    spec = PairwiseBarrier()
    xi, xk, ui, uk = np.array([0., 0.]), np.array([2., 1.]), np.array([.3, -.2]), np.array([-.5, .4])
    d = xi - xk
    assert np.isclose(spec.value(xi, ui, xk, uk), -2 * d @ (ui - uk) - 2.0 * (d @ d - 1.0))


def test_seed_fixes_world_across_methods():
    a, b = run('S4', seed=3), run('S4', seed=3)
    assert np.array_equal(a.ext_x, b.ext_x) and np.array_equal(a.x[0], b.x[0])


def test_input_bound_and_metrics():
    log = run('S2')
    A, bnd = SingleIntegrator().input_polytope()
    assert np.all(log.u @ A.T <= bnd + 1e-6)
    m = {**Cost()(log), **Safety()(log)}
    assert m['cost'] >= 0 and 0 <= m['viol_ext'] <= 1


def test_bound_limits():
    from mas_benchmark.solvers.thermo.bound import certified_bound, log_mgf_atom_exp, log_mgf_uniform_max
    lw = np.zeros(1)
    assert np.isclose(certified_bound(lw, log_mgf_atom_exp(0.3, -50.0, 1e7)[None], 0.05)[0], 0.3, atol=1e-3)
    A, _ = certified_bound(lw, log_mgf_uniform_max(-5.0, -1.0, 1.0)[None], 0.05)
    assert 0.9 - 1e-9 <= A <= 1.0        # >= the 95% quantile, <= the max


def test_thermo_copies_stay_opposite_plain_law():
    log = run('S1', solver=Thermo(eps=0.1, law='plain'))
    assert AgreementGap()(log)['gap_max'] < 1e-9


def test_thermo_follow_law_gap_nonpositive():
    log = run('S4', solver=Thermo(eps=0.1))
    g = AgreementGap()(log)
    assert g['gap_min'] <= 1e-12 and g['gap_max'] <= -g['gap_min'] + 1e-12    # r_ik + r_ki <= 0


class _LocalOnly:
    """Exposes nothing but agent i's own observation."""
    def __init__(self, obs):
        self._obs = obs

    @property
    def n_agents(self):
        return self._obs.n_agents

    def local(self, i):
        return self._obs.local(i)


def test_local_methods_use_only_local_views():
    from mas_benchmark.solvers import PCCA
    for make in [lambda: Thermo(eps=0.2), PCCA, Reciprocal]:
        a, b = make(), make()
        sc = make_scenario('S4')
        rng = np.random.default_rng(0)
        x = sc.reset(rng)
        dyn, spec = SingleIntegrator(), PairwiseBarrier()
        for s_ in (a, b):
            s_.reset(sc, dyn, spec, 0.02)
        from mas_benchmark.core import Observation, sense
        ex, eu = sc.externals()
        obs = Observation(0.0, x, sc.nominal_input(x), sc.weights(), sense(x, np.zeros_like(x), ex, eu, dyn, spec,
                          rng.permutation(len(x) + len(ex))), ex, eu, sc.v_env)
        ua, _ = a.act(obs)
        ub, _ = b.act(_LocalOnly(obs))       # AttributeError if anything beyond local(i) is touched
        assert np.allclose(ua, ub)


def test_every_solver_runs_and_respects_input_bound():
    A, bnd = SingleIntegrator().input_polytope()
    for name in ['oracle', 'tan', 'pcca', 'risk_ratio', 'reciprocal', 'ours_eps0.2']:
        log = run('S4', solver=make_solver(name))
        assert np.all(log.u @ A.T <= bnd + 1e-6), name


def test_batched_bound_matches_scalar():
    from mas_benchmark.solvers.thermo.belief import TemperatureBelief
    rng = np.random.default_rng(1)
    th = Thermo(); th.spec = PairwiseBarrier()
    bs, rs, al, hs = [], [], [], []
    for _ in range(40):
        b = TemperatureBelief()
        for _ in range(rng.integers(0, 50)):
            b.append(rng.normal(0, 0.5), rng.choice([1.0, 0.3, 0.0]), rng.normal(0, 0.2))
        d = rng.uniform(1, 5)
        bs.append(b); rs.append(rng.normal(0, 1)); al.append(2 * d); hs.append(d * d - 1)
    A, _, _ = th.room_batch(bs, np.array(rs), np.array(al), np.array(hs), 1.0)
    for j in range(40):
        assert np.isclose(A[j], th.room(bs[j], rs[j], al[j], hs[j], 1.0)[0], rtol=0, atol=1e-12)


def test_newton_step_keeps_copies_opposite():
    log = run('S1', solver=Thermo(eps=0.1, law='plain', step='newton'))
    assert AgreementGap()(log)['gap_max'] < 1e-9


def test_agreement_memory_gap_nonpositive():
    log = run('S1', solver=make_solver('ours_eps0.1_mem'))
    g = AgreementGap()(log)
    assert np.isnan(g['gap_min']) or g['gap_min'] <= 1e-12


def test_region_step_keeps_copies_opposite():
    log = run('S1', solver=Thermo(eps=0.1, law='plain', step='region'))
    assert AgreementGap()(log)['gap_max'] < 1e-9


def test_mutual_trust_region_copies_exact():
    for sc in ('S1', 'S4'):
        log = run(sc, solver=make_solver('ours_eps0.1_mutual_region'))
        g = AgreementGap()(log)
        assert np.isnan(g['gap_max']) or g['gap_max'] < 1e-12


def test_isolation_region_copies_exact():
    for sc in ('S1', 'S4'):
        log = run(sc, solver=make_solver('ours_eps0.1_mutual_region_iso'))
        g = AgreementGap()(log)
        assert np.isnan(g['gap_max']) or g['gap_max'] < 1e-12


def test_projection_copies_exact():
    for sc in ('S1', 'S4'):
        log = run(sc, solver=make_solver('ours_eps0.1_mutual_region_iso_proj'))
        g = AgreementGap()(log)
        assert np.isnan(g['gap_max']) or g['gap_max'] < 1e-12
