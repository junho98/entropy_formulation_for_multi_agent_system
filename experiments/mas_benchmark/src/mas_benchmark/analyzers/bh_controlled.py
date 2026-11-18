"""Controlled Bretagnolle-Huber check: P_F(A_n^c) + P_out(A_n) >= 1/2 exp(-KL_n), A_n = {r_ik(n) >= m}.

Input records come from `scenarios.hypothesis.run` (one per hypothesis, rule, geometry, sigma, seed), reduced to
r at the requested n, the H_F chain-rule KL at n, and the H_out feasibility margin.
"""
from collections import defaultdict

import numpy as np

NS = (5, 10, 25, 50, 100, 200)


def reduce_run(o, ns=NS):
    """Keep what the bound needs from one run (None if i never activated)."""
    if o is None:
        return None
    pick = lambda s, n: float(s[min(n, len(s) - 1)]) if len(s) else np.nan
    return dict(r={n: pick(o['r'], n) for n in ns}, kl={n: pick(o['kl'], n) for n in ns},
                margin=float(np.min(o['margin'])) if o['margin'] else np.nan,
                min_dist=float(np.min(o['dist'])), t_act=o['t_act'])


def summarize(records, deltas, fracs=(0.25, 0.5, 0.75), ns=NS):
    """records: list of dict(rule, geometry, sigma, hyp, seed, run=<reduced>). deltas[(rule, geometry)] = Delta*.

    Thresholds m: 'feas' = median over H_out runs of the smallest feasibility margin G_i - U_ik after activation
    (the largest r_ik that keeps i's walled problem feasible along the whole H_out encounter), and frac * Delta*.
    -> list of rows (rule, geometry, sigma, n, m_name, m, P_F_fail, P_out_A, KL, bound, sum, gap, counts)."""
    cell = defaultdict(lambda: {'F': [], 'out': []})
    for rec in records:
        if rec['run'] is not None:
            cell[(rec['rule'], rec['geometry'], rec['sigma'])][rec['hyp']].append(rec['run'])
    rows = []
    for (rule, geo, sig), hs in sorted(cell.items()):
        F, O = hs['F'], hs['out']
        if not F or not O:
            continue
        ms = {'feas': float(np.nanmedian([o['margin'] for o in O]))}
        ms.update({f'{f:g}Δ*': f * deltas[(rule, geo)] for f in fracs})
        for n in ns:
            rF = np.array([o['r'][n] for o in F]); rO = np.array([o['r'][n] for o in O])
            KL = float(np.mean([o['kl'][n] for o in F]))
            for name, m in ms.items():
                pf = float(np.mean(~(rF >= m)))
                po = float(np.mean(rO >= m))
                bound = 0.5 * np.exp(-KL)
                rows.append(dict(rule=rule, geometry=geo, sigma=sig, n=n, m_name=name, m=m, P_F_fail=pf, P_out_A=po,
                                 KL=KL, bound=bound, sum=pf + po, gap=pf + po - bound, nF=len(F), nO=len(O)))
    return rows
