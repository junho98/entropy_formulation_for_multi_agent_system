"""Beta, round 2: w~ read on the first 25 constrained steps with that neighbour (then frozen). Same sweep as round 1;
appends a section to results/beta.md with the round-1 rows for comparison.

    python scripts/run_beta_rc.py [--workers 11]
"""
import argparse
import json
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from run_beta import RES, WB, job as _job, ms
import run_beta

NEW = {'beta (rc), W0 = 1x, no leak': f'beta_eps0.1_W0{WB:g}_leakinf_rc',
       'beta (rc), W0 = 1x, leak 30 s': f'beta_eps0.1_W0{WB:g}_leak30_rc',
       'beta (rc), W0 = 0.5x, no leak': f'beta_eps0.1_W0{0.5 * WB:g}_leakinf_rc',
       'beta (rc), W0 = 0.5x, leak 30 s': f'beta_eps0.1_W0{0.5 * WB:g}_leak30_rc'}
run_beta.VARIANTS.update(NEW)
OLD_RC = 'beta, W0 = 1x, no leak, read on constrained steps (diagnostic)'


def job(sc, var, seed):
    return _job(sc, var, seed)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=11)
    args = ap.parse_args()
    old = [json.loads(l) for l in (RES / 'beta.jsonl').read_text().splitlines()]
    reuse = [dict(r, variant='beta (rc), W0 = 1x, no leak') for r in old if r['variant'] == OLD_RC]   # identical setting
    jobs = [(sc, v, s) for sc in ('S1', 'S4') for v in NEW if v != 'beta (rc), W0 = 1x, no leak' for s in range(6)]
    with ProcessPoolExecutor(args.workers) as ex:
        rows = list(ex.map(job, *zip(*jobs))) + reuse
    (RES / 'beta_rc.jsonl').write_text('\n'.join(json.dumps(r) for r in rows) + '\n')
    g = defaultdict(list)
    for r in old + rows:
        g[(r['scenario'], r['variant'])].append(r)
    show = ['final', 'beta, W0 = 1x, no leak', 'beta, W0 = 1x, leak 30 s', 'beta, W0 = 0.5x, no leak',
            'beta, W0 = 0.5x, leak 30 s'] + list(NEW)
    L = ['', '## Round 2: w~ read on the first 25 constrained steps with that neighbour', '',
         'Rule: the effective-weight reading uses the first 25 exchange steps with that neighbour at which the contact is '
         'constrained (s_i < eps or s_k < eps), then freezes (rows "beta (rc)"). Everything else as in round 1; round-1 rows '
         '(neighbours effectively read as 1) repeated for comparison. The "W0 = 1x, no leak" rc row is the round-1 '
         'diagnostic run (same setting, same seeds).', '']
    for sc in ('S1', 'S4'):
        L += [f'### {sc}', '',
              '| setting | cost | W std/mean | W range | min dist. agents | viol. agents (%) | min dist. ext. | viol. ext. (%) | '
              'max |r_ik+r_ki| | imbalance (time-w.) | w~ read: exact | within one cell | mean |ln(w~/true)| | max w~ | '
              'P(not following), true followers (mean / p95) |',
              '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
        for v in show:
            rr = g[(sc, v)]
            L.append(f"| {v} | {ms([r['cost'] for r in rr])} | {ms([r['W_cv'] for r in rr])} | {ms([r['W_range'] for r in rr], nd=2)} | "
                     f"{min(r['min_dist_team'] for r in rr):.2f} | {ms([r['viol_team'] for r in rr], pct=True)} | "
                     f"{np.nanmin([r['min_dist_ext'] for r in rr]):.2f} | {ms([r['viol_ext'] for r in rr], pct=True)} | "
                     f"{max(r['gap_max'] for r in rr):.2g} | {ms([r.get('imbalance_time') for r in rr], nd=2)} | "
                     f"{np.nanmean([r.get('read_exact', np.nan) for r in rr]):.2f} | {np.nanmean([r.get('read_within1', np.nan) for r in rr]):.2f} | "
                     f"{np.nanmean([r.get('read_logerr', np.nan) for r in rr]):.2f} | {np.nanmax([r.get('wt_max', np.nan) for r in rr]):.2g} | "
                     f"{np.nanmean([r['p_not_follow_mean'] for r in rr]):.3f} / {np.nanmean([r['p_not_follow_p95'] for r in rr]):.3f} |")
        L.append('')
    with (RES / 'beta.md').open('a') as f:
        f.write('\n'.join(L) + '\n')
    print('\n'.join(L))
