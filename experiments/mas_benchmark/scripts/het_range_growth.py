"""Internal: why per-step centred beta's W range keeps growing in HET-E4/E8 (results/grid2x3/het_range_growth_note.md).
One 600 s rerun, HET-E8 + ts1.5, seed 0, per-step beta W0 4.22 at eps 0.2 (as run_beta_step.py builds it), recording per
step beta_i, W_i and the cost split by what constrains agent i (outsider row active / team rows only / none).

    python scripts/het_range_growth.py   -> results/grid2x3/diag/het_e8_beta_step_eps0.2_seed0.npz
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_grid2x3_ts as G                                                # noqa: E402
from mas_benchmark.analyzers import Cost                                  # noqa: E402
from mas_benchmark.configs import evaluate                                # noqa: E402

CELL, SEED = 'HET-E8+ts1.5', 0

if __name__ == '__main__':
    cb2 = json.loads((G.OUT / 'cbar_eps0.2.json').read_text())
    log = evaluate(CELL, 'beta', SEED, 600.0, **dict(G.OURS, per_step=True, eps=0.2, W0=4.22, cbar=cb2[CELL]))
    N = log.x.shape[1]
    tracks = np.asarray(log.meta['tracks'])
    body = np.empty_like(tracks); body[tracks] = np.arange(len(tracks))
    beta = np.array([[inf['beta'][i] for i in range(N)] for inf in log.info])
    W = np.array([inf['W'] for inf in log.info])
    f = 0.5 * log.weights[None] * np.sum((log.u - log.u_nom) ** 2, axis=2)
    ext = np.zeros_like(f, bool); team = np.zeros_like(f, bool)
    for k, inf in enumerate(log.info):
        for (i, t), lam in inf['mu'].items():
            if lam > 0:
                (ext if body[t] >= N else team)[k, i] = True
    out = G.OUT / 'diag' / 'het_e8_beta_step_eps0.2_seed0.npz'
    np.savez_compressed(out, t=np.asarray(log.t), beta=beta, W=W, f=f, ext=ext, team=team, weights=log.weights,
                        cbar=cb2[CELL])
    print('cost', Cost()(log)['cost'], '->', out)
