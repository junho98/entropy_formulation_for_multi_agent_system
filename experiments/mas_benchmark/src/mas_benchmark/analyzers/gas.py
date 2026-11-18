"""Group price spread: are prices equal across a connected group of agents (gas-like)?"""
import numpy as np

from ..core import Analyzer


def agent_prices(inf, N):
    """Scalar price per agent: info['lam_agent'] (gas solver) or, for pairwise solvers, the mean of i's active pair
    prices (0 if none)."""
    if 'lam_agent' in inf and inf['lam_agent']:
        return np.array([inf['lam_agent'].get(i, 0.0) for i in range(N)])
    lam = [[] for _ in range(N)]
    for (i, _), m in inf.get('mu', {}).items():
        if m > 0:
            lam[i].append(m)
    return np.array([np.mean(v) if v else 0.0 for v in lam])


class GroupSpread(Analyzer):
    """Per step, connected components of the team contact graph (pairs closer than r_c); for components of size >= 2
    with a positive mean price, CV = std/mean of the members' scalar prices. Reported: median and mean CV over
    (step, component), and the fraction of agent-steps with a positive price."""
    name = 'group_spread'

    def __init__(self, r_c=3.0):
        self.r_c = r_c

    def __call__(self, log):
        N = log.x.shape[1]
        cvs, pos = [], []
        for t, inf in enumerate(log.info):
            lam = agent_prices(inf, N)
            pos.append(np.mean(lam > 0))
            X = log.x[t]
            D = np.linalg.norm(X[:, None] - X[None], axis=2) < self.r_c
            seen = np.zeros(N, bool)
            for s in range(N):
                if seen[s]:
                    continue
                comp, stack = [], [s]
                seen[s] = True
                while stack:
                    a = stack.pop(); comp.append(a)
                    for b in np.where(D[a] & ~seen)[0]:
                        seen[b] = True; stack.append(b)
                if len(comp) >= 2 and lam[comp].mean() > 0:
                    cvs.append(lam[comp].std() / lam[comp].mean())
        return dict(group_cv_median=float(np.median(cvs)) if cvs else np.nan,
                    group_cv_mean=float(np.mean(cvs)) if cvs else np.nan, price_on_frac=float(np.mean(pos)))
