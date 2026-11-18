"""Result figures from the stored runs (no new simulation except the trajectories passed in).

  safety(grid_rows, path)        time in violation toward externals and among agents, S2-S4, per method (mean ± s.e.)
  tradeoff(grid_rows, path)      cost vs time in violation toward externals, S3 and S4 (Ours over eps; baselines)
  range_vs_time(hz_rows, path)   max_i W_i - min_i W_i against t, final vs centred beta, S1 and S4 (mean ± s.e. band)
  cv_bars(hz_rows, path)         W std/mean at 120 s, Ours (final, centred beta) and baselines, S1 and S4
  work_curves(trs, path)         W_i(t) per agent for one seed, final vs centred beta
Grid rows: results/final_mutual/grid.jsonl. Horizon rows: results/beta_horizon.jsonl.
"""
from collections import defaultdict

import numpy as np
import matplotlib.pyplot as plt

from . import style

BASE = ('oracle', 'tan', 'pcca', 'risk_ratio', 'reciprocal')
OURS = 'ours_eps0.1_mutual'


def _ms(v):
    v = np.array([x for x in v if x is not None and np.isfinite(x)], float)
    return (v.mean(), v.std(ddof=1) / np.sqrt(len(v))) if len(v) > 1 else (np.nan, np.nan)


def _by(rows, *keys):
    g = defaultdict(list)
    for r in rows:
        g[tuple(r[k] for k in keys)].append(r)
    return g


def safety(rows, path, scenarios=('S2', 'S3', 'S4')):
    style.use()
    g = _by(rows, 'scenario', 'solver')
    methods = [(b, b) for b in BASE] + [(OURS, 'final')]
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.4), sharey=True)
    w = 0.8 / len(methods)
    for ax, (q, ttl) in zip(axes, (('viol_ext', 'toward outsiders'), ('viol_team', 'among team agents'))):
        for j, (key, sty) in enumerate(methods):
            xs = np.arange(len(scenarios)) + (j - (len(methods) - 1) / 2) * w
            m, s = zip(*[_ms([100 * r[q] for r in g[(sc, key)]]) for sc in scenarios])
            ax.bar(xs, m, w * 0.9, yerr=s, color=style.colour(sty), label=style.label(sty),
                   error_kw=dict(lw=0.8, capsize=2, ecolor=style.INK2))
            for x, v in zip(xs, m):
                if v == 0:
                    ax.text(x, 0.004, '0', ha='center', va='bottom', fontsize=7, color=style.colour(sty))
        ax.set_xticks(range(len(scenarios)), scenarios)
        ax.set_yscale('symlog', linthresh=0.1)
        ax.set_ylim(0, 100)
        ax.set_title(f'time in violation, {ttl}')
        ax.grid(axis='x', visible=False)
    axes[0].set_ylabel(r'% of time with $d<0.95\rho$')
    axes[1].legend(ncol=2, loc='upper left')
    fig.text(0.5, -0.04, r'Ours: $\varepsilon=0.1$. Mean ± s.e. over 6 seeds × 120 s; symlog axis (linear below 0.1%).',
             ha='center', fontsize=8, color=style.INK2)
    fig.tight_layout()
    style.save(fig, path)
    plt.close(fig)


def tradeoff(rows, path, scenarios=('S3', 'S4'), centred=None, ncols=None):
    """centred: solver key prefix of the centred-beta rows to add as one point (None: not shown)."""
    style.use()
    g = _by(rows, 'scenario', 'solver')
    ncols = ncols or len(scenarios)
    nrows = -(-len(scenarios) // ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.5 * ncols, 3.6 * nrows), squeeze=False)
    axes = axes.ravel()
    for ax, sc in zip(axes, scenarios):
        if centred:
            rr = [r for r in rows if r['scenario'] == sc and r['solver'].startswith(centred)]
            (cx, sx), (cy, sy) = _ms([r['cost'] for r in rr]), _ms([100 * r['viol_ext'] for r in rr])
            ax.errorbar([cx], [cy], xerr=[sx], yerr=[sy], fmt='D', ms=7, color=style.colour('centred'), capsize=2,
                        elinewidth=0.8, label=style.label('centred') + r' ($\varepsilon$ = 0.1)', zorder=4)
        pts = []
        for e in ('0.1', '0.2', '0.3'):
            rr = g[(sc, f'ours_eps{e}_mutual')]
            (cx, sx), (cy, sy) = _ms([r['cost'] for r in rr]), _ms([100 * r['viol_ext'] for r in rr])
            pts.append((cx, sx, cy, sy, e))
        x, sx, y, sy, e = zip(*pts)
        ax.errorbar(x, y, xerr=sx, yerr=sy, color=style.colour('final'), marker='o', ms=7, capsize=2, elinewidth=0.8,
                    label=r'Ours ($\varepsilon$ = 0.1, 0.2, 0.3)', zorder=3)
        for xi, yi, ei in zip(x, y, e):
            ax.annotate(rf'$\varepsilon$={ei}', (xi, yi), fontsize=8, textcoords='offset points', color=style.INK2,
                        xytext={'0.1': (-30, -13), '0.2': (2, 7), '0.3': (4, -13)}[ei])
        for key in BASE:
            rr = g[(sc, key)]
            (cx, sx), (cy, sy) = _ms([r['cost'] for r in rr]), _ms([100 * r['viol_ext'] for r in rr])
            ax.errorbar([cx], [cy], xerr=[sx], yerr=[sy], fmt='s', ms=7, color=style.colour(key), capsize=2,
                        elinewidth=0.8, label=style.label(key), zorder=3)
        ax.set_yscale('symlog', linthresh=0.1)
        ax.set_ylim(-0.06, 100)
        ax.set_xlabel('cost (mean per agent)')
        ax.set_ylabel('time in violation toward outsiders (%)')
        ax.set_title(sc)
    axes[-1].legend(loc='upper right', fontsize=8)
    fig.tight_layout()
    style.save(fig, path)
    plt.close(fig)


def range_vs_time(rows, path, scenarios=('S1', 'S4'), confs=(('final', 'final'), ('centred 0.25x', 'centred')), ncols=None):
    style.use()
    g = _by(rows, 'scenario', 'conf')
    ncols = ncols or len(scenarios)
    nrows = -(-len(scenarios) // ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.5 * ncols, 3.2 * nrows + 0.2), squeeze=False)
    axes = axes.ravel()
    for ax, sc in zip(axes, scenarios):
        for conf, sty in confs:
            rr = g[(sc, conf)]
            ts = sorted(int(t) for t in rr[0]['at'])
            v = np.array([[r['at'][str(t)].get('range', r['at'][str(t)].get('W_range')) for t in ts] for r in rr])
            m, s = v.mean(0), v.std(0, ddof=1) / np.sqrt(len(v))
            ax.plot(ts, m, color=style.colour(sty), marker='o', ms=4, label=style.label(sty))
            ax.fill_between(ts, m - s, m + s, color=style.colour(sty), alpha=0.18, lw=0)
        ax.set_xlabel('t (s)')
        ax.set_ylabel(r'$\max_i W_i - \min_i W_i$')
        ax.set_title(sc)
        ax.set_xlim(0, 600)
        ax.set_ylim(bottom=0)
    axes[0].legend(loc='upper left')
    fig.text(0.5, -0.03, r'Centred $\beta$: $W_0=4.22$, $\beta_{\max}=8$. Mean ± s.e. over 12 seeds (band).',
             ha='center', fontsize=8, color=style.INK2)
    fig.tight_layout()
    style.save(fig, path)
    plt.close(fig)


def cv_bars(rows, path, scenarios=('S1', 'S4'), t='120'):
    style.use()
    g = _by(rows, 'scenario', 'conf')
    confs = [('oracle', 'oracle'), ('tan', 'tan'), ('pcca', 'pcca'), ('final', 'final'), ('centred 0.25x', 'centred')]
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    w = 0.8 / len(confs)
    for j, (conf, sty) in enumerate(confs):
        xs = np.arange(len(scenarios)) + (j - (len(confs) - 1) / 2) * w
        m, s = zip(*[_ms([r['at'][t]['cv'] for r in g[(sc, conf)]]) for sc in scenarios])
        n = len(g[(scenarios[0], conf)])
        ax.bar(xs, m, w * 0.9, yerr=s, color=style.colour(sty), label=f'{style.label(sty)} (n={n})',
               error_kw=dict(lw=0.8, capsize=2, ecolor=style.INK2))
    ax.set_xticks(range(len(scenarios)), scenarios)
    ax.grid(axis='x', visible=False)
    ax.set_ylabel(r'$W$ std / mean at $t=120$ s')
    ax.legend(loc='upper right', fontsize=8)
    fig.text(0.5, -0.03, 'Lower = work spread more evenly over agents. Mean ± s.e. over seeds (n per method).',
             ha='center', fontsize=8, color=style.INK2)
    fig.tight_layout()
    style.save(fig, path)
    plt.close(fig)


def work_curves(pairs, path):
    """pairs: [(scenario, traj_final, traj_centred), ...] -> one row per scenario, two panels sharing y."""
    style.use()
    fig, axes = plt.subplots(len(pairs), 2, figsize=(9.0, 3.0 * len(pairs)), sharex=True, squeeze=False)
    for row, (sc, tf, tc) in zip(axes, pairs):
        top = max(tf.W.max(), tc.W.max()) * 1.05
        for ax, tr, sty in zip(row, (tf, tc), ('final', 'centred')):
            t = tr.t
            sub = slice(None, None, 25)
            for i in range(tr.W.shape[1]):
                ax.plot(t[sub], tr.W[sub, i], color=style.colour(sty), lw=1.2, alpha=0.75)
            ax.plot(t[sub], tr.W[sub].mean(1), color=style.INK, lw=1.4, ls='--', label='fleet mean')
            ax.set_ylim(0, top)
            ax.set_xlim(0, t[-1])
            ax.set_title(f'{sc}: {style.label(sty)}  (range at end {tr.W[-1].max() - tr.W[-1].min():.1f})')
            ax.set_ylabel(r'$W_i(t)$')
        row[0].legend(loc='upper left')
    for ax in axes[-1]:
        ax.set_xlabel('t (s)')
    fig.text(0.5, -0.01, f'One line per agent, seed {pairs[0][1].seed}.', ha='center', fontsize=8, color=style.INK2)
    fig.tight_layout()
    style.save(fig, path)
    plt.close(fig)
