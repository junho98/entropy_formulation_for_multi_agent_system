"""Readability of the costate: hard wall vs layer (slide 14).

    python figures/plot_readability.py   -> public/images/readability_wall_vs_layer.png

Costate lambda = -Psi'(s) as a function of the slack s.
Hard wall: 0 for s > 0, the whole ray [0, inf) at s = 0 (complementary slackness), so an
observed slack s = 0 does not fix lambda.  Layer: Psi(s) = k_e/2 (eps - s)_+^2 + M(-s)_+,
lambda = k_e (eps - s)_+ on s >= 0, one value per observed slack.
"""
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

INK, MUTED, MARK = '#1f2937', '#6b7280', '#2b3448'
KE, EPS = 20.0, 0.1
OUT = os.path.join(os.path.dirname(__file__), '..', 'public', 'images', 'readability_wall_vs_layer.png')

plt.rcParams.update({'font.size': 19, 'axes.edgecolor': MUTED, 'axes.labelcolor': INK,
                     'xtick.color': MUTED, 'ytick.color': MUTED, 'mathtext.fontset': 'cm'})
fig, axes = plt.subplots(2, 1, figsize=(4.8, 6.2), sharex=True)
ymax = KE * EPS * 1.6

# hard wall
ax = axes[0]
ax.plot([0, 0.14], [0, 0], color=MARK, lw=2.5, solid_capstyle='round')
ax.plot([0, 0], [0, ymax], color=MARK, lw=2.5, solid_capstyle='round')
ax.annotate('', xy=(0, ymax * 1.02), xytext=(0, ymax * 0.9),
            arrowprops=dict(arrowstyle='->', color=MARK, lw=2.5))
ax.text(0.02, ymax * 0.62, r'$s=0$:' '\n' r'$\lambda\in[0,\infty)$', color=INK, fontsize=18)
ax.set_title('hard wall', color=INK, fontsize=20)

# layer
ax = axes[1]
s = np.linspace(0, 0.14, 200)
ax.plot(s, KE * np.maximum(EPS - s, 0), color=MARK, lw=2.5)
s0 = 0.04
l0 = KE * (EPS - s0)
ax.plot([s0, s0], [0, l0], color=MUTED, lw=1.2, ls='--')
ax.plot([-0.02, s0], [l0, l0], color=MUTED, lw=1.2, ls='--')
ax.plot([s0], [l0], 'o', color=MARK, ms=8, mec='white', mew=2)
ax.text(s0 + 0.008, l0 + 0.15, r'one $\lambda$ per $s$', color=INK, fontsize=18)
ax.axvspan(0, EPS, color=MARK, alpha=0.07, lw=0)
ax.text(EPS / 2, ymax * 0.85, r'$(0,\epsilon)$', ha='center', color=MUTED, fontsize=18)
ax.set_title('layer', color=INK, fontsize=20)

for ax in axes:
    ax.set_xlim(-0.015, 0.14)
    ax.set_ylim(-0.1, ymax * 1.05)
    ax.set_xticks([0, EPS])
    ax.set_xticklabels(['0', r'$\epsilon$'])
    ax.set_yticks([0])
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
axes[1].set_xlabel('slack $s$')
for ax in axes:
    ax.set_ylabel(r"$\lambda=-\Psi'(s)$")
fig.tight_layout(h_pad=0.4)
fig.savefig(OUT, dpi=200, facecolor='white')
print(os.path.abspath(OUT))
