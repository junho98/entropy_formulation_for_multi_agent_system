"""One agent's own view next to the arena: `extract` keeps agent i's local quantities from a logged run (contact
logging on), `LocalView` draws the scene with i highlighted and five time panels with a cursor, as a still or an mp4.
`extract_tan` and `CompareView` put the same agent under Tan next to it (see the comparison section below).

Everything in the panels is i's own: its observations, its beliefs about each neighbour, its agreements and prices,
its ledger. Only the scene is ground truth. Per contact (track k, as i sees it):

  lam    lambda_ik = k_e (eps - s_ik)_+, i's layer multiplier after its QP
  theta  theta*_ik, the decision temperature of the certified bound (minimiser over theta)
  follow w_ik(F) = 1 - w_ik(tau = inf), i's posterior mass on k following
  mX, vX predictive mean / variance of k's next usage X = alpha y_k - kappa h / 2 under i's belief
  R      R_ik = A[max(c_k, r_ik)], the certified bound on k's usage; r_ik the agreement; cover U_ik = R_ik - r_ik
Agent summaries (paper v42, Sec. thermo): T_i = sum_k lambda_ik theta*_ik (the agent temperature at the optimal risk
allotment, where lambda_ik theta*_ik = T_i p_ik with sum_k p_ik = 1; the runs use the fixed allotment delta_ik = delta),
P_i = sum_k lambda_ik |d_ik|^2 (virial pressure). Fairness: beta_i and W_i against the public reference c-bar t.
"""
from dataclasses import dataclass, asdict

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FFMpegWriter, FuncAnimation
from matplotlib.collections import LineCollection
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D
from matplotlib.patches import Circle

from . import style
from .scene import draw_frame

FIELDS = ('t', 'k', 'lam', 'theta', 'follow', 'mX', 'vX', 'R', 'r', 'alpha', 'h')
# neighbour colours: categorical, no red (violations) and no grey (outsider bodies)
NB = ['#2a78d6', '#eb6834', '#1baf7a', '#6250d6', '#eda100', '#e87ba4', '#0d2f5e', '#8a5a00', '#3cb6d3', '#a03a8c']


@dataclass
class LocalLog:
    agent: int
    weight: float
    cbar: float
    kappa: float
    t: np.ndarray            # (K,) step times
    beta: np.ndarray         # (K,) beta_i used in the QP
    W: np.ndarray            # (K,) i's ledger W_i
    rows: dict               # per (step, contact) arrays, FIELDS; k is the body index (team 0..N-1, then outsiders)
    n_team: int

    def save(self, path):
        d = {k: v for k, v in asdict(self).items() if k != 'rows'}
        np.savez_compressed(path, **{k: np.asarray(v) for k, v in d.items()}, **{'row_' + k: v for k, v in self.rows.items()})

    @classmethod
    def load(cls, path):
        z = np.load(path)
        rows = {k[4:]: z[k] for k in z.files if k.startswith('row_')}
        return cls(int(z['agent']), float(z['weight']), float(z['cbar']), float(z['kappa']), z['t'], z['beta'], z['W'],
                   rows, int(z['n_team']))


def extract(log, agent, cbar, kappa):
    """Agent `agent`'s rows of info['clog'] plus its beta_i and W_i, from a run with log_contacts=True."""
    tracks = np.asarray(log.meta['tracks'])
    body = np.empty_like(tracks); body[tracks] = np.arange(len(tracks))
    rows = [dict(c, t=t, k=int(body[c['track']]), R=c['U'] + c['r'])
            for t, inf in zip(log.t, log.info) for c in inf.get('clog', []) if c['i'] == agent]
    arr = {k: np.array([r[k] for r in rows], float) for k in FIELDS}
    beta = np.array([inf['beta'][agent] for inf in log.info])
    W = np.array([inf['W'][agent] for inf in log.info])
    return LocalLog(agent, float(log.weights[agent]), cbar, kappa, np.asarray(log.t, float), beta, W, arr,
                    log.x.shape[1])


def squeezed_steps(log, agent):
    """Steps at which `agent` is constrained (lambda > 0) by a teammate and an outsider at once."""
    N = log.x.shape[1]
    tracks = np.asarray(log.meta['tracks'])
    body = np.empty_like(tracks); body[tracks] = np.arange(len(tracks))
    n = 0
    for inf in log.info:
        ks = [int(body[c['track']]) for c in inf.get('clog', []) if c['i'] == agent and c['lam'] > 0]
        n += any(k < N for k in ks) and any(k >= N for k in ks)
    return n


class LocalView:
    """Scene (left) and five panels of one agent's own quantities (right), synced by a time cursor."""
    NEAR = 3.0               # panel 2 shows a neighbour's belief only while it is this close (sensing range is 5)

    def __init__(self, tr, loc, t_end=None, figsize=(19.2, 10.8), dpi=100):
        style.use()
        self.tr, self.loc = tr, loc
        K = len(tr.p) if t_end is None else min(len(tr.p), int(round(t_end / tr.dt)))
        self.K, self.t_end = K, tr.t[K - 1]
        R = loc.rows
        keep = R['t'] <= self.t_end + 1e-9
        self.R = {k: v[keep] for k, v in R.items()}
        # neighbours in order of first contact; colour by that order
        ks, first = np.unique(self.R['k'].astype(int), return_index=True)
        self.nbs = [int(k) for k in ks[np.argsort(first)]]
        self.col = {k: NB[j % len(NB)] for j, k in enumerate(self.nbs)}
        self.fig = plt.figure(figsize=figsize, dpi=dpi)
        gs = GridSpec(5, 2, figure=self.fig, width_ratios=[1.0, 1.15], left=0.01, right=0.95, top=0.93, bottom=0.07,
                      wspace=0.12, hspace=0.42)
        self.ax_s = self.fig.add_subplot(gs[:, 0])
        self.axes = [self.fig.add_subplot(gs[j, 1]) for j in range(5)]
        for ax in self.axes[1:]:
            ax.sharex(self.axes[0])
        self._panels()
        self.cursors = [ax.axvline(0.0, color=style.INK, lw=1.0, alpha=0.7, zorder=10) for ax in self.axes]
        w = 'w = %g' % loc.weight
        self.fig.text(0.53, 0.965, f'Agent {loc.agent} ({w}): its own observations, beliefs and decisions',
                      fontsize=13, color=style.INK, ha='left', va='center', weight='bold')
        self.fig.text(0.01, 0.965, 'Arena (ground truth)', fontsize=13, color=style.INK, ha='left', va='center',
                      weight='bold')
        self._legend()

    # ---- static time panels -------------------------------------------------------------------------------------
    def _series(self, k, q, near=None):
        """k's rows of quantity q; near: only steps with |d_ik| < near (h = |d|^2 - rho^2, rho = 1)."""
        m = self.R['k'] == k
        if near is not None:
            m &= self.R['h'] < near ** 2 - self.tr.rho ** 2
        return self.R['t'][m], self.R[q][m]

    def _gaps(self, t, y):
        """insert NaN where a contact was absent, so a line does not bridge the gap."""
        if len(t) < 2:
            return t, y
        br = np.flatnonzero(np.diff(t) > 1.5 * self.tr.dt) + 1
        return np.insert(t, br, np.nan), np.insert(y.astype(float), br, np.nan)

    def _panels(self):
        A, R, N = self.axes, self.R, self.loc.n_team
        ls = lambda k: '-' if k < N else (0, (3, 1.5))
        T_end = self.t_end
        # 1. temperature and pressure of the agent
        steps = np.round(R['t'] / self.tr.dt).astype(int)
        u, inv = np.unique(steps, return_inverse=True)
        T = np.bincount(inv, R['lam'] * R['theta'], len(u))
        P = np.bincount(inv, R['lam'] * (R['alpha'] / 2) ** 2, len(u))
        Ti, Pi = np.zeros(self.K), np.zeros(self.K)
        ok = u < self.K
        Ti[u[ok]], Pi[u[ok]] = T[ok], P[ok]
        t = self.tr.t[:self.K]
        A[0].plot(t, Ti, color=style.INK, lw=1.4, label=r'$T_i=\sum_k\lambda_{ik}\theta^\star_{ik}$')
        a2 = A[0].twinx()
        a2.plot(t, Pi, color=style.colour('tan'), lw=1.2, alpha=0.85, label=r'$P_i=\sum_k\lambda_{ik}\|d_{ik}\|^2$')
        a2.set_ylabel(r'$P_i$', color=style.colour('tan')); a2.tick_params(axis='y', colors=style.colour('tan'))
        a2.grid(False); a2.spines['right'].set_visible(True)
        A[0].set_ylabel(r'$T_i$')
        A[0].set_title('1  temperature $T_i$ and pressure $P_i$', loc='left', fontsize=11)
        h1, l1 = A[0].get_legend_handles_labels(); h2, l2 = a2.get_legend_handles_labels()
        A[0].legend(h1 + h2, l1 + l2, loc='upper left', ncol=2, fontsize=9)
        # 2. following mass per neighbour
        for k in self.nbs:
            A[1].plot(*self._gaps(*self._series(k, 'follow', near=self.NEAR)), color=self.col[k], ls=ls(k), lw=1.5)
        A[1].set_ylim(-0.05, 1.05); A[1].set_ylabel(r'$w_{ik}(\mathcal{F})$')
        A[1].set_title(r'2  belief: mass on "$k$ follows", neighbours closer than %g (solid teammate, dashed outsider)'
                       % self.NEAR, loc='left', fontsize=11)
        # 3. prediction vs observation for the most binding neighbour at each step
        X = self._observed()
        best = self._most_binding()
        for (k, sl) in best:
            tk = R['t'][sl]
            c = self.col[k]
            m, sd = R['mX'][sl], np.sqrt(np.maximum(R['vX'][sl], 0))
            A[2].fill_between(tk, m - sd, m + sd, color=c, alpha=0.18, lw=0)
            A[2].plot(tk, m, color=c, lw=1.4)
            A[2].fill_between(tk, R['r'][sl], R['R'][sl], color=style.INK2, alpha=0.10, lw=0)
            A[2].plot(tk, R['R'][sl], color=style.INK, lw=1.2, ls=(0, (4, 2)))
            A[2].plot(tk, X[sl], color=c, lw=0, marker='.', ms=2.5)
        A[2].set_ylabel('usage of $k$')
        A[2].set_title(r'3  most binding neighbour: predicted mean $\pm$ sd (band), bound $R_{ik}$ (dashed), '
                       r'cover $R_{ik}-r_{ik}$ (grey), observed (dots)', loc='left', fontsize=11)
        # 4. fairness state
        A[3].plot(t, self.loc.beta[:self.K], color=style.colour('centred'), lw=1.6, label=r'$\beta_i$')
        A[3].set_yscale('log', base=2); A[3].set_ylim(1 / 9, 9)
        A[3].set_ylabel(r'$\beta_i$')
        a4 = A[3].twinx()
        a4.plot(t, self.loc.W[:self.K], color=style.colour('final'), lw=1.4, label=r'$W_i$')
        a4.plot(t, self.loc.cbar * t, color=style.colour('final'), lw=1.0, ls=(0, (4, 2)), label=r'$\bar c\,t$ (public)')
        a4.set_ylabel(r'$W_i$', color=style.colour('final')); a4.tick_params(axis='y', colors=style.colour('final'))
        a4.grid(False); a4.spines['right'].set_visible(True)
        h1, l1 = A[3].get_legend_handles_labels(); h2, l2 = a4.get_legend_handles_labels()
        A[3].legend(h1 + h2, l1 + l2, loc='upper left', ncol=3, fontsize=9)
        A[3].set_title(r'4  fairness: $\beta_i$ (log scale) and ledger $W_i$ vs $\bar c\,t$', loc='left', fontsize=11)
        # 5. agreement and price per neighbour (neighbours that ever bind)
        a5 = A[4].twinx()
        for k in self.nbs:
            tk, lam = self._series(k, 'lam')
            if not np.any(lam > 0):
                continue
            A[4].plot(*self._gaps(*self._series(k, 'r')), color=self.col[k], ls=ls(k), lw=1.5)
            a5.plot(*self._gaps(tk, lam), color=self.col[k], ls=ls(k), lw=0.9, alpha=0.55)
        A[4].set_ylabel(r'$r_{ik}$'); a5.set_ylabel(r'$\lambda_{ik}$ (thin)'); a5.grid(False); a5.spines['right'].set_visible(True)
        A[4].set_title(r'5  agreement $r_{ik}$ (thick) and price $\lambda_{ik}$ (thin) per neighbour', loc='left', fontsize=11)
        A[4].set_xlabel('t (s)')
        for ax in A:
            ax.set_xlim(0, T_end)
        for ax in A[:-1]:
            plt.setp(ax.get_xticklabels(), visible=False)

    def _observed(self):
        """k's realised usage at each logged step, as i observes it one step later: alpha y_k - kappa h / 2 with
        y_k the approach speed of k toward i from k's next displacement."""
        tr, R = self.tr, self.R
        Pb = np.concatenate([tr.p, tr.q], axis=1) if tr.q.shape[1] else tr.p
        k = np.round(R['t'] / tr.dt).astype(int)
        kk = np.minimum(k + 1, len(tr.p) - 1)
        b = R['k'].astype(int)
        d = Pb[k, self.loc.agent] - Pb[k, b]
        dh = d / np.linalg.norm(d, axis=1, keepdims=True)
        v = (Pb[kk, b] - Pb[k, b]) / tr.dt
        return R['alpha'] * np.sum(dh * v, axis=1) - 0.5 * self.loc.kappa * R['h']

    def _most_binding(self):
        """[(k, index array)] runs of steps where k has the largest lambda_ik > 0 among i's contacts."""
        R = self.R
        steps = np.round(R['t'] / self.tr.dt).astype(int)
        order = np.lexsort((-R['lam'], steps))
        first = np.r_[True, np.diff(steps[order]) != 0]
        top = order[first]
        top = top[R['lam'][top] > 0]
        out, cur, idx = [], None, []
        prev = None
        for j in top:
            k = int(R['k'][j]); s = steps[j]
            if k != cur or (prev is not None and s != prev + 1):
                if idx:
                    out.append((cur, np.array(idx)))
                cur, idx = k, []
            idx.append(j); prev = s
        if idx:
            out.append((cur, np.array(idx)))
        return out

    def _legend(self):
        h = [Line2D([], [], marker='o', ls='', color=style.WEIGHT[1.0], ms=9, label='team, $w=1$'),
             Line2D([], [], marker='o', ls='', color=style.WEIGHT[3.0], ms=9, label='team, $w=3$'),
             Line2D([], [], marker='o', ls='', color=style.OUTSIDER, ms=9, label='outsider'),
             Line2D([], [], marker='o', ls='', mfc='none', mec=style.INK, mew=2.2, ms=13, label=f'agent {self.loc.agent}'),
             Line2D([], [], color=style.INK2, lw=2.5, label=r'link to a neighbour of agent %d (colour = panels, width $\propto\lambda_{ik}$)' % self.loc.agent),
             Line2D([], [], marker='o', ls='', mfc='none', mec=style.VIOL, mew=2, ms=11, label=r'violation $d<0.95\rho$')]
        self.fig.legend(handles=h, loc='lower left', bbox_to_anchor=(0.01, 0.005), ncol=3, fontsize=10)

    # ---- per frame -------------------------------------------------------------------------------------------------
    def draw(self, k):
        tr, i = self.tr, self.loc.agent
        draw_frame(self.ax_s, tr, k, colour='weight', contacts=False, sense_agent=i, clock=True)
        P = tr.bodies(k)
        R = self.R
        m = np.round(R['t'] / tr.dt).astype(int) == k
        segs, cols, lws = [], [], []
        lam_ref = max(np.percentile(R['lam'][R['lam'] > 0], 95), 1e-9) if np.any(R['lam'] > 0) else 1.0
        for b, lam in zip(R['k'][m].astype(int), R['lam'][m]):
            segs.append((P[i], P[b])); cols.append(self.col[b]); lws.append(0.8 + 5.0 * min(lam / lam_ref, 1.2))
        if segs:
            self.ax_s.add_collection(LineCollection(segs, colors=cols, linewidths=lws, alpha=0.85, zorder=3))
        self.ax_s.add_patch(Circle(tr.p[k, i], tr.rho * 0.75, fill=False, ec=style.INK, lw=2.2, zorder=7))
        tk = tr.t[k]
        for c in self.cursors:
            c.set_xdata([tk, tk])
        return []

    def still(self, path, t):
        self.draw(int(round(t / self.tr.dt)))
        self.fig.savefig(f'{path}.png', dpi=self.fig.dpi, bbox_inches=None)

    def animate(self, path, fps=20, bitrate=1400, speed=1.0):
        """mp4 at `speed` x real time (frames every speed/fps s of simulation)."""
        stride = max(1, int(round(speed / (fps * self.tr.dt))))
        frames = list(range(0, self.K, stride))
        anim = FuncAnimation(self.fig, self.draw, frames=frames, blit=False)
        anim.save(f'{path}.mp4', writer=FFMpegWriter(fps=fps, bitrate=bitrate, codec='libx264',
                                                     extra_args=['-pix_fmt', 'yuv420p', '-preset', 'slow']),
                  dpi=self.fig.dpi)


# ---- comparison with Tan -------------------------------------------------------------------------------------------
# Tan (solvers/tan.py) has no beliefs: teammates are identified and exchange multipliers; outsiders are identified and
# covered at their capability. Its per-row quantities are mapped onto the LocalLog fields:
#   lam     c_i^m, i's QP multiplier of the row (team or outsider)
#   lam_nb  c_k^m, the multiplier teammate k communicates for the same pair (NaN for outsiders)
#   R       the room i leaves to k: y_i^m - y_k^m for a teammate, alpha v_env - kappa h / 2 (capability) for an outsider
#   r       y_i^m - y_k^m for a teammate (NaN for outsiders); theta, follow, mX, vX are NaN (no counterpart)


def extract_tan(log, agent, v_env, kappa):
    """Agent `agent`'s rows from a Tan run (info['mu'], info['r']) in the LocalLog layout; beta is 1, W from the log."""
    tracks = np.asarray(log.meta['tracks'])
    body = np.empty_like(tracks); body[tracks] = np.arange(len(tracks))
    N = log.x.shape[1]
    me = int(tracks[agent])
    rows = []
    for k, (t, inf) in enumerate(zip(log.t, log.info)):
        P = np.concatenate([log.x[k, :, :2], log.ext_x[k, :, :2]]) if log.ext_x.shape[1] else log.x[k, :, :2]
        for (i, tr), lam in inf['mu'].items():
            if i != agent:
                continue
            b = int(body[tr])
            d = np.linalg.norm(P[agent] - P[b])
            alpha, h = 2.0 * d, d * d - log.rho ** 2
            team = b < N
            y = inf['r'].get((agent, tr), np.nan) if team else np.nan
            rows.append(dict(t=t, k=b, lam=lam, lam_nb=inf['mu'].get((b, me), np.nan) if team else np.nan,
                             R=y if team else alpha * v_env - 0.5 * kappa * h, r=y, alpha=alpha, h=h,
                             theta=np.nan, follow=np.nan, mX=np.nan, vX=np.nan))
    arr = {q: np.array([r[q] for r in rows], float) for q in FIELDS + ('lam_nb',)}
    f = 0.5 * log.weights[agent] * np.sum((log.u[:, agent] - log.u_nom[:, agent]) ** 2, axis=1) * log.dt
    return LocalLog(agent, float(log.weights[agent]), np.nan, kappa, np.asarray(log.t, float), np.ones(len(log.t)),
                    np.cumsum(f), arr, N)


def _gaps(t, y, dt):
    """NaN where a contact was absent, so a line does not bridge the gap."""
    if len(t) < 2:
        return t, y
    br = np.flatnonzero(np.diff(t) > 1.5 * dt) + 1
    return np.insert(t, br, np.nan), np.insert(np.asarray(y, float), br, np.nan)


class CompareView:
    """Two runs of the same cell and seed (ours, Tan), same agent: two scenes (left) and six time panels (right)."""
    NEAR = 3.0

    def __init__(self, runs, t_end=None, figsize=(19.2, 10.8), dpi=100, note=None):
        """runs: [(label, style key, Trajectory, LocalLog)], ours first, Tan second; note: a footnote line under the
        legend (e.g. what a dagger in a label means)."""
        style.use()
        self.runs = runs
        tr0 = runs[0][2]
        self.dt = tr0.dt
        self.K = min(min(len(r[2].p) for r in runs), len(tr0.p) if t_end is None else int(round(t_end / tr0.dt)))
        self.t = tr0.t[:self.K]
        self.t_end = self.t[-1]
        self.agent, self.N = runs[0][3].agent, runs[0][3].n_team
        self.has_out = any(r[2].q.shape[1] for r in runs)    # without outsiders the outsider parts are left out
        self.R = []
        for _, _, _, loc in runs:
            keep = loc.rows['t'] <= self.t_end + 1e-9
            self.R.append({q: v[keep] for q, v in loc.rows.items()})
        self.col = lambda b: NB[(b - 1) % len(NB)] if b < self.N else style.OUTSIDER
        self._violations()
        self.fig = plt.figure(figsize=figsize, dpi=dpi)
        gs = GridSpec(6, 2, figure=self.fig, width_ratios=[0.62, 1.38], left=0.005, right=0.955, top=0.94, bottom=0.1,
                      wspace=0.1, hspace=0.55)
        gl = gs[:, 0].subgridspec(2, 1, hspace=0.08)
        self.ax_s = [self.fig.add_subplot(gl[j]) for j in range(2)]
        self.axes = [self.fig.add_subplot(gs[j, 1]) for j in range(6)]
        for ax in self.axes[1:]:
            ax.sharex(self.axes[0])
        self._panels()
        self.cursors = [ax.axvline(0.0, color=style.INK, lw=1.0, alpha=0.7, zorder=10) for ax in self.axes]
        self.fig.text(0.40, 0.972, f'Agent {self.agent} (w = {runs[0][3].weight:g}) under each method: what the method '
                      'itself uses', fontsize=13, weight='bold', color=style.INK, va='center')
        self.fig.text(0.005, 0.972, 'Arena (ground truth), same start', fontsize=13, weight='bold', color=style.INK,
                      va='center')
        self._legend()
        if note:
            self.fig.text(0.995, 0.004, note, fontsize=9.5, color=style.INK2, ha='right', va='bottom')

    def _violations(self):
        """cumulative count of steps with some team pair / some team-outsider pair closer than 0.95 rho."""
        self.vcount = []
        for _, _, tr, _ in self.runs:
            vt, vo = np.zeros(self.K, int), np.zeros(self.K, int)
            for k in range(self.K):
                v = tr.violations(k)
                vt[k] = any(c < self.N for _, c in v)
                vo[k] = any(c >= self.N for _, c in v)
            self.vcount.append((np.cumsum(vt), np.cumsum(vo)))

    def _dist(self, tr):
        P = tr.p[:self.K]
        d_team = np.linalg.norm(P[:, [self.agent]] - P, axis=2)
        d_team[:, self.agent] = np.inf
        d_out = np.linalg.norm(P[:, [self.agent]] - tr.q[:self.K], axis=2) if tr.q.shape[1] else np.full((self.K, 1), np.inf)
        return d_team.min(1), d_out.min(1)

    def _binding(self, R):
        """per step, the row with the largest multiplier > 0 -> index array into R."""
        st = np.round(R['t'] / self.dt).astype(int)
        order = np.lexsort((-R['lam'], st))
        top = order[np.r_[True, np.diff(st[order]) != 0]]
        return top[R['lam'][top] > 0]

    def _panels(self):
        A, t = self.axes, self.t
        (lo, so, tro, _), (lt, st_, trt, _) = self.runs
        Ro, Rt = self.R
        co, ct = style.colour(so), style.colour(st_)
        # 1. distances
        for (lab, sk, tr, _) in self.runs:
            dt_, do = self._dist(tr)
            A[0].plot(t, dt_, color=style.colour(sk), lw=1.3)
            if self.has_out:
                A[0].plot(t, do, color=style.colour(sk), lw=1.1, ls=(0, (3, 1.5)))
        A[0].axhline(tro.rho, color=style.INK2, lw=0.9)
        A[0].axhline(0.95 * tro.rho, color=style.VIOL, lw=1.0, ls=(0, (2, 2)))
        A[0].set_ylim(0.6, 3.5); A[0].set_ylabel('distance')
        A[0].set_title((r'1  distance from agent %d to nearest teammate (solid) and outsider (dashed); ' if self.has_out
                        else r'1  distance from agent %d to its nearest teammate; ') % self.agent
                       + r'$\rho$ grey, $0.95\rho$ red', loc='left', fontsize=11)
        # 2a. ours: following mass per neighbour (from own observations)
        for b in np.unique(Ro['k']).astype(int):
            m = (Ro['k'] == b) & (Ro['h'] < self.NEAR ** 2 - tro.rho ** 2)
            A[1].plot(*_gaps(Ro['t'][m], Ro['follow'][m], self.dt), color=self.col(b), lw=1.3,
                      ls='-' if b < self.N else (0, (3, 1.5)))
        A[1].set_ylim(-0.05, 1.05); A[1].set_ylabel(r'$w_{ik}(\mathcal{F})$')
        A[1].set_title(r'2a  %s: belief "$k$ follows", from own observations (neighbours closer than %g%s)'
                       % (lo, self.NEAR, '; dashed grey = outsiders' if self.has_out else ''), loc='left', fontsize=11)
        # 2b. Tan: multiplier communicated by each teammate; outsiders identified by assumption
        for b in np.unique(Rt['k']).astype(int):
            if b >= self.N:
                continue
            m = (Rt['k'] == b) & (Rt['h'] < self.NEAR ** 2 - trt.rho ** 2)
            A[2].plot(*_gaps(Rt['t'][m], Rt['lam_nb'][m], self.dt), color=self.col(b), lw=1.3)
        A[2].set_yscale('symlog', linthresh=0.1); A[2].set_ylabel(r'$c_k^m$ received')
        if self.has_out:
            self._outsider_count(A[2], Rt, t)
        A[2].set_title(r'2b  %s: multiplier each teammate communicates (it is told, not inferred)' % lt
                       + ('; grey = outsiders identified by assumption, covered at capability' if self.has_out else ''),
                       loc='left', fontsize=11)
        self._rest(A, t, Ro, Rt, lo, lt, co, ct)

    def _outsider_count(self, ax, Rt, t):
        a2 = ax.twinx()
        st2 = np.round(Rt['t'] / self.dt).astype(int)
        n_out = np.bincount(st2[Rt['k'] >= self.N], minlength=self.K)[:self.K]
        a2.fill_between(t, 0, n_out, step='post', color=style.OUTSIDER, alpha=0.25, lw=0)
        a2.set_ylabel('outsiders\nin range', color=style.INK2); a2.grid(False); a2.spines['right'].set_visible(True)
        a2.set_ylim(0, max(4, n_out.max() + 1))

    def _rest(self, A, t, Ro, Rt, lo, lt, co, ct):
        # 3. room against the most binding neighbour
        for R, c, lab in ((Ro, co, lo), (Rt, ct, lt)):
            idx = self._binding(R)
            tt = R['t'][idx]
            A[3].plot(*_gaps(tt, R['R'][idx], self.dt), color=c, lw=1.4)
            if R is Ro:
                A[3].plot(*_gaps(tt, R['r'][idx], self.dt), color=c, lw=1.0, ls=(0, (4, 2)))
        A[3].set_ylabel('usage of $k$')
        A[3].set_title(r'3  room left to the most binding neighbour: %s bound $R_{ik}$ (solid) and agreement $r_{ik}$ '
                       r'(dashed); %s $y_i-y_k$' % (lo, lt) + (' (teammate) or capability (outsider)' if self.has_out else ''),
                       loc='left', fontsize=11)
        # 4. prices
        for R, c in ((Ro, co), (Rt, ct)):
            st4 = np.round(R['t'] / self.dt).astype(int)
            mx = np.zeros(self.K)
            np.maximum.at(mx, np.minimum(st4, self.K - 1), np.where(np.isfinite(R['lam']), R['lam'], 0.0))
            A[4].plot(t, mx, color=c, lw=1.2)
        A[4].set_yscale('symlog', linthresh=0.1); A[4].set_ylabel('multiplier')
        A[4].set_title(r'4  largest multiplier among the rows of agent %d: %s $\lambda_{ik}$, %s $c_i^m$' % (self.agent, lo, lt),
                       loc='left', fontsize=11)
        # 5. fairness
        for (lab, sk, tr, loc) in self.runs:
            A[5].plot(t, loc.W[:self.K], color=style.colour(sk), lw=1.5)
            A[5].plot(t, np.ptp(tr.W[:self.K], axis=1), color=style.colour(sk), lw=1.1, ls=(0, (3, 1.5)))
        A[5].set_ylabel('W'); A[5].set_xlabel('t (s)')
        A[5].set_title(r'5  accumulated cost $W_%d$ of agent %d (solid) and fleet range $\max_i W_i-\min_i W_i$ (dashed)'
                       % (self.agent, self.agent), loc='left', fontsize=11)
        for ax in A:
            ax.set_xlim(0, self.t_end)
        for ax in A[:-1]:
            plt.setp(ax.get_xticklabels(), visible=False)

    def _legend(self):
        h = [Line2D([], [], color=style.colour(sk), lw=2.5, label=lab) for lab, sk, _, _ in self.runs]
        h += [Line2D([], [], marker='o', ls='', color=style.WEIGHT[1.0], ms=9, label='team, $w=1$'),
              Line2D([], [], marker='o', ls='', color=style.WEIGHT[3.0], ms=9, label='team, $w=3$'),
              Line2D([], [], marker='o', ls='', mfc='none', mec=style.INK, mew=2.2, ms=12, label=f'agent {self.agent}'),
              Line2D([], [], marker='o', ls='', mfc='none', mec=style.VIOL, mew=2, ms=11, label=r'$d<0.95\rho$'),
              Line2D([], [], color=NB[0], lw=2.5, label='link / line colour = neighbour')]
        if self.has_out:
            h.insert(4, Line2D([], [], marker='o', ls='', color=style.OUTSIDER, ms=9, label='outsider'))
        self.fig.legend(handles=h, loc='lower left', bbox_to_anchor=(0.005, 0.018), ncol=len(h), fontsize=10)

    def draw(self, k):
        for j, (ax, (lab, sk, tr, _), R) in enumerate(zip(self.ax_s, self.runs, self.R)):
            draw_frame(ax, tr, k, colour='weight', contacts=False, sense_agent=self.agent, clock=(j == 0), targets=False)
            P = tr.bodies(k)
            m = np.round(R['t'] / self.dt).astype(int) == k
            lam = np.where(np.isfinite(R['lam'][m]), R['lam'][m], 0.0)
            ref = max(np.percentile(R['lam'][R['lam'] > 0], 95), 1e-9) if np.any(R['lam'] > 0) else 1.0
            segs = [(P[self.agent], P[int(b)]) for b in R['k'][m]]
            if segs:
                ax.add_collection(LineCollection(segs, colors=[self.col(int(b)) for b in R['k'][m]],
                                                 linewidths=0.6 + 4.5 * np.minimum(lam / ref, 1.2), alpha=0.85, zorder=3))
            ax.add_patch(Circle(tr.p[k, self.agent], tr.rho * 0.75, fill=False, ec=style.INK, lw=2.2, zorder=7))
            vt, vo = self.vcount[j]
            ax.text(0.02, 0.02, lab, transform=ax.transAxes, fontsize=11, weight='bold', color=style.colour(sk), va='bottom')
            txt = f'team {vt[k]}  outsider {vo[k]}' if self.has_out else f'team {vt[k]}'
            ax.text(0.98, 0.02, f'violation steps\n{txt}', transform=ax.transAxes, fontsize=9.5,
                    ha='right', va='bottom', color=style.VIOL if vt[k] + vo[k] else style.INK2, family='monospace')
        for c in self.cursors:
            c.set_xdata([self.t[k], self.t[k]])
        return []

    def still(self, path, t):
        self.draw(min(int(round(t / self.dt)), self.K - 1))
        self.fig.savefig(f'{path}.png', dpi=self.fig.dpi, bbox_inches=None)

    def animate(self, path, fps=20, bitrate=1400, speed=1.0):
        stride = max(1, int(round(speed / (fps * self.dt))))
        anim = FuncAnimation(self.fig, self.draw, frames=list(range(0, self.K, stride)), blit=False)
        anim.save(f'{path}.mp4', writer=FFMpegWriter(fps=fps, bitrate=bitrate, codec='libx264',
                                                     extra_args=['-pix_fmt', 'yuv420p', '-preset', 'slow']),
                  dpi=self.fig.dpi)
