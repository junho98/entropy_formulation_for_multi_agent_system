"""Work per contact in the final configuration: for each agent i and each contact (body within sensing range, from
the step it enters to the step it leaves: the span over which beta is frozen), dW_c = base cost of i accumulated over
the contact, int 1/2 w_i |u_i - u0_i|^2 dt. Also mean contact duration and mean number of simultaneous contacts.

    python scripts/beta_work_per_contact.py [--seeds 0 1 2 3 4 5]  -> results/beta_work_per_contact.json (+ printed)
"""
import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from mas_benchmark.core import simulate
from mas_benchmark.dynamics import SingleIntegrator
from mas_benchmark.scenarios import make_scenario
from mas_benchmark.solvers import make_solver
from mas_benchmark.specs import PairwiseBarrier

RES = Path(__file__).resolve().parents[1] / 'results'
SENSE = 5.0


def job(sc, seed):
    log = simulate(make_scenario(sc), SingleIntegrator(), PairwiseBarrier(), make_solver('ours_eps0.1_mutual'), 120.0, 0.02, seed)
    f = 0.5 * log.weights[None] * np.sum((log.u - log.u_nom) ** 2, axis=2) * log.dt        # (K, N) cost per step
    P = np.concatenate([log.x, log.ext_x], axis=1) if log.ext_x.shape[1] else log.x
    N, B = log.x.shape[1], P.shape[1]
    D = np.linalg.norm(log.x[:, :, None] - P[:, None], axis=3)                              # (K, N, B)
    inside = D <= SENSE
    for i in range(N):
        inside[:, i, i] = False
    dW, dur = [], []
    for i in range(N):
        cum = np.concatenate([[0.0], np.cumsum(f[:, i])])
        for b in range(B):
            s = inside[:, i, b].astype(int)
            edges = np.diff(np.concatenate([[0], s, [0]]))
            starts, ends = np.where(edges == 1)[0], np.where(edges == -1)[0]
            for a, e in zip(starts, ends):
                dW.append(cum[e] - cum[a]); dur.append((e - a) * log.dt)
    return dict(scenario=sc, seed=seed, dW=dW, dur=dur, n_contacts=float(inside.sum(axis=2).mean()))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--seeds', nargs='+', type=int, default=list(range(6)))
    args = ap.parse_args()
    jobs = [(sc, s) for sc in ('S1', 'S4') for s in args.seeds]
    with ProcessPoolExecutor(min(11, len(jobs))) as ex:
        res = list(ex.map(job, *zip(*jobs)))
    out = {}
    for sc in ('S1', 'S4'):
        dW = np.concatenate([r['dW'] for r in res if r['scenario'] == sc])
        dur = np.concatenate([r['dur'] for r in res if r['scenario'] == sc])
        out[sc] = dict(n=int(len(dW)), median=float(np.median(dW)), p10=float(np.percentile(dW, 10)),
                       p90=float(np.percentile(dW, 90)), mean=float(dW.mean()), dur_mean=float(dur.mean()),
                       dur_median=float(np.median(dur)),
                       n_sim=float(np.mean([r['n_contacts'] for r in res if r['scenario'] == sc])))
    (RES / 'beta_work_per_contact.json').write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
