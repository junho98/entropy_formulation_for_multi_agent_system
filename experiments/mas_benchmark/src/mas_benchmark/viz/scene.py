"""Arena drawings: one frame of a Trajectory, the scenario overview, and side-by-side animations.

Bodies are disks of radius rho/2, so two disks overlap exactly when the pair is closer than rho.
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FFMpegWriter, FuncAnimation, PillowWriter
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from matplotlib.colors import Normalize
from matplotlib.patches import Circle

from . import style


def _frame_axes(ax, tr):
    ax.cla()
    ax.set_aspect('equal')
    ax.set_xlim(-tr.arena_radius - 0.6, tr.arena_radius + 0.6)
    ax.set_ylim(-tr.arena_radius - 0.6, tr.arena_radius + 0.6)
    ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.add_patch(Circle((0, 0), tr.arena_radius, fill=False, ec=style.INK2, lw=0.8))
    ax.add_patch(Circle((0, 0), tr.circle_radius, fill=False, ec=style.GRID, lw=0.8, ls='--'))


def draw_frame(ax, tr, k, colour='weight', norm=None, trail=3.0, contacts=True, lam_ref=None, sense_agent=None,
               targets=True, clock=True):
    """Draw step k of tr on ax. colour: 'weight' (team by w_i) or 'work' (team by W_i(t) under norm)."""
    _frame_axes(ax, tr)
    N, E = tr.p.shape[1], tr.q.shape[1]
    r = tr.rho / 2
    k0 = max(0, k - int(round(trail / tr.dt)))
    P = tr.bodies(k)
    if colour == 'work':
        norm = norm or Normalize(0, max(tr.W[k].max(), 1e-9))
        cols = [style.WORK(norm(w)) for w in tr.W[k]]
    else:
        cols = [style.WEIGHT.get(float(w), style.colour('final')) for w in tr.weights]
    # trails
    for e in range(E):
        ax.plot(tr.q[k0:k + 1, e, 0], tr.q[k0:k + 1, e, 1], color=style.OUTSIDER, lw=1.0, alpha=0.5, solid_capstyle='round')
    for i in range(N):
        ax.plot(tr.p[k0:k + 1, i, 0], tr.p[k0:k + 1, i, 1], color=cols[i], lw=1.4, alpha=0.6, solid_capstyle='round')
    if targets:
        ax.scatter(tr.targets[k, :, 0], tr.targets[k, :, 1], marker='x', s=28, c=cols, lw=1.4, zorder=3)
    if sense_agent is not None:
        ax.add_patch(Circle(P[sense_agent], tr.sensing, fill=False, ec=cols[sense_agent], lw=1.0, ls=(0, (4, 3))))
    # active contacts, width proportional to lambda_ik
    if contacts and len(tr.lam):
        rows = tr.lam[tr.lam[:, 0] == k]
        if len(rows):
            lam_ref = lam_ref or np.percentile(tr.lam[:, 3], 95)
            segs = [(P[int(i)], P[int(b)]) for _, i, b, _ in rows]
            lw = np.clip(4.0 * rows[:, 3] / lam_ref, 0.3, 6.0)
            ax.add_collection(LineCollection(segs, linewidths=lw, colors=style.INK2, alpha=0.55, zorder=2))
    for e in range(E):
        ax.add_patch(Circle(tr.q[k, e], r, fc=style.OUTSIDER, ec='white', lw=0.8, zorder=4))
    for i in range(N):
        ax.add_patch(Circle(tr.p[k, i], r, fc=cols[i], ec='white', lw=0.8, zorder=5))
    # violations (d < 0.95 rho)
    for i, b in tr.violations(k):
        for c in (P[i], P[b]):
            ax.add_patch(Circle(c, r * 1.25, fill=False, ec=style.VIOL, lw=2.0, zorder=6))
        ax.plot(*zip(P[i], P[b]), color=style.VIOL, lw=2.0, zorder=6)
    if clock:
        ax.text(0.02, 0.98, f't = {tr.t[k]:5.1f} s', transform=ax.transAxes, va='top', fontsize=9, color=style.INK2,
                family='monospace')


def overview(trs, k, path, names=None):
    """One panel per trajectory (scenario), snapshot at step k, with the sensing range of agent 0."""
    style.use()
    fig, axes = plt.subplots(1, len(trs), figsize=(3.2 * len(trs), 3.6))
    for ax, tr, nm in zip(np.atleast_1d(axes), trs, names or [tr.scenario for tr in trs]):
        draw_frame(ax, tr, k, colour='weight', contacts=False, sense_agent=0, clock=False)
        ax.set_title(nm, fontsize=10)
    tr = trs[0]
    handles = [Line2D([], [], marker='o', ls='', color=style.WEIGHT[1.0], ms=8, label='team, $w=1$'),
               Line2D([], [], marker='o', ls='', color=style.WEIGHT[3.0], ms=8, label='team, $w=3$'),
               Line2D([], [], marker='o', ls='', color=style.OUTSIDER, ms=8, label='outsider'),
               Line2D([], [], marker='x', ls='', color=style.INK2, ms=7, label='target'),
               Line2D([], [], ls=(0, (4, 3)), color=style.WEIGHT[1.0], label='sensing range (agent 0)')]
    fig.legend(handles=handles, loc='lower center', ncol=5, bbox_to_anchor=(0.5, -0.02), fontsize=9,
               title=fr'disk diameter = safety radius $\rho$ = {tr.rho:g};  trails: last 3 s', title_fontsize=8)
    fig.subplots_adjust(bottom=0.2, wspace=0.05)
    style.save(fig, path)
    plt.close(fig)


def animate(trs, names, path, t_end=None, fps=25, colour='work', contacts=True, gif_stride=4, gif_width=None):
    """Side-by-side animation of trajectories (same seed, same scenario) -> path.mp4 and path.gif (subsampled).

    colour='work' colours team agents by W_i(t) on one scale shared by all panels (0 .. max W_i at t_end)."""
    style.use()
    n = len(trs)
    K = min(len(tr.p) for tr in trs)
    if t_end is not None:
        K = min(K, int(round(t_end / trs[0].dt)))
    stride = max(1, int(round(1.0 / (fps * trs[0].dt))))
    frames = list(range(0, K, stride))
    norm = Normalize(0, max(tr.W[K - 1].max() for tr in trs))
    lam_ref = max((np.percentile(tr.lam[:, 3], 95) for tr in trs if len(tr.lam)), default=None)
    fig, axes = plt.subplots(1, n, figsize=(3.6 * n + (0.7 if colour == 'work' else 0), 4.2))
    axes = np.atleast_1d(axes)
    if colour == 'work':
        fig.subplots_adjust(left=0.01, right=0.88, bottom=0.12, top=0.92, wspace=0.04)
        cax = fig.add_axes((0.9, 0.2, 0.015, 0.62))
        cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=style.WORK), cax=cax)
        cb.set_label(r'accumulated work $W_i(t)$')
    else:
        fig.subplots_adjust(left=0.01, right=0.99, bottom=0.12, top=0.92, wspace=0.04)
    handles = [Line2D([], [], marker='o', ls='', color=style.OUTSIDER, ms=7, label='outsider'),
               Line2D([], [], marker='o', ls='', mfc='none', mec=style.VIOL, mew=2, ms=9,
                          label=r'violation ($d<0.95\rho$)')]
    if contacts:
        handles.append(Line2D([], [], color=style.INK2, lw=2, alpha=0.6, label=r'contact, width $\propto\lambda_{ik}$'))
    if colour != 'work':
        handles.insert(0, Line2D([], [], marker='o', ls='', color=style.WEIGHT[1.0], ms=7, label='team'))
    fig.legend(handles=handles, loc='lower center', ncol=len(handles), fontsize=8)

    def update(k):
        for ax, tr, nm in zip(axes, trs, names):
            draw_frame(ax, tr, k, colour=colour, norm=norm, contacts=contacts, lam_ref=lam_ref)
            nv = len(tr.violations(k))
            ax.set_title(nm, fontsize=10, color=style.INK)
            ax.text(0.98, 0.98, f'{nv} violating pair' + ('s' if nv != 1 else '') if nv else '', transform=ax.transAxes,
                    ha='right', va='top', fontsize=9, color=style.VIOL)
        return []

    anim = FuncAnimation(fig, update, frames=frames, blit=False)
    anim.save(f'{path}.mp4', writer=FFMpegWriter(fps=fps, bitrate=2400, codec='libx264',
                                                 extra_args=['-pix_fmt', 'yuv420p']), dpi=140)
    anim_gif = FuncAnimation(fig, update, frames=frames[::gif_stride], blit=False)
    anim_gif.save(f'{path}.gif', writer=PillowWriter(fps=max(1, fps // gif_stride)), dpi=gif_width or 60)
    plt.close(fig)
