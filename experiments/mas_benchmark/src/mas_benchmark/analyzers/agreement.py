import numpy as np

from ..core import Analyzer


def body_of(log):
    """track id -> body index (team 0..N-1, then externals), from the run's anonymous track permutation."""
    tracks = log.meta.get('tracks')
    n = log.x.shape[1] + log.ext_x.shape[1]
    return {int(t): b for b, t in enumerate(tracks)} if tracks is not None else {b: b for b in range(n)}


class AgreementGap(Analyzer):
    """r_ik + r_ki over all team agreements and steps (needs info['r'] keyed by (i, track)).

    gap_max = max |r_ik + r_ki|; gap_min = most negative r_ik + r_ki. Prop. 2.7 needs r_ik + r_ki >= 0 (allowances
    a = -sum r within the budget); a negative gap is safe only through the coverage (v40 Remark 5.3)."""
    name = 'agreement_gap'

    def __call__(self, log):
        N, body = log.x.shape[1], body_of(log)
        track = {b: t for t, b in body.items()}
        sums = []
        for inf in log.info:
            r = inf.get('r', {})
            for (i, tk), v in r.items():
                k = body.get(tk, -1)
                if 0 <= k < N and i < k and (k, track[i]) in r:
                    sums.append(v + r[(k, track[i])])
        if not sums:
            return dict(gap_max=np.nan, gap_min=np.nan)
        sums = np.array(sums)
        return dict(gap_max=float(np.abs(sums).max()), gap_min=float(sums.min()))


def encounters(log, tol=1e-6):
    """Isolated two-agent encounters: maximal runs of steps where team pair (i, k), i < k, has i's only active
    price toward k and k's only active price toward i (mu > tol). -> list of dict(i, k, start, mu_i, mu_k)."""
    N, body = log.x.shape[1], body_of(log)
    done, open_ = [], {}
    for t, inf in enumerate(log.info):
        act = {}
        for (i, tk), m in inf.get('mu', {}).items():
            if m > tol:
                act.setdefault(i, {})[body.get(tk, -1)] = m
        now = set()
        for i, a in act.items():
            if len(a) == 1:
                (k, mi), = a.items()
                if i < k < N and set(act.get(k, {})) == {i}:
                    now.add((i, k))
                    e = open_.setdefault((i, k), dict(i=i, k=k, start=t, mu_i=[], mu_k=[]))
                    e['mu_i'].append(mi); e['mu_k'].append(act[k][i])
        for key in [key for key in open_ if key not in now]:
            done.append(open_.pop(key))
    done += list(open_.values())
    for e in done:
        e['mu_i'], e['mu_k'] = np.array(e['mu_i']), np.array(e['mu_k'])
    return done


class PriceImbalance(Analyzer):
    """|mu_i - mu_k| / (mu_i + mu_k) in isolated two-agent encounters (Sec. 12.1, S1).

    Each encounter (see `encounters`) is scored by its mean imbalance; encounters are averaged overall and split
    by equal / different weights. `early` scores only the first `early_s` seconds of each encounter (the first
    activation, where v40 Sec. 13 bounds the imbalance below by |w_a - w_b|/(w_a + w_b)), `settled` the rest
    (encounters longer than `early_s` only). `time` weights every encounter step equally (long encounters count
    more than fragments); `n_short` counts encounters no longer than `early_s`."""
    name = 'price_imbalance'

    def __init__(self, tol=1e-6, early_s=0.2):
        self.tol, self.early_s = tol, early_s

    def __call__(self, log):
        n0 = max(1, int(round(self.early_s / log.dt)))
        w = log.weights
        rows = []
        for e in encounters(log, self.tol):
            imb = np.abs(e['mu_i'] - e['mu_k']) / (e['mu_i'] + e['mu_k'])
            same = w[e['i']] == w[e['k']]
            rows.append((same, imb.mean(), imb[:n0].mean(), imb[n0:].mean() if len(imb) > n0 else np.nan, imb))
        mean = lambda v: float(np.nanmean(v)) if len(v) and not np.all(np.isnan(v)) else np.nan
        out = dict(n_encounters=len(rows), n_short=sum(len(r[4]) <= n0 for r in rows))
        for tag, sel in [('', lambda r: True), ('_same_w', lambda r: r[0]), ('_diff_w', lambda r: not r[0])]:
            sub = [r for r in rows if sel(r)]
            out[f'imbalance{tag}'] = mean([r[1] for r in sub])
            out[f'imbalance_early{tag}'] = mean([r[2] for r in sub])
            out[f'imbalance_settled{tag}'] = mean([r[3] for r in sub])
            allv = np.concatenate([r[4] for r in sub]) if sub else np.array([])
            out[f'imbalance_time{tag}'] = float(allv.mean()) if len(allv) else np.nan     # step-weighted
        return out
