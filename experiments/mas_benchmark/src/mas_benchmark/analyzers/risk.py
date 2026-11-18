"""Per-agent risk allotment (v41 Prop. 6.4): coverage, agent temperature and nu equalisation."""
import numpy as np

from ..core import Analyzer


class RiskAllotment(Analyzer):
    """From the solver's info['cov'] (U_ik = R_ik - r_ik), info['nu'] (nu_ik = lam_ik theta*_ik / delta_ik on active
    contacts) and info['delta']:
      coverage      mean over agent-steps of sum_k U_ik;
      T             agent temperature T_i = nu_i delta_i, nu_i = mean of nu_ik over i's active contacts (agent-steps
                    with at least one active contact), with delta_i = sum_k delta_ik;
      nu_cv         coefficient of variation of nu_ik across an agent's active contacts (agent-steps with >= 2 active),
                    the equalisation check (0 when the allotment equalises nu);
      union_delta   mean sum_k delta_ik (the per-step risk an agent actually spends)."""
    name = 'risk_allotment'

    def __call__(self, log):
        N = log.x.shape[1]
        cov, T, cv, dsum, series = [], [], [], [], []
        for inf in log.info:
            c = [0.0] * N; ds = [0.0] * N; nu = [[] for _ in range(N)]
            for (i, _), v in inf.get('cov', {}).items():
                c[i] += v
            for (i, _), v in inf.get('delta', {}).items():
                ds[i] += v
            for (i, _), v in inf.get('nu', {}).items():
                nu[i].append(v)
            cov += c; dsum += ds
            Ts = [np.mean(nu[i]) * ds[i] for i in range(N) if nu[i]]
            T += Ts
            series.append(float(np.mean(Ts)) if Ts else np.nan)
            cv += [np.std(nu[i]) / np.mean(nu[i]) for i in range(N) if len(nu[i]) >= 2 and np.mean(nu[i]) > 0]
        T = np.array(T)
        return dict(coverage=float(np.mean(cov)), union_delta=float(np.mean(dsum)),
                    T_mean=float(T.mean()) if len(T) else np.nan, T_median=float(np.median(T)) if len(T) else np.nan,
                    T_p90=float(np.percentile(T, 90)) if len(T) else np.nan,
                    nu_cv=float(np.median(cv)) if cv else np.nan, T_series=series)
