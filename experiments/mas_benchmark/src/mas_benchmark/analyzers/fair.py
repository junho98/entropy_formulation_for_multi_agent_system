"""Fairness over time: spread of accumulated cost, per-weight-group cost, copy gap and inference accuracy."""
import numpy as np

from ..core import Analyzer
from .agreement import body_of


class FairOverTime(Analyzer):
    """W_i = accumulated own cost over the run (from the log, so it applies to every solver).
    spread: max - min and std/mean of W over agents; cost by weight group (mean f_i for w = 1 and w = 3);
    copy gap |r_ik + r_ki| over team agreements: median, p95, max;
    inference (fair solver only): at the end of each team contact, |mu_hat_ik - mu_k,i| (truth: k's frozen mu for
    the contact with i) and whether w_hat_ik = w_k."""
    name = 'fair'

    def __call__(self, log):
        N = log.x.shape[1]
        f = 0.5 * log.weights[None] * np.sum((log.u - log.u_nom) ** 2, axis=2)
        W = f.sum(0) * log.dt
        out = dict(W_range=float(W.max() - W.min()), W_cv=float(W.std() / W.mean()),
                   cost_w1=float(f[:, log.weights == 1].mean()), cost_w3=float(f[:, log.weights == 3].mean())
                   if np.any(log.weights == 3) else np.nan, W=W.tolist())
        body = body_of(log); track = {b: t for t, b in body.items()}
        gaps = []
        for inf in log.info:
            r = inf.get('r', {})
            for (i, tk), v in r.items():
                k = body.get(tk, -1)
                if 0 <= k < N and i < k and (k, track[i]) in r:
                    gaps.append(abs(v + r[(k, track[i])]))
        g = np.array(gaps) if gaps else np.array([np.nan])
        out.update(gap_med=float(np.nanmedian(g)), gap_p95=float(np.nanpercentile(g, 95)), gap_max=float(np.nanmax(g)))
        last, last_act, ever, seen_keys = {}, {}, {}, set()
        for inf in log.info:
            for key, mh in inf.get('mu_hat', {}).items():
                i, tk = key
                k = body.get(tk, -1)
                if 0 <= k < N:
                    truth = inf.get('mu_own', {}).get((k, track[i]))
                    if truth is not None:
                        rec = (mh, truth, inf.get('w_hat', {}).get(key), float(log.weights[k]))
                        last[key] = rec
                        if inf.get('mu', {}).get(key, 0.0) > 0 or inf.get('mu', {}).get((k, track[i]), 0.0) > 0:
                            last_act[key] = rec          # last step with the pair's price active
                        if inf.get('ever_c', {}).get(key):
                            ever[key] = rec              # contact constrained at least once (last record)
                        seen_keys.add(key)
        if seen_keys:
            out['frac_constrained'] = len(ever) / len(seen_keys)
        if ever:
            ve = list(ever.values())
            tr_ = [b for _, b, _, _ in ve]; mh_ = [a for a, _, _, _ in ve]
            out.update(mu_abs_err_c=float(np.mean(np.abs(np.array(mh_) - np.array(tr_)))),
                       mu_hat_mean_c=float(np.mean(mh_)), mu_true_mean_c=float(np.mean(tr_)),
                       mu_corr_c=float(np.corrcoef(mh_, tr_)[0, 1]) if len(ve) > 2 and np.std(tr_) > 0 and np.std(mh_) > 0 else np.nan,
                       w_acc_c=float(np.mean([c == d for _, _, c, d in ve if c is not None]))
                       if any(c is not None for _, _, c, _ in ve) else np.nan,
                       w_fixed_frac_c=float(np.mean([c is not None for _, _, c, _ in ve])), n_contacts_c=len(ve))
        if last_act:
            va = list(last_act.values())
            tr_ = [b for _, b, _, _ in va]; mh_ = [a for a, _, _, _ in va]
            out.update(mu_abs_err_act=float(np.mean(np.abs(np.array(mh_) - np.array(tr_)))),
                       mu_hat_mean_act=float(np.mean(mh_)), mu_true_mean_act=float(np.mean(tr_)),
                       mu_corr_act=float(np.corrcoef(mh_, tr_)[0, 1]) if len(va) > 2 and np.std(tr_) > 0 and np.std(mh_) > 0 else np.nan,
                       w_acc_act=float(np.mean([c == d for _, _, c, d in va if c is not None]))
                       if any(c is not None for _, _, c, _ in va) else np.nan, n_contacts_act=len(va))
        if last:
            vals = list(last.values())
            out.update(mu_abs_err=float(np.mean([abs(a - b) for a, b, _, _ in vals])),
                       mu_true_mean=float(np.mean([b for _, b, _, _ in vals])),
                       mu_hat_mean=float(np.mean([a for a, _, _, _ in vals])),
                       w_acc=float(np.mean([c == d for _, _, c, d in vals if c is not None])) if any(c is not None for _, _, c, _ in vals) else np.nan,
                       n_contacts=len(vals))
        return out
