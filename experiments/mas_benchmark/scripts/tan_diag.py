"""Internal: where Tan's team and outsider violations come from (results/grid2x3/tan_team_violation_note.md).

Reruns the grid's Tan configuration (k0 1, sat_width 0.1) for a few cells/seeds with extra recording. The solver is
unchanged: TanRec only keeps the observation and wraps the module's soft_qp to keep each local QP's slack z and
multipliers; the recorded run's cost is checked against the grid row.

    python scripts/tan_diag.py   -> results/grid2x3/diag/tan_<cell>_seed<s>.npz, printed tables
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_tuning as T                                                    # noqa: E402
from mas_benchmark.analyzers import Cost, Safety                          # noqa: E402
from mas_benchmark.configs import RHO, build                              # noqa: E402
from mas_benchmark.core import simulate                                   # noqa: E402
from mas_benchmark.dynamics import SingleIntegrator                       # noqa: E402
from mas_benchmark.scenarios import make_scenario                         # noqa: E402
import mas_benchmark.solvers.tan as tanmod                                # noqa: E402

OUT = Path(__file__).resolve().parents[1] / 'results' / 'grid2x3'
RUNS = [('HET-E8', 0), ('HET-E8', 2), ('HOM-E8', 0), ('HET-E0', 0)]
TOL = 1e-6                     # slack tolerance, as Tan.slack_tol
_CALLS = []
_orig = tanmod.soft_qp


def _soft_qp(*a, **k):
    out = _orig(*a, **k)
    _CALLS.append((np.array(out[1]), np.array(out[2])))
    return out


class TanRec(tanmod.Tan):
    """Tan with recording only: per step and agent, each row's (body, external, slack z, multiplier), the pair keys
    whose y moved this step (both multipliers reported last step), and the shift y_i - y_k used in the row."""

    def reset(self, *a, **k):
        super().reset(*a, **k)
        self.rec = []

    def act(self, obs):
        moved = {key for key in self.c if (key[1], key[0]) in self.c}
        _CALLS.clear()
        U, info = super().act(obs)
        N = obs.u_nom.shape[0]
        step = []
        for i, (z, lam) in zip(range(N), _CALLS):
            rows = []
            for nb, zr, lr in zip(obs.neighbours[i], z, lam):
                b = N + nb.ext_index if nb.external else nb.index
                shift = np.nan if nb.external else self.y.get((i, b), 0.0) - self.y.get((b, i), 0.0)
                rows.append((b, nb.external, float(zr), float(lr), shift, (not nb.external) and (i, b) in moved))
            step.append(rows)
        self.rec.append(step)
        return U, info


def run(cell, seed):
    tanmod.soft_qp = _soft_qp
    sol, spec = build('tan', **T.DEFAULT['tan'])
    rec = TanRec(k0=sol.k0, sat_width=sol.sat_width)
    log = simulate(make_scenario(cell + '+ts1.5'), SingleIntegrator(), spec, rec, 120.0, 0.02, seed)
    log.rho = RHO
    N = log.x.shape[1]
    rows = [(k, i, *r) for k, step in enumerate(rec.rec) for i, rs in enumerate(step) for r in rs]
    A = np.array([(k, i, b, e, z, l, s, m) for k, i, b, e, z, l, s, m in rows], float).reshape(-1, 8)
    np.savez_compressed(OUT / 'diag' / f'tan_{cell}_seed{seed}.npz', rows=A, x=log.x[..., :2], q=log.ext_x[..., :2], N=N)
    return cell, seed, Cost()(log)['cost'], Safety()(log)


def analyse(cell, seed):
    d = np.load(OUT / 'diag' / f'tan_{cell}_seed{seed}.npz')
    A, x, q, N = d['rows'], d['x'], d['q'], int(d['N'])
    k, i, b, ext, z, lam, shift, moved = A.T
    k, i, b, ext = k.astype(int), i.astype(int), b.astype(int), ext.astype(bool)
    K = x.shape[0]
    P = np.concatenate([x, q], axis=1) if q.shape[1] else x
    dist = np.linalg.norm(P[k, i] - P[k, b], axis=1)
    viol = dist < 0.95 * RHO
    key = k * N + i
    soft = np.zeros(K * N, bool); np.logical_or.at(soft, key, z > TOL)
    nb_o = np.bincount(key, (ext & ((lam > 1e-9) | (z > TOL))), K * N)
    nb_t = np.bincount(key, (~ext & ((lam > 1e-9) | (z > TOL))), K * N)
    r = {}
    r['soft_share'] = soft.mean()
    for lo, hi, nm in ((0, 0, '0'), (1, 1, '1'), (2, 99, '2+')):
        m = (nb_o >= lo) & (nb_o <= hi)
        r[f'soft|out{nm}'] = soft[m].mean() if m.any() else np.nan
        r[f'share_out{nm}'] = m.mean()
        m = (nb_t >= lo) & (nb_t <= hi)
        r[f'soft|team{nm}'] = soft[m].mean() if m.any() else np.nan
    zo, zt = z[ext].sum(), z[~ext].sum()
    r['slack_share_out'] = zo / max(zo + zt, 1e-300)
    sk = soft[key]
    r['relaxed_out|soft'] = np.mean(np.bincount(key[ext & (z > TOL)], minlength=K * N)[soft] > 0) if soft.any() else np.nan
    r['relaxed_team|soft'] = np.mean(np.bincount(key[~ext & (z > TOL)], minlength=K * N)[soft] > 0) if soft.any() else np.nan
    # team violations: pair-steps (i < b both team) under 0.95 rho, from i's row (each team pair appears twice)
    tm = ~ext & (i < b)
    tv = tm & viol
    other = {(kk, ii, bb): (zz, ll) for kk, ii, bb, zz, ll in zip(k[~ext], i[~ext], b[~ext], z[~ext], lam[~ext])}
    zk = np.array([other.get((kk, bb, ii), (0.0, 0.0))[0] for kk, ii, bb in zip(k[tv], i[tv], b[tv])])
    soft_i, soft_b = soft[k[tv] * N + i[tv]], soft[k[tv] * N + b[tv]]
    out_i, out_b = nb_o[k[tv] * N + i[tv]] > 0, nb_o[k[tv] * N + b[tv]] > 0
    r['team_viol_pairsteps'] = int(tv.sum())
    r['tv|either soft'] = np.mean(soft_i | soft_b) if tv.any() else np.nan
    r['tv|team row relaxed'] = np.mean((z[tv] > TOL) | (zk > TOL)) if tv.any() else np.nan
    r['tv|either outsider row binding'] = np.mean(out_i | out_b) if tv.any() else np.nan
    r['tv|y frozen'] = np.mean(moved[tv] < 0.5) if tv.any() else np.nan
    r['tv|neither soft'] = np.mean(~(soft_i | soft_b)) if tv.any() else np.nan
    ov = ext & viol
    r['out_viol_pairsteps'] = int(ov.sum())
    r['ov|outsider row relaxed'] = np.mean(z[ov] > TOL) if ov.any() else np.nan
    r['ov|agent soft'] = np.mean(soft[k[ov] * N + i[ov]]) if ov.any() else np.nan
    # common definition: violations per pair-step in sensing range (each unordered pair once)
    r['per_pairstep_team'] = tv.sum() / max(tm.sum(), 1)
    r['per_pairstep_out'] = ov.sum() / max(ext.sum(), 1)
    r['pairsteps_team'], r['pairsteps_out'] = int(tm.sum()), int(ext.sum())
    return r


if __name__ == '__main__':
    (OUT / 'diag').mkdir(exist_ok=True)
    grid = {(r['cell'][:6], r['seed']): r for r in map(json.loads, (OUT / 'runs.jsonl').read_text().splitlines())
            if r['conf'] == 'tan'}
    with ProcessPoolExecutor(len(RUNS)) as ex:
        for cell, seed, cost, saf in ex.map(run, *zip(*RUNS)):
            g = grid[(cell, seed)]
            print(cell, seed, 'cost', cost, 'grid', g['cost'], 'identical' if cost == g['cost'] else 'DIFFERENT',
                  'viol team/ext', saf['viol_team'], saf['viol_ext'], flush=True)
    for cell, seed in RUNS:
        print(cell, seed, json.dumps({kk: (round(v, 4) if isinstance(v, float) else v) for kk, v in analyse(cell, seed).items()}))
