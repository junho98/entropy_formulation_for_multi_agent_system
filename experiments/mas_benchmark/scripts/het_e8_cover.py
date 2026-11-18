"""Internal: why Ours (with cover) has more outsider violation than Ours no cover in HET-E8 (HOM-E8 as control).
Reads results/grid2x3/clog_main (per-step, seeds 0-5) and contacts (per-contact, seeds 0-23). No runs.

    python scripts/het_e8_cover.py   -> prints the tables used in results/grid2x3/het_e8_cover_note.md
"""
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parents[1] / 'results' / 'grid2x3'
N, DT, HV = 8, 0.02, 0.95 ** 2 - 1.0          # team size, step, h = d^2 - rho^2 below which d < 0.95 rho (rho = 1)
CONFS = ('ours_eps0.1', 'ours_nocover_eps0.1')


def ms(v, nd=3):
    v = np.asarray(v, float)
    return f'{v.mean():.{nd}f} ± {v.std(ddof=1) / np.sqrt(len(v)):.{nd}f}'


def per_contact(cell, conf, seed):
    d = np.load(OUT / 'contacts' / f'{cell}+ts1.5_{conf}_seed{seed}.npz')
    o = d['k'] >= N
    return dict(sensed=d['n_steps'][o].sum() * DT / N, constrained=(d['n_steps'] * d['constrained'])[o].sum() * DT / N)


def per_step(cell, conf, seed):
    d = np.load(OUT / 'clog_main' / f'{cell}+ts1.5_{conf}_seed{seed}.npz')
    i, k, t, lam, s, h = d['i'].astype(int), d['k'].astype(int), d['t'], d['lam'], d['s'], d['h']
    o, act = k >= N, lam > 0
    viol = h < HV
    w3 = (i % 2 == 1)                                      # HET: weights alternate 1, 3 (agent 1, 3, ... is w = 3)
    key = np.round(t / DT).astype(np.int64) * N + i        # agent-step
    u, inv = np.unique(key, return_inverse=True)
    n_act = np.bincount(inv, act.astype(int), len(u))
    n_team = np.bincount(inv, (act & ~o).astype(int), len(u))
    neg = np.bincount(inv, (s < 0).astype(int), len(u)) > 0
    squeezed = n_team[inv] > 0                             # row's agent also has a constrained team contact
    oc = o & act
    r = dict(viol_per_step=viol[oc].sum() / max(oc.sum(), 1),
             viol_per_step_squeezed=viol[oc & squeezed].sum() / max((oc & squeezed).sum(), 1),
             viol_per_step_alone=viol[oc & ~squeezed].sum() / max((oc & ~squeezed).sum(), 1),
             squeezed_share=(oc & squeezed).sum() / max(oc.sum(), 1),
             viol_steps_w1=viol[o & ~w3].sum() * DT / 4, viol_steps_w3=viol[o & w3].sum() * DT / 4,
             exp_w1=oc[~w3].sum() * DT / 4, exp_w3=oc[w3].sum() * DT / 4)
    for lo, hi, nm in ((1, 1, '1'), (2, 2, '2'), (3, 99, '3+')):
        m = (n_act >= lo) & (n_act <= hi)
        r[f'neg_{nm}'] = neg[m].mean() if m.any() else np.nan
        r[f'share_{nm}'] = m.mean()
    return r


if __name__ == '__main__':
    for cell in ('HET-E8', 'HOM-E8'):
        print(f'## {cell}')
        A = {c: [per_contact(cell, c, s) for s in range(24)] for c in CONFS}
        for q, lab in (('sensed', 'outsider in sensing range, s per agent'), ('constrained', 'outsider contact constrained (lam > 0), s per agent')):
            a, b = [x[q] for x in A[CONFS[0]]], [x[q] for x in A[CONFS[1]]]
            print(f'(a) {lab} [24 seeds]: Ours {ms(a, 2)}, no cover {ms(b, 2)}, paired diff {ms(np.subtract(a, b), 2)}')
        B = {c: [per_step(cell, c, s) for s in range(6)] for c in CONFS}
        keys = ['viol_per_step', 'viol_per_step_squeezed', 'viol_per_step_alone', 'squeezed_share',
                'exp_w1', 'exp_w3', 'viol_steps_w1', 'viol_steps_w3',
                'share_1', 'neg_1', 'share_2', 'neg_2', 'share_3+', 'neg_3+']
        for q in keys:
            a, b = [x[q] for x in B[CONFS[0]]], [x[q] for x in B[CONFS[1]]]
            print(f'[6 seeds] {q}: Ours {ms(a, 4)}, no cover {ms(b, 4)}, paired diff {ms(np.subtract(a, b), 4)}')
