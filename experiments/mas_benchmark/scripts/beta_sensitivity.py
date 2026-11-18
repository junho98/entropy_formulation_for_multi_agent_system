"""Why the w~ reading fails: sensitivity of the predicted response to w~ on constrained steps.

Reruns the round-1 setting (beta, W0 = 1x, no leak; seeds 0-5, 120 s, S1 and S4) with extra logging. On every exchange
step with s_i < eps or s_k < eps: k_e alpha^2; the in-layer coefficient a(w~) = w~/(w~ + k_e alpha^2) for w~ in {1,2,4};
and |y_hat(w~=1) - y_hat(w~=4)| / sigma, where y_hat = a u_bar + b is the predicted approach speed of k in the regime of
its replicated slack, u_bar = k's true nominal approach speed (offline truth) and sigma = sqrt(s2) the likelihood noise.

    python scripts/beta_sensitivity.py  -> appends to results/beta.md
"""
from pathlib import Path

import numpy as np

from mas_benchmark.core import simulate
from mas_benchmark.dynamics import SingleIntegrator
from mas_benchmark.scenarios import make_scenario
from mas_benchmark.solvers.thermo.beta import ThermoBeta
from mas_benchmark.solvers.thermo.fair import lin_w
from mas_benchmark.specs import PairwiseBarrier

RES = Path(__file__).resolve().parents[1] / 'results'
WB = 16.88


class Logged(ThermoBeta):
    def act(self, obs):
        self._unom = {nb.track: (obs.u_nom[nb.index] if nb.index >= 0 else nb.u_prev)
                      for nbs in obs.neighbours for nb in nbs}
        return super().act(obs)

    def exchange(self, body, pair):
        P = pair.prev
        d, alpha, h, kappa = P['d'], P['alpha'], P['h'], self.spec.kappa
        dhat = d / np.linalg.norm(d)
        y_k = float(dhat @ body.u_prev)
        y_i = float(-dhat @ P['u_i'])
        s_k = -(alpha * y_k - 0.5 * kappa * h + P['R_ki'])
        s_i = -(alpha * y_i - 0.5 * kappa * h + P['R_ik'])
        if s_i < self.eps or s_k < self.eps:
            ub = float(dhat @ self._unom.get(body.track, np.zeros(2)))
            yhat = {w: (lambda ab: ab[0] * ub + ab[1])(lin_w(s_k, P['R_ki'], alpha, h, kappa, self.eps, self.ke, w))
                    for w in (1.0, 4.0)}
            regime = 'layer' if self.tol_layer(s_k) else ('wall' if s_k <= 1e-6 else 'free')
            self.rec.append((self.ke * alpha ** 2, *[w / (w + self.ke * alpha ** 2) for w in (1.0, 2.0, 4.0)],
                             abs(yhat[1.0] - yhat[4.0]) / np.sqrt(self.s2), regime))
        return super().exchange(body, pair)

    def tol_layer(self, s):
        return 1e-6 < s < self.eps - 1e-6


def q(v):
    v = np.asarray(v, float)
    return f'{np.median(v):.3g} ({np.percentile(v, 10):.3g}–{np.percentile(v, 90):.3g})'


L = ['', '## Decision and sensitivity of the w~ reading', '',
     'Decision (theory side, 2026-11-13): the w~ reading is dropped. The beta variant is round 1 (own β; neighbours at the '
     'public w = 1), now the `ThermoBeta` default; `read=True` / `read_constrained=True` keep the readings as options.', '',
     'Sensitivity, on constrained exchange steps (s_i < ε or s_k < ε) of the round-1 setting (W0 = 1x, no leak; seeds '
     '0–5, 120 s, rerun with logging). Response difference: |ŷ(w~ = 1) − ŷ(w~ = 4)| / σ with ŷ = a ū + b in the '
     'regime of k\'s replicated slack, ū = k\'s true nominal approach speed (offline), σ = √s2 = 0.1005 (likelihood '
     'noise). Median (10–90%).', '',
     '| scenario | steps | k_e α² | a(1) | a(2) | a(4) | response diff. / σ, all | in the layer | at the wall | share in layer / wall / free |',
     '|---|---|---|---|---|---|---|---|---|---|']
for sc in ('S1', 'S4'):
    rec = []
    for seed in range(6):
        s = Logged(eps=0.1, W0=WB, tau_leak=np.inf); s.rec = rec
        simulate(make_scenario(sc), SingleIntegrator(), PairwiseBarrier(), s, 120.0, 0.02, seed)
    k = [r[0] for r in rec]; a1 = [r[1] for r in rec]; a2 = [r[2] for r in rec]; a4 = [r[3] for r in rec]
    dd = [r[4] for r in rec]
    lay = [r[4] for r in rec if r[5] == 'layer']; wal = [r[4] for r in rec if r[5] == 'wall']
    sh = [np.mean([r[5] == x for r in rec]) for x in ('layer', 'wall', 'free')]
    L.append(f'| {sc} | {len(rec)} | {q(k)} | {q(a1)} | {q(a2)} | {q(a4)} | {q(dd)} | {q(lay) if lay else "–"} | '
             f'{q(wal) if wal else "–"} | {sh[0]:.2f} / {sh[1]:.2f} / {sh[2]:.2f} |')
with (RES / 'beta.md').open('a') as f:
    f.write('\n'.join(L) + '\n')
print('\n'.join(L))
