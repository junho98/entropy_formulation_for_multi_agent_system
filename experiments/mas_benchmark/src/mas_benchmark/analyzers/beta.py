"""Beta variant: reading of the neighbours' effective weight and following mass of true followers."""
import numpy as np

from ..core import Analyzer
from .agreement import body_of


class BetaReading(Analyzer):
    """For each team contact (i, k): the effective weight w~_k decided by i (first step it appears) against k's true
    QP weight w_k beta_k at that step; exact-match rate, rate within one grid step, mean |log ratio|; max w~ decided;
    and P(not following) = 1 - following mass at the last step of each team contact (true followers)."""
    name = 'beta_reading'

    def __call__(self, log):
        from ..solvers.thermo.beta import GRID
        N, body = log.x.shape[1], body_of(log)
        first, lastfol = {}, {}
        for inf in log.info:
            weff = inf.get('w_eff', {})
            for (i, tk), wh in inf.get('wt_hat', {}).items():
                k = body.get(tk, -1)
                if 0 <= k < N and (i, tk) not in first:
                    first[(i, tk)] = (wh, weff.get(k, np.nan))
            for (i, tk), fol in inf.get('follow', {}).items():
                if 0 <= body.get(tk, -1) < N:
                    lastfol[(i, tk)] = fol
        out = dict(p_not_follow_mean=float(np.mean([1 - f for f in lastfol.values()])) if lastfol else np.nan,
                   p_not_follow_p95=float(np.percentile([1 - f for f in lastfol.values()], 95)) if lastfol else np.nan)
        if first:
            dec = np.array([a for a, _ in first.values()]); tru = np.array([b for _, b in first.values()])
            gi = lambda x: int(np.argmin(np.abs(np.array(GRID) - x)))
            out.update(read_exact=float(np.mean([gi(a) == gi(b) for a, b in zip(dec, tru)])),
                       read_within1=float(np.mean([abs(gi(a) - gi(b)) <= 1 for a, b in zip(dec, tru)])),
                       read_logerr=float(np.mean(np.abs(np.log(dec / tru)))), wt_max=float(dec.max()),
                       true_wt_mean=float(tru.mean()), dec_wt_mean=float(dec.mean()), n_reads=len(first))
        return out


class BetaTuning(Analyzer):
    """Jain index and max of the accumulated base cost W_i (from the log), fraction of agent-time with beta at the cap,
    and, at team violations (some pair closer than 0.95 rho), the first step of each violating pair episode: beta of
    both agents, their number of contacts, and whether each agent's QP weight came from another contact's frozen beta
    (beta_QP > the beta frozen for this pair)."""
    name = 'beta_tuning'

    def __init__(self, beta_max=4.0, frac=0.95):
        self.beta_max, self.frac = beta_max, frac

    def __call__(self, log):
        N, body = log.x.shape[1], body_of(log)
        track = {b: t for t, b in body.items()}
        f = 0.5 * log.weights[None] * np.sum((log.u - log.u_nom) ** 2, axis=2)
        W = f.sum(0) * log.dt
        cap = [np.mean([inf['beta'].get(i, 1.0) >= self.beta_max - 1e-9 for i in range(N)]) for inf in log.info if 'beta' in inf]
        low = [np.mean([inf['beta'].get(i, 1.0) <= 1.0 / self.beta_max + 1e-9 for i in range(N)]) for inf in log.info if 'beta' in inf]
        below1 = [np.mean([inf['beta'].get(i, 1.0) < 1.0 - 1e-9 for i in range(N)]) for inf in log.info if 'beta' in inf]
        out = dict(jain=float(W.sum() ** 2 / (N * np.sum(W ** 2))), W_max=float(W.max()),
                   cap_frac=float(np.mean(cap)) if cap else np.nan, cap_low_frac=float(np.mean(low)) if low else np.nan,
                   below1_frac=float(np.mean(below1)) if below1 else np.nan)
        D = np.linalg.norm(log.x[:, :, None] - log.x[:, None], axis=3)
        events, open_ = [], set()
        for t, inf in enumerate(log.info):
            now = set()
            for i in range(N):
                for k in range(i + 1, N):
                    if D[t, i, k] < self.frac * log.rho:
                        now.add((i, k))
                        if (i, k) not in open_ and 'beta' in inf:
                            bi, bk = inf['beta'].get(i), inf['beta'].get(k)
                            pi = inf['beta_pair'].get((i, track[k])); pk = inf['beta_pair'].get((k, track[i]))
                            events.append(dict(t=t * log.dt, i=i, k=k, beta_i=bi, beta_k=bk,
                                               nc_i=inf['n_contacts'].get(i), nc_k=inf['n_contacts'].get(k),
                                               pair_beta_i=pi, pair_beta_k=pk,
                                               from_other_i=bool(pi is not None and bi > pi + 1e-9),
                                               from_other_k=bool(pk is not None and bk > pk + 1e-9),
                                               w_i=float(log.weights[i]), w_k=float(log.weights[k]),
                                               min_dist=float(D[t, i, k])))
            open_ = now
        out['viol_events'] = events
        return out
