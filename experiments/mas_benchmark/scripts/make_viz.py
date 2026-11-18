"""Figures and animations for slides -> results/viz/.

    python scripts/make_viz.py record      # seed-0 trajectories (results/viz/traj/*.npz); single runs, no grid
    python scripts/make_viz.py figures     # scenario overview + result figures (PDF + PNG)
    python scripts/make_viz.py anim        # mp4 + gif animations
    python scripts/make_viz.py all
    python scripts/make_viz.py grid        # 2x3 grid (target_sep 1.5): record, scene figures, animations -> results/viz/grid2x3/
    python scripts/make_viz.py local       # one agent's own view, HET-E8 seed 2, per-step beta -> results/viz/local/
    python scripts/make_viz.py tan         # the same agent under Tan (grid configuration) next to ours -> results/viz/local/
    python scripts/make_viz.py tan_e0      # ours vs Tan as published in HET-E0 (no outsiders) -> results/viz/local/

Trajectories: S1, S4 final and centred beta (W0 4.22, beta_max 8) 600 s; S2, S3 final 60 s; S4 PCCA and Tan 60 s.
Result figures read results/final_mutual/grid.jsonl and results/beta_horizon.jsonl.
Grid: HOM-E0, HET-E0, HOM-E8, HET-E8 (+ts1.5), one representative seed per cell (the seed in 0-5 whose Ours eps 0.1
cost is closest to the 24-seed median), 120 s, Ours eps 0.1, Ours + centred beta (W0 4.22, c-bar of the cell), tuned
Oracle and tuned PCCA, built exactly as in run_grid2x3_ts.py.
"""
import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from mas_benchmark.configs import RHO, build
from mas_benchmark.viz import Trajectory, record, results, scene

RES = Path(__file__).resolve().parents[1] / 'results'
OUT = RES / 'viz'
TRAJ = OUT / 'traj'
WB = 16.88
CBAR = {'S1': 10.3774 / 120, 'S4': 29.3127 / 120}
SOLVER = {'final': lambda sc: 'ours_eps0.1_mutual',
          'centred': lambda sc: f'beta_eps0.1_W0{0.25 * WB:g}_leakinf_bmax8_cbar{CBAR[sc]:.6g}',
          'pcca': lambda sc: 'pcca', 'tan': lambda sc: 'tan'}
RUNS = [('S1', 'final', 600.0), ('S4', 'final', 600.0), ('S1', 'centred', 600.0), ('S4', 'centred', 600.0),
        ('S2', 'final', 60.0), ('S3', 'final', 60.0), ('S4', 'pcca', 60.0), ('S4', 'tan', 60.0)]
SEED = 0
G_OUT = OUT / 'grid2x3'
G_CELLS = ('HOM-E0', 'HET-E0', 'HOM-E8', 'HET-E8')
G_TS = '+ts1.5'
G_CONFS = [('ours_eps0.1', 'Ours'), ('beta_W04.22', r'Ours + centred $\beta$'), ('oracle_tuned', 'Oracle (tuned)'),
           ('pcca_tuned', 'PCCA (tuned)')]


def path(sc, conf):
    return TRAJ / f'{sc}_{conf}_seed{SEED}.npz'


def _rec(sc, conf, horizon):
    record(sc, SOLVER[conf](sc), horizon, SEED).save(path(sc, conf))
    return sc, conf


def load(sc, conf):
    return Trajectory.load(path(sc, conf))


def do_record(workers):
    TRAJ.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(workers) as ex:
        for sc, conf in ex.map(_rec, *zip(*RUNS)):
            print('recorded', sc, conf, flush=True)


def do_figures():
    grid = [json.loads(l) for l in (RES / 'final_mutual' / 'grid.jsonl').read_text().splitlines()]
    hz = [json.loads(l) for l in (RES / 'beta_horizon.jsonl').read_text().splitlines()]
    trs = [load(sc, 'final') for sc in ('S1', 'S2', 'S3', 'S4')]
    scene.overview(trs, int(round(30.0 / trs[0].dt)), OUT / 'scenarios',
                   names=['S1: team only, $w$ = 1, 3', 'S2: 8 reactive outsiders', 'S3: 4 slow outsiders',
                          'S4: 8 non-reactive outsiders'])
    results.safety(grid, OUT / 'safety_S2_S4')
    results.tradeoff(grid, OUT / 'tradeoff_S3_S4')
    results.range_vs_time(hz, OUT / 'fairness_range_vs_time')
    results.cv_bars(hz, OUT / 'fairness_cv_120s')
    results.work_curves([(sc, load(sc, 'final'), load(sc, 'centred')) for sc in ('S1', 'S4')], OUT / 'work_per_agent_seed0')
    print('figures done', flush=True)


def _anim(job):
    if job == 'S1' or job == 'S4':
        scene.animate([load(job, 'final'), load(job, 'centred')], ['Ours', r'Ours, centred $\beta$'],
                      OUT / f'anim_{job}_final_vs_centred', t_end=60.0)
    else:
        scene.animate([load('S4', 'final'), load('S4', 'pcca'), load('S4', 'tan')], ['Ours', 'PCCA', 'Tan'],
                      OUT / 'anim_S4_ours_pcca_tan', t_end=60.0, colour='weight', contacts=False)
    return job


def do_anim(workers):
    with ProcessPoolExecutor(min(3, workers)) as ex:
        for j in ex.map(_anim, ('S1', 'S4', 'cmp')):
            print('animated', j, flush=True)


def g_params(conf, cell):
    import run_grid2x3_ts as G
    cb = json.loads((RES / 'grid2x3' / 'cbar.json').read_text())
    return {'ours_eps0.1': ('ours', dict(G.OURS, eps=0.1)),
            'beta_W04.22': ('beta', dict(G.OURS, eps=0.1, W0=4.22, cbar=cb[cell])),
            'oracle_tuned': ('oracle', G.TUNED['oracle']), 'pcca_tuned': ('pcca', G.TUNED['pcca'])}[conf]


def g_seeds():
    import numpy as np
    rows = [json.loads(l) for l in (RES / 'grid2x3' / 'runs.jsonl').read_text().splitlines()]
    out = {}
    for c in G_CELLS:
        cost = {r['seed']: r['cost'] for r in rows if r['conf'] == 'ours_eps0.1' and r['cell'] == c + G_TS}
        med = float(np.median(list(cost.values())))
        out[c] = min(range(6), key=lambda s: abs(cost[s] - med))
    return out


def g_path(cell, conf, seed):
    return G_OUT / 'traj' / f'{cell}_{conf}_seed{seed}.npz'


def _g_rec(cell, conf, seed):
    m, p = g_params(conf, cell + G_TS)
    sol, spec = build(m, **p)
    record(cell + G_TS, sol, 120.0, seed, spec=spec, rho=RHO).save(g_path(cell, conf, seed))
    return cell, conf


def _g_anim(cell, seed):
    trs = [Trajectory.load(g_path(cell, k, seed)) for k, _ in G_CONFS]
    scene.animate(trs, [n for _, n in G_CONFS], G_OUT / f'anim_{cell}', t_end=60.0)
    return cell


def do_grid(workers):
    sd = g_seeds()
    (G_OUT / 'traj').mkdir(parents=True, exist_ok=True)
    (G_OUT / 'seeds.json').write_text(json.dumps(sd, indent=1))
    jobs = [(c, k, sd[c]) for c in G_CELLS for k, _ in G_CONFS if not g_path(c, k, sd[c]).exists()]
    with ProcessPoolExecutor(workers) as ex:
        for c, k in ex.map(_g_rec, *zip(*jobs)) if jobs else ():
            print('recorded', c, k, flush=True)
    k30 = int(round(30.0 / 0.02))
    scene.overview([Trajectory.load(g_path(c, 'ours_eps0.1', sd[c])) for c in G_CELLS], k30, G_OUT / 'scenes_cells',
                   names=[f'{c} (seed {sd[c]}), Ours' for c in G_CELLS])
    for c in G_CELLS:
        scene.overview([Trajectory.load(g_path(c, k, sd[c])) for k, _ in G_CONFS], k30, G_OUT / f'scene_{c}',
                       names=[n for _, n in G_CONFS])
    print('scene figures done', flush=True)
    with ProcessPoolExecutor(min(4, workers)) as ex:
        for c in ex.map(_g_anim, G_CELLS, [sd[c] for c in G_CELLS]):
            print('animated', c, flush=True)


L_OUT = OUT / 'local'
L_CELL, L_SEED, L_T = 'HET-E8', 2, 60.0


def do_local():
    """Per-step centred beta (W0 4.22, eps 0.1; built as run_beta_step.py builds beta_step_W04.22) with contact logging,
    120 s recorded; the agent shown is the w = 1 agent with most steps constrained by a teammate and an outsider at once
    in the first 60 s; video and still cover 0-60 s."""
    import numpy as np
    from mas_benchmark.viz import local
    import run_grid2x3_ts as G
    L_OUT.mkdir(parents=True, exist_ok=True)
    cell = L_CELL + G_TS
    cb = json.loads((RES / 'grid2x3' / 'cbar.json').read_text())[cell]
    sol, spec = build('beta', **dict(G.OURS, per_step=True, eps=0.1, W0=4.22, cbar=cb, log_contacts=True))
    tr, log = record(cell, sol, 120.0, L_SEED, spec=spec, rho=RHO, return_log=True)
    tr.save(L_OUT / f'{L_CELL}_beta_step_seed{L_SEED}.npz')
    K = int(round(L_T / log.dt))
    log60 = type('L', (), dict(info=log.info[:K], x=log.x, meta=log.meta))
    cand = [i for i in range(log.x.shape[1]) if log.weights[i] == 1.0]
    sq = {i: local.squeezed_steps(log60, i) for i in cand}
    agent = max(cand, key=lambda i: sq[i])
    loc = local.extract(log, agent, cb, spec.kappa)
    loc.save(L_OUT / f'{L_CELL}_beta_step_seed{L_SEED}_agent{agent}.npz')
    from mas_benchmark.analyzers import Cost
    (L_OUT / 'choice.json').write_text(json.dumps(dict(cell=cell, seed=L_SEED, agent=agent, squeezed_steps=sq,
                                                        cost=Cost()(log)['cost']), indent=1))
    print('agent', agent, 'squeezed steps (w = 1 agents, first 60 s):', sq, flush=True)
    v = local.LocalView(tr, loc, t_end=L_T)
    R = loc.rows                                           # still: the step of highest pressure P_i in 0-60 s
    st = np.round(R['t'] / log.dt).astype(int)
    P = np.bincount(st, R['lam'] * (R['alpha'] / 2) ** 2, len(log.t))[:K]
    v.still(L_OUT / f'local_{L_CELL}_agent{agent}', float(np.argmax(P) * log.dt))
    v.animate(L_OUT / f'local_{L_CELL}_agent{agent}')
    print('local view done', flush=True)


def do_tan():
    """Tan as in the grid (k0 1, sat_width 0.1), HET-E8 seed 2, 120 s recorded; compared with the per-step beta run of
    do_local for the agent chosen there; video and still cover 0-60 s."""
    import numpy as np
    from mas_benchmark.scenarios import make_scenario
    from mas_benchmark.viz import local
    import run_tuning as T
    cell = L_CELL + G_TS
    choice = json.loads((L_OUT / 'choice.json').read_text())
    agent = choice['agent']
    p_tr, p_loc = L_OUT / f'{L_CELL}_tan_seed{L_SEED}.npz', L_OUT / f'{L_CELL}_tan_seed{L_SEED}_agent{agent}.npz'
    if not (p_tr.exists() and p_loc.exists()):                # recorded once; reruns only redraw
        from mas_benchmark.analyzers import Cost
        sol, spec = build('tan', **T.DEFAULT['tan'])
        tr_t, log = record(cell, sol, 120.0, L_SEED, spec=spec, rho=RHO, return_log=True)
        tr_t.save(p_tr)
        local.extract_tan(log, agent, make_scenario(cell).v_env, spec.kappa).save(p_loc)
        print('tan cost', Cost()(log)['cost'], flush=True)
    tr_t, loc_t = Trajectory.load(p_tr), local.LocalLog.load(p_loc)
    tr_o = Trajectory.load(L_OUT / f'{L_CELL}_beta_step_seed{L_SEED}.npz')
    loc_o = local.LocalLog.load(L_OUT / f'{L_CELL}_beta_step_seed{L_SEED}_agent{agent}.npz')
    note = (r'$\dagger$ Tan + local worst-case row (our extension): each outsider is added as a local constraint '
            r'(Tan et al., Sec. VI-A), bounded at $v_{env}$ = 1.0 with its identity given')
    v = local.CompareView([(r'Ours + centred $\beta$', 'centred', tr_o, loc_o), (r'Tan$\dagger$', 'tan', tr_t, loc_t)],
                          t_end=L_T, note=note)
    v.still(L_OUT / f'compare_tan_{L_CELL}_agent{agent}', 35.6)
    v.animate(L_OUT / f'compare_tan_{L_CELL}_agent{agent}')
    print('tan comparison done', flush=True)


E0_CELL = 'HET-E0'


def _rec_e0(method, params, seed):
    from mas_benchmark.analyzers import Cost
    sol, spec = build(method, **params)
    tr, log = record(E0_CELL + G_TS, sol, 120.0, seed, spec=spec, rho=RHO, return_log=True)
    return tr, log, spec, Cost()(log)['cost']


def do_tan_e0():
    """Ours (per-step centred beta W0 4.22, eps 0.1, contact logging) and Tan as published (grid configuration) in
    HET-E0. Seed: among 0-5, the one whose costs of both methods are jointly closest to their 24-seed medians (largest
    relative deviation smallest). Agent: the one with most steps constrained by a teammate in 0-60 s, summed over both
    runs. Both 120 s costs must equal the grid rows; video and still cover 0-60 s."""
    import numpy as np
    from mas_benchmark.viz import local
    import run_grid2x3_ts as G
    import run_tuning as T
    cell = E0_CELL + G_TS
    rows = [json.loads(l) for l in (RES / 'grid2x3' / 'runs.jsonl').read_text().splitlines()]
    cost = {k: {r['seed']: r for r in rows if r['conf'] == k and r['cell'] == cell} for k in ('beta_step_W04.22', 'tan')}
    med = {k: float(np.median([r['cost'] for r in v.values()])) for k, v in cost.items()}
    seed = min(range(6), key=lambda s: max(abs(cost[k][s]['cost'] - med[k]) / med[k] for k in cost))
    cb = json.loads((RES / 'grid2x3' / 'cbar.json').read_text())[cell]
    tr_o, log_o, spec_o, c_o = _rec_e0('beta', dict(G.OURS, per_step=True, eps=0.1, W0=4.22, cbar=cb, log_contacts=True), seed)
    tr_t, log_t, spec_t, c_t = _rec_e0('tan', T.DEFAULT['tan'], seed)
    for k, c in (('beta_step_W04.22', c_o), ('tan', c_t)):
        assert c == cost[k][seed]['cost'], (k, c, cost[k][seed]['cost'])
    K, N = int(round(L_T / log_o.dt)), log_o.x.shape[1]
    team_steps = np.zeros(N)
    for log in (log_o, log_t):
        for inf in log.info[:K]:
            for i in {i for (i, _), v in inf['mu'].items() if v > 0}:
                team_steps[i] += 1
    agent = int(np.argmax(team_steps))
    loc_o = local.extract(log_o, agent, cb, spec_o.kappa)
    loc_t = local.extract_tan(log_t, agent, make_scenario_v_env(cell), spec_t.kappa)
    choice = dict(cell=cell, seed=seed, agent=agent, weight=float(log_o.weights[agent]),
                  team_constrained_steps_0_60s=[int(x) for x in team_steps], medians=med,
                  seed_rows={k: {q: cost[k][seed][q] for q in ('cost', 'viol_team', 'W_cv', 'W_range')} for k in cost})
    (L_OUT / f'choice_{E0_CELL}.json').write_text(json.dumps(choice, indent=1))
    print(json.dumps(choice), flush=True)
    v = local.CompareView([(r'Ours + centred $\beta$', 'centred', tr_o, loc_o), ('Tan', 'tan', tr_t, loc_t)], t_end=L_T)
    st = np.round(loc_o.rows['t'] / log_o.dt).astype(int)          # still: the step of highest pressure in 0-60 s
    P = np.bincount(st, loc_o.rows['lam'] * (loc_o.rows['alpha'] / 2) ** 2, len(log_o.t))[:K]
    v.still(L_OUT / f'compare_tan_{E0_CELL}_agent{agent}', float(np.argmax(P) * log_o.dt))
    v.animate(L_OUT / f'compare_tan_{E0_CELL}_agent{agent}')
    print('tan_e0 comparison done', flush=True)


def make_scenario_v_env(cell):
    from mas_benchmark.scenarios import make_scenario
    return make_scenario(cell).v_env


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('what', choices=('record', 'figures', 'anim', 'all', 'grid', 'local', 'tan', 'tan_e0'))
    ap.add_argument('--workers', type=int, default=8)
    a = ap.parse_args()
    if a.what in ('record', 'all'):
        do_record(a.workers)
    if a.what in ('figures', 'all'):
        do_figures()
    if a.what in ('anim', 'all'):
        do_anim(a.workers)
    if a.what == 'grid':
        do_grid(a.workers)
    if a.what == 'local':
        do_local()
    if a.what == 'tan':
        do_tan()
    if a.what == 'tan_e0':
        do_tan_e0()
