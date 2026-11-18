"""Tables and figures for the 2x3 grid with target_sep 1.5 -> results/grid2x3/summary.md, tradeoff_E4_E8.pdf/.png,
range_vs_time.pdf/.png. Works on partial data (lists what is there).

    python scripts/grid2x3_ts_summary.py
"""
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt                                           # noqa: E402

from mas_benchmark.scenarios import GRID2X3                               # noqa: E402
from mas_benchmark.viz import style                                       # noqa: E402

OUT = Path(__file__).resolve().parents[1] / 'results' / 'grid2x3'
TS = '+ts1.5'
GROUPS = [('A. central / privileged', [('oracle_default', 'Oracle (default κ 2)'), ('oracle_tuned', 'Oracle (tuned κ 16)')]),
          ('B. communication + identification', [('tan', 'Tan')]),
          ('C. own observation only', [
              ('pcca_default', 'PCCA (default)'), ('pcca_tuned', 'PCCA (tuned κ 1, margin 0.2)'),
              ('reciprocal_default', 'Reciprocal (default)'), ('reciprocal_tuned', 'Reciprocal (tuned κ 16, margin 0.2)'),
              ('risk_ratio_default', 'Risk ratio (default)'), ('risk_ratio_tuned', 'Risk ratio (tuned c 2×, κ 4)'),
              ('ours_eps0.1', 'Ours, ε = 0.1'), ('ours_eps0.2', 'Ours, ε = 0.2'), ('ours_eps0.3', 'Ours, ε = 0.3'),
              ('beta_step_W04.22', 'Ours + centred β, W0 = 4.22, ε = 0.1'),
              ('beta_step_W04.22_eps0.2', 'Ours + centred β, W0 = 4.22, ε = 0.2')]),
          ('Reference: Ours with full information', [('ours_nocover_eps0.1', 'Ours, no cover (U = 0), ε = 0.1')])]
# appendix only: the earlier per-contact (frozen) β and per-step β at W0 2.1
OTHER_BETA = [('beta_W04.22', 'per-contact β (earlier variant), W0 = 4.22, ε = 0.1'),
              ('beta_W02.1', 'per-contact β (earlier variant), W0 = 2.1, ε = 0.1'),
              ('beta_W04.22_eps0.2', 'per-contact β (earlier variant), W0 = 4.22, ε = 0.2'),
              ('beta_step_W02.1', 'per-step β, W0 = 2.1, ε = 0.1')]
BETA_EPS = [('0.1', 'ours_eps0.1', 'beta_step_W04.22', 'beta_W04.22'),
            ('0.2', 'ours_eps0.2', 'beta_step_W04.22_eps0.2', 'beta_W04.22_eps0.2')]
CONFS = [c for _, G in GROUPS for c in G] + OTHER_BETA
TUNED_KEYS = ['oracle_tuned', 'tan', 'pcca_tuned', 'reciprocal_tuned', 'risk_ratio_tuned']
# Tan (2026-11-16): compared only in the cells without outsiders; its E4/E8 rows stay in runs.jsonl but are not reported
TAN_E0 = 'Tan (as published)'
TAN_ONLY_E0 = 'Tan et al. do not treat agents outside the team, so it is compared only in the cells without outsiders.'
TAN_CHOICES = ("Implementation choices in the Tan baseline that are ours: equal split of the −κh term between the pair, "
               "dropping the pair's y when the pair leaves sensing range, and a soft-QP fallback when the local problem "
               'is infeasible.')


def name_in(key, name, c0):
    return TAN_E0 if key == 'tan' else name


def group_stats(W, w):
    """per weight group: mean W, W std/mean within the group."""
    W, w = np.asarray(W), np.asarray(w)
    return {g: (W[w == g].mean(), W[w == g].std() / W[w == g].mean()) for g in (1.0, 3.0)}


T_AT = ('20', '60', '120', '240', '360', '480', '600')
N_HZ = 12                                            # seeds per cell in the 600 s runs


def load(name):
    p = OUT / name
    return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []


def ms(v, nd=3, pct=False):
    v = np.array([x for x in v if x is not None and np.isfinite(x)], float)
    if len(v) < 2:
        return '–' if not len(v) else (f'{100 * v[0]:.2f}' if pct else f'{v[0]:.{nd}f}')
    m, s = v.mean(), v.std(ddof=1) / np.sqrt(len(v))
    return f'{100 * m:.2f} ± {100 * s:.2f}' if pct else f'{m:.{nd}f} ± {s:.{nd}f}'


def mn(v):
    v = [x for x in v if x is not None and np.isfinite(x)]
    return f'{min(v):.2f}' if v else '–'


def paired(A, B, q, scale=1.0, nd=3):
    s = sorted(set(A) & set(B))
    return ms([scale * (B[k][q] - A[k][q]) for k in s], nd), len(s)


rows, hz = load('runs.jsonl'), load('horizon.jsonl') + load('horizon_eps0.2.jsonl')
rows = [r for r in rows if not (r['conf'] == 'tan' and not r['cell'].split('+')[0].endswith('E0'))]
APP = ['## Appendix: secondary metrics', '']
OB, ORow = [], []
cb = json.loads((OUT / 'cbar.json').read_text()) if (OUT / 'cbar.json').exists() else {}
g, h = defaultdict(dict), defaultdict(dict)
for r in rows:
    g[(r['cell'], r['conf'])][r['seed']] = r
for r in hz:
    h[(r['cell'], r['conf'])][r['seed']] = r

L = ['# 2×3 grid (target_sep 1.5)', '',
     'Team of 8 on the circle arena; targets redrawn on arrival and kept at least 1.5 from the other agents\' current '
     'targets (target_sep 1.5, applied identically to every method). Team: HOM = all w = 1; HET = w alternating 1, 3. '
     'Outsiders: E0 none; E4 / E8 = 4 / 8 as in S4 (speed 0.8, heading noise 2 rad/√s, never yield). v_env 1.0 (E4/E8), '
     '1.2 (E0, as S1). Ours: pairwise specification, mutual law, default step 1/(2k_e), k_e 20, δ 0.05 per neighbour, '
     'window 50, prior 0.97. Centred β: β_i = clip(exp((W_i − c̄ t)/W0), 1/8, 8), applied at every step (per-step, '
     'paper v42 Def. 6.5); c̄ per cell = fleet-mean work rate of that cell\'s Ours runs at the same ε (mean of '
     'mean_i W_i(120)/120 over the 24 seeds). The earlier per-contact variant (β frozen over a contact) is in the '
     'appendix only. Baselines at default and at the values tuned on seeds 100–102 '
     'under target_sep 1.5 (results/tuning/tuning.md). ' + TAN_ONLY_E0 + ' ' + TAN_CHOICES + ' Seeds 0–23 × 120 s, same seeds for all; mean ± '
     's.e. over seeds; minimum distances = minimum over seeds; violation = % of time with some pair closer than 0.95ρ. '
     'W_i = accumulated base cost ½ w_i‖u_i − u0_i‖²; range = max_i W_i − min_i W_i. Standstill: some agent with '
     '|u| < 0.15 for more than 10 s in a row. Price imbalance: time-weighted, isolated two-agent encounters. Copy gap: '
     'max over agreements and steps of |r_ik + r_ki|. Slack: fraction of steps in which a soft (penalised) QP row was used. '
     'Ours, no cover: the full-information reference, rooms R_ik = r_ik and R_ki = −r_ik (cover U = 0), everything else as '
     'Ours ε 0.1; not implementable from own observation, it isolates the cost of the cover. Σ λU = time-average over '
     'agent-time of Σ_k λ_ik U_ik (same units as cost). Secondary metrics are in the appendix.',
     '', '| c̄ | ' + ' | '.join(GRID2X3) + ' |', '|---|' + '---|' * len(GRID2X3),
     '| fleet-mean work rate | ' + ' | '.join(f'{cb[c + TS]:.4f}' if c + TS in cb else '–' for c in GRID2X3) + ' |', '']
for c0 in GRID2X3:
    c = c0 + TS
    ext = not c0.endswith('E0')
    main = [f'## {c0}', '', '| method | n | cost | viol. outsiders (%) | viol. team (%) | viol. total (%) | W std/mean | '
            'W range | Jain |', '|---|---|---|---|---|---|---|---|---|']
    sec = ['', f'Secondary ({c0}):', '', '| method | min dist. outsiders | min dist. team | standstill | slack (%) | '
           'price imbalance | max \\|r_ik + r_ki\\| |', '|---|---|---|---|---|---|---|']
    for gname, G in GROUPS:
        main.append(f'| *{gname}* |' + ' |' * 8)
        sec.append(f'| *{gname}* |' + ' |' * 6)
        if gname.startswith('B.') and ext:
            main.append(f'| – ({TAN_ONLY_E0}) |' + ' |' * 8)
        for key, name in G:
            D = g.get((c, key), {})
            if not D:
                continue
            name = name_in(key, name, c0)
            R = list(D.values())
            ours = key.startswith(('ours', 'beta'))
            gap = f"{max(r['gap_max'] for r in R):.2g}" if ours else '–'
            st = sum(r['longest_stop_s'] > 10 for r in R)
            tot = [(r['viol_ext'] if ext else 0.0) + r['viol_team'] for r in R]
            main.append(f"| {name} | {len(R)} | {ms([r['cost'] for r in R])} | "
                        f"{ms([r['viol_ext'] for r in R], pct=True) if ext else '–'} | {ms([r['viol_team'] for r in R], pct=True)} | "
                        f"{ms(tot, pct=True)} | {ms([r['W_cv'] for r in R])} | {ms([r['W_range'] for r in R], 2)} | "
                        f"{ms([r['jain'] for r in R])} |")
            sec.append(f"| {name} | {mn([r['min_dist_ext'] for r in R]) if ext else '–'} | {mn([r['min_dist_team'] for r in R])} | "
                       f"{st}/{len(R)} | {ms([r['slack_frac'] for r in R], pct=True)} | "
                       f"{ms([r['imbalance_time'] for r in R], 2) if ours else '–'} | {gap} |")
    L += main
    APP += [f'### {c0}'] + sec[2:] + ['']
    F = g.get((c, 'ours_eps0.1'), {})
    for e_, ko, kb, kf in BETA_EPS:
        Fo, B = g.get((c, ko), {}), g.get((c, kb), {})
        if Fo and B:
            a, n = paired(Fo, B, 'W_cv'); d, _ = paired(Fo, B, 'W_range', 1, 2)
            e, _ = paired(Fo, B, 'viol_ext', 100, 2); k, _ = paired(Fo, B, 'cost')
            L.append(f'\nPaired β (W0 = 4.22, ε {e_}) − Ours ε {e_} (n = {n}): Δ W std/mean {a}; Δ W range {d}; '
                     f'Δ viol. outsiders {e if ext else "–"} pp; Δ cost {k}.')
        Bf = g.get((c, kf), {})
        if B and Bf:
            ORow.append(f"| {c0} | {e_} | {paired(Bf, B, 'cost')[0]} | {paired(Bf, B, 'viol_team', 100, 2)[0]} | "
                        f"{paired(Bf, B, 'viol_ext', 100, 2)[0] if ext else '–'} | {paired(Bf, B, 'W_cv')[0]} | "
                        f"{paired(Bf, B, 'W_range', 1, 2)[0]} |")
        for key, name in OTHER_BETA:
            R = list(g.get((c, key), {}).values())
            if R and e_ == '0.1':
                OB.append(f"| {c0} | {name} | {len(R)} | {ms([r['cost'] for r in R])} | {ms([r['viol_team'] for r in R], pct=True)} | "
                          f"{ms([r['viol_ext'] for r in R], pct=True) if ext else '–'} | {ms([r['W_cv'] for r in R])} | "
                          f"{ms([r['W_range'] for r in R], 2)} |")
    B = g.get((c, 'beta_step_W04.22'), {})
    if B:
        L += ['', 'Paired β (W0 = 4.22, ε 0.1) − each tuned baseline (same seeds): Δ W std/mean · Δ W range · Δ viol. outsiders (pp) · Δ cost', '']
        for key in TUNED_KEYS:
            A = g.get((c, key), {})
            if A:
                L.append(f"- vs {name_in(key, dict(CONFS)[key], c0)}: {paired(A, B, 'W_cv')[0]} · {paired(A, B, 'W_range', 1, 2)[0]} · "
                         f"{paired(A, B, 'viol_ext', 100, 2)[0] if ext else '–'} · {paired(A, B, 'cost')[0]}")
    N0 = g.get((c, 'ours_nocover_eps0.1'), {})
    if F and N0:
        k, n = paired(N0, F, 'cost', 1, 4)
        lu = [F[q]['info_cost'] for q in F if 'info_cost' in F[q]]
        L.append(f'\nPaired Ours ε 0.1 − Ours no cover (n = {n}): Δ cost {k}; Σ λU of Ours {ms(lu, 4)}.')
    if c0.startswith('HET'):
        L += ['', 'HET, per weight group (W includes the weight: W_i = ∫ ½ w_i‖u_i − u0_i‖² dt). Mean W of the group · '
              'W std/mean within the group:', '', '| method | w = 1: mean W | w = 1: std/mean | w = 3: mean W | w = 3: std/mean |',
              '|---|---|---|---|---|']
        for key, name in CONFS:
            name = name_in(key, name, c0)
            R = list(g.get((c, key), {}).values())
            if not R:
                continue
            w = np.array([1.0, 3.0] * 4)
            gs = [group_stats(r['W'], w) for r in R]
            L.append(f"| {name} | {ms([x[1.0][0] for x in gs], 2)} | {ms([x[1.0][1] for x in gs])} | "
                     f"{ms([x[3.0][0] for x in gs], 2)} | {ms([x[3.0][1] for x in gs])} |")
    L.append('')

INFO = []
for c0 in GRID2X3:
    c = c0 + TS
    F, N0, O = (g.get((c, k), {}) for k in ('ours_eps0.1', 'ours_nocover_eps0.1', 'oracle_tuned'))
    s = sorted(set(F) & set(N0) & set(O))
    if not s:
        continue
    cf, cn, co = (np.array([X[q]['cost'] for q in s]) for X in (F, N0, O))
    lu = [F[q].get('info_cost', np.nan) for q in s]
    gap, info = (cf - co).mean(), (cf - cn).mean()
    INFO.append(f"| {c0} | {len(s)} | {ms(cf - co, 4)} | {ms(cf - cn, 4)} | {ms(lu, 4)} | "
                f"{(100 * info / gap if abs(gap) > 1e-12 else np.nan):.0f} | {ms(cn - co, 4)} |")
if INFO:
    L += ['## Cost of information', '', 'Paired over seeds. Gap = Ours ε 0.1 − tuned Oracle; cover = Ours − Ours no cover '
          '(the part of the gap due to not knowing the neighbour); share = cover / gap (ratio of the means); rest = Ours no '
          'cover − tuned Oracle.', '',
          '| cell | n | gap to Oracle | cover: Ours − no cover | Σ λU (Ours) | share explained (%) | rest: no cover − Oracle |',
          '|---|---|---|---|---|---|---|'] + INFO + ['']

L += ['## Fairness summary (all cells × methods)', '', 'W std/mean and W range (max − min), mean ± s.e. over 24 seeds.', '',
      '| method | ' + ' | '.join(GRID2X3) + ' |', '|---|' + '---|' * len(GRID2X3)]
for gname, G in GROUPS:
    L.append(f'| *{gname}* |' + ' |' * len(GRID2X3))
    for key, name in G:
        cells_ = []
        for c0 in GRID2X3:
            R = list(g.get((c0 + TS, key), {}).values())
            cells_.append(f"{ms([r['W_cv'] for r in R], 2)} / {ms([r['W_range'] for r in R], 1)}" if R else '–')
        L.append(f"| {TAN_E0 if key == 'tan' else name} | " + ' | '.join(cells_) + ' |')
L += ['', TAN_ONLY_E0, '']

def hz_beta(c, e_, kb, kf):
    """600 s β rows: per-step if present, else the per-contact variant (marked)."""
    return (h.get((c, kb), {}), '') if len(h.get((c, kb), {})) >= N_HZ else (h.get((c, kf), {}), ' (per-contact variant)')


if hz:
    L += ['## Horizon (600 s)', '', 'Ours vs centred β (W0 4.22) at the same ε, seeds 0–11, same seeds; Δ = β − Ours, paired.', '']
    for c0 in GRID2X3:
        c = c0 + TS
        ext = not c0.endswith('E0')
        for e_, ko, kb, kf in BETA_EPS:
            F = h.get((c, ko), {})
            B, tag = hz_beta(c, e_, kb, kf)
            s = sorted(set(F) & set(B))
            if len(s) < N_HZ:                            # shown only once all 12 seeds are in
                continue
            L += [f'### {c0}, ε {e_} (n = {len(s)}){tag}', '', '| t (s) | range: Ours | β | Δ | W std/mean: Ours | β | Δ |',
                  '|---|---|---|---|---|---|---|']
            for t in T_AT:
                fr, br = [F[k]['at'][t]['W_range'] for k in s], [B[k]['at'][t]['W_range'] for k in s]
                fc, bc = [F[k]['at'][t]['W_cv'] for k in s], [B[k]['at'][t]['W_cv'] for k in s]
                L.append(f'| {t} | {ms(fr, 2)} | {ms(br, 2)} | {ms(np.subtract(br, fr), 2)} | {ms(fc)} | {ms(bc)} | {ms(np.subtract(bc, fc))} |')
            if e_ == '0.1':
                for key in ('oracle_tuned', 'pcca_tuned'):
                    X = h.get((c, key), {})
                    sx = sorted(set(X) & set(s))
                    if sx:
                        L += ['', f'{dict(CONFS)[key]} at 600 s (n = {len(sx)}), range / W std/mean: ' + '; '.join(
                            f"{t} s {ms([X[k]['at'][t]['W_range'] for k in sx], 2)} / {ms([X[k]['at'][t]['W_cv'] for k in sx])}" for t in T_AT)]
            L += ['', f"600 s run: cost Ours {ms([F[k]['cost'] for k in s])}, β {ms([B[k]['cost'] for k in s])}; team viol. "
                      f"Ours {ms([F[k]['viol_team'] for k in s], pct=True)} %, β {ms([B[k]['viol_team'] for k in s], pct=True)} %"
                  + (f"; outsider viol. Ours {ms([F[k]['viol_ext'] for k in s], pct=True)} %, β "
                     f"{ms([B[k]['viol_ext'] for k in s], pct=True)} %" if ext else '')
                  + (f"; standstills Ours {sum(F[k]['longest_stop_s'] > 10 for k in s)}/{len(s)}, β "
                     f"{sum(B[k].get('longest_stop_s', 0) > 10 for k in s)}/{len(s)}." if all('longest_stop_s' in F[k] for k in s) else '.'), '']
if len(APP) > 2:
    L += APP
if OB:
    L += ['## Appendix: other β variants', '', 'The earlier per-contact variant (β_i frozen at its value when a contact starts) '
          'and per-step β at W0 = 2.1; not in the main table. 24 seeds × 120 s, mean ± s.e.', '',
          '| cell | variant | n | cost | viol. team (%) | viol. outsiders (%) | W std/mean | W range |',
          '|---|---|---|---|---|---|---|---|'] + OB + ['']
if ORow:
    L += ['Paired per-step − per-contact β (W0 = 4.22, same ε, same seeds):', '',
          '| cell | ε | Δ cost | Δ viol. team (pp) | Δ viol. outsiders (pp) | Δ W std/mean | Δ W range |',
          '|---|---|---|---|---|---|---|'] + ORow + ['']
HF = []
for c0 in GRID2X3:
    c = c0 + TS
    X, F = h.get((c, 'beta_W04.22'), {}), h.get((c, 'ours_eps0.1'), {})
    k = sorted(set(X) & set(F))
    if len(k) >= N_HZ:
        ext = not c0.endswith('E0')
        HF.append(f"| {c0} | {len(k)} | {ms([X[q]['at']['600']['W_range'] for q in k], 2)} | {ms([X[q]['at']['600']['W_cv'] for q in k])} | "
                  f"{ms([X[q]['cost'] for q in k])} | {ms([X[q]['viol_team'] for q in k], pct=True)} | "
                  f"{ms([X[q]['viol_ext'] for q in k], pct=True) if ext else '–'} | "
                  f"{ms([X[q]['at']['600']['W_range'] - F[q]['at']['600']['W_range'] for q in k], 2)} |")
if HF and any(len(h.get((c0 + TS, 'beta_step_W04.22'), {})) >= N_HZ for c0 in GRID2X3):
    L += ['600 s, per-contact β (earlier variant), W0 = 4.22, ε = 0.1, seeds 0–11:', '',
          '| cell | n | W range (600 s) | W std/mean (600 s) | cost | viol. team (%) | viol. outsiders (%) | Δ W range vs Ours ε 0.1 |',
          '|---|---|---|---|---|---|---|---|'] + HF + ['']
(OUT / 'summary.md').write_text('\n'.join(L) + '\n')
print('\n'.join(L))

# figures
style.use()
STY = {'oracle': 'oracle', 'tan': 'tan', 'pcca': 'pcca', 'risk_ratio': 'risk_ratio', 'reciprocal': 'reciprocal'}
cells = [c for c in GRID2X3 if not c.endswith('E0')]
# main figure: three axes. Top row: total violation vs cost; bottom row: W std/mean vs cost; one column per cell.
MAIN = [('oracle_tuned', 'oracle', 'A'), ('tan', 'tan', 'B'), ('pcca_tuned', 'pcca', 'C'), ('reciprocal_tuned', 'reciprocal', 'C'),
        ('risk_ratio_tuned', 'risk_ratio', 'C'), ('ours_eps0.1', 'final', 'C'), ('beta_step_W04.22', 'centred', 'C'),
        ('beta_step_W04.22_eps0.2', 'centred', 'C')]
MK = {'A': 's', 'B': '^', 'C': 'o'}
MKK = {'beta_step_W04.22_eps0.2': 'D'}
LAB = {'tan': 'Tan (as published; E0 only)', 'ours_eps0.1': r'Ours, $\varepsilon$ = 0.1', 'beta_step_W04.22': r'Ours + centred $\beta$, $\varepsilon$ = 0.1',
       'beta_step_W04.22_eps0.2': r'Ours + centred $\beta$, $\varepsilon$ = 0.2'}


def lab_of(key, sty, grp):
    return LAB.get(key, style.label(sty) + ('' if sty == 'tan' else ' (tuned)')) + f' [{grp}]'


def msv(R, f):
    v = np.array([f(r) for r in R], float)
    return v.mean(), (v.std(ddof=1) / np.sqrt(len(v)) if len(v) > 1 else 0.0)


if rows:
    fig, axes = plt.subplots(2, 6, figsize=(18, 6.4), sharex='col')
    for j, c0 in enumerate(GRID2X3):
        ext = not c0.endswith('E0')
        for key, sty, grp in MAIN:
            R = list(g.get((c0 + TS, key), {}).values())
            if not R:
                continue
            (cx, sx) = msv(R, lambda r: r['cost'])
            (vy, sy) = msv(R, lambda r: 100 * ((r['viol_ext'] if ext else 0.0) + r['viol_team']))
            (fy, sf) = msv(R, lambda r: r['W_cv'])
            lab = lab_of(key, sty, grp)
            kw = dict(fmt=MKK.get(key, MK[grp]), ms=7, color=style.colour(sty), capsize=2, elinewidth=0.8)
            axes[0, j].errorbar([cx], [vy], xerr=[sx], yerr=[sy], label=lab, **kw)
            axes[1, j].errorbar([cx], [fy], xerr=[sx], yerr=[sf], **kw)
        axes[0, j].set_title(c0)
        axes[0, j].set_yscale('symlog', linthresh=0.1); axes[0, j].set_ylim(-0.06, 100)
        axes[1, j].set_xlabel('cost')
    axes[0, 0].set_ylabel('violation, outsiders + team (%)')
    axes[1, 0].set_ylabel('W std/mean (lower = fairer)')
    h_, l_ = axes[0, 5].get_legend_handles_labels()
    fig.legend(h_, l_, loc='lower center', ncol=4, fontsize=8, bbox_to_anchor=(0.5, -0.09))
    fig.text(0.5, -0.12, 'Mean ± s.e. over 24 seeds, target_sep 1.5. [A] central, [B] communication + identification, '
             '[C] own observation only. Lower is better on every axis. ' + TAN_ONLY_E0, ha='center', fontsize=8,
             color=style.INK2)
    fig.tight_layout()
    style.save(fig, OUT / 'three_axes')
    plt.close(fig)
    # compact summary: mean rank over the six cells on each axis, among the methods present in every cell (Tan is not)
    MAIN_R = [m for m in MAIN if m[0] != 'tan']
    ranks = {k: {'cost': [], 'violation': [], 'fairness': []} for k, _, _ in MAIN_R}
    for c0 in GRID2X3:
        ext = not c0.endswith('E0')
        vals = {}
        for key, _, _ in MAIN_R:
            R = list(g.get((c0 + TS, key), {}).values())
            if R:
                vals[key] = (np.mean([r['cost'] for r in R]),
                             np.mean([(r['viol_ext'] if ext else 0.0) + r['viol_team'] for r in R]),
                             np.mean([r['W_cv'] for r in R]))
        if len(vals) < len(MAIN_R):
            continue
        for a, ax_name in enumerate(('cost', 'violation', 'fairness')):
            order = sorted(vals, key=lambda k: vals[k][a])
            for rk, key in enumerate(order, 1):
                # ties (e.g. zero violation) share the best rank
                ranks[key][ax_name].append(1 + sum(vals[o][a] < vals[key][a] - 1e-12 for o in vals))
    if all(ranks[k]['cost'] for k in ranks):
        fig, ax = plt.subplots(figsize=(8, 4.2))
        y = np.arange(len(MAIN_R))
        for a, (ax_name, alpha) in enumerate((('cost', 0.45), ('violation', 0.75), ('fairness', 1.0))):
            vals_ = [np.mean(ranks[k][ax_name]) for k, _, _ in MAIN_R]
            ax.barh(y + (a - 1) * 0.26, vals_, 0.24, color=[style.colour(s) for _, s, _ in MAIN_R], alpha=alpha,
                    label=ax_name, edgecolor='white')
            for yi, v in zip(y + (a - 1) * 0.26, vals_):
                ax.text(v + 0.05, yi, f'{ax_name[0]} {v:.1f}', va='center', fontsize=7, color=style.INK2)
        ax.set_yticks(y, [lab_of(k, s, grp) for k, s, grp in MAIN_R])
        ax.invert_yaxis(); ax.set_xlim(0, len(MAIN_R) + 0.8); ax.grid(axis='y', visible=False)
        ax.set_xlabel(f'mean rank over the six cells (1 = best of {len(MAIN_R)})')
        ax.legend(loc='lower right', fontsize=8, title='bar shade', title_fontsize=7)
        fig.text(0.5, -0.02, 'Tan is not ranked: ' + TAN_ONLY_E0, ha='center', fontsize=7, color=style.INK2, wrap=True)
        fig.tight_layout()
        style.save(fig, OUT / 'rank_summary')
        plt.close(fig)
if rows:
    fig, axes = plt.subplots(2, 2, figsize=(10, 7.6))
    for ax, c0 in zip(axes.ravel(), cells):
        c = c0 + TS
        pts = []
        for e in ('0.1', '0.2', '0.3'):
            R = list(g.get((c, f'ours_eps{e}'), {}).values())
            if R:
                pts.append((np.mean([r['cost'] for r in R]), np.std([r['cost'] for r in R], ddof=1) / np.sqrt(len(R)),
                            100 * np.mean([r['viol_ext'] for r in R]), 100 * np.std([r['viol_ext'] for r in R], ddof=1) / np.sqrt(len(R)), e))
        if pts:
            x, sx, y, sy, e = zip(*pts)
            ax.errorbar(x, y, xerr=sx, yerr=sy, color=style.colour('final'), marker='o', ms=7, capsize=2, elinewidth=0.8,
                        label=r'Ours ($\varepsilon$ = 0.1, 0.2, 0.3)', zorder=3)
        for w, mk in (('0.1', 'D'), ('0.2', 'd')):
            R = list(g.get((c, 'beta_step_W04.22' + ('' if w == '0.1' else '_eps0.2')), {}).values())
            if R:
                ax.errorbar([np.mean([r['cost'] for r in R])], [100 * np.mean([r['viol_ext'] for r in R])],
                            xerr=[np.std([r['cost'] for r in R], ddof=1) / np.sqrt(len(R))],
                            yerr=[100 * np.std([r['viol_ext'] for r in R], ddof=1) / np.sqrt(len(R))], fmt=mk, ms=7,
                            color=style.colour('centred'), capsize=2, elinewidth=0.8, zorder=4,
                            label=fr'Ours + centred $\beta$, $\varepsilon$ = {w}')
        for m, s in STY.items():
            for kind, mk, fill in (('default', 's', 'none'), ('tuned', 's', None)):
                key = m if m == 'tan' else f'{m}_{kind}'
                if m == 'tan' and kind == 'tuned':
                    continue
                R = list(g.get((c, key), {}).values())
                if not R:
                    continue
                ax.errorbar([np.mean([r['cost'] for r in R])], [100 * np.mean([r['viol_ext'] for r in R])],
                            xerr=[np.std([r['cost'] for r in R], ddof=1) / np.sqrt(len(R))],
                            yerr=[100 * np.std([r['viol_ext'] for r in R], ddof=1) / np.sqrt(len(R))], fmt=mk, ms=7,
                            color=style.colour(s), mfc=fill or style.colour(s), capsize=2, elinewidth=0.8, zorder=3,
                            label=style.label(s) + ('' if m == 'tan' else f' ({kind})'))
        ax.set_yscale('symlog', linthresh=0.1)
        ax.set_ylim(-0.06, 100)
        ax.set_xlabel('cost (mean per agent)')
        ax.set_ylabel('time in violation toward outsiders (%)')
        ax.set_title(c0)
    h_, l_ = axes[0, 0].get_legend_handles_labels()
    fig.legend(h_, l_, loc='lower center', ncol=4, fontsize=8, bbox_to_anchor=(0.5, -0.06))
    fig.text(0.5, -0.11, 'Open squares: default settings; filled: tuned. Mean ± s.e. over 24 seeds; symlog axis.',
             ha='center', fontsize=8, color=style.INK2)
    fig.tight_layout()
    style.save(fig, OUT / 'tradeoff_E4_E8')
    plt.close(fig)
if hz:
    fig, axes = plt.subplots(2, 3, figsize=(13, 6.8))
    for ax, c0 in zip(axes.ravel(), GRID2X3):
        c = c0 + TS
        hb = 'beta_step_W04.22' if len(h.get((c, 'beta_step_W04.22'), {})) >= N_HZ else 'beta_W04.22'
        for key, sty, ls, lab in (('ours_eps0.1', 'final', '-', r'Ours, $\varepsilon$ = 0.1'),
                                  (hb, 'centred', '-', r'Ours + centred $\beta$, $\varepsilon$ = 0.1'
                                   + ('' if hb.startswith('beta_step') else ' (per-contact)')),
                                  ('ours_eps0.2', 'final', '--', r'Ours, $\varepsilon$ = 0.2'),
                                  ('beta_step_W04.22_eps0.2', 'centred', '--', r'Ours + centred $\beta$, $\varepsilon$ = 0.2'),
                                  ('oracle_tuned', 'oracle', '-', 'Oracle (tuned)'), ('pcca_tuned', 'pcca', '-', 'PCCA (tuned)')):
            R = list(h.get((c, key), {}).values())
            if len(R) < N_HZ:
                continue
            ts = sorted(int(t) for t in R[0]['at'])
            v = np.array([[r['at'][str(t)]['W_range'] for t in ts] for r in R])
            m, s = v.mean(0), v.std(0, ddof=1) / np.sqrt(len(v)) if len(v) > 1 else np.zeros(len(ts))
            ax.plot(ts, m, color=style.colour(sty), ls=ls, marker='o', ms=3, label=lab)
            ax.fill_between(ts, m - s, m + s, color=style.colour(sty), alpha=0.18, lw=0)
        ax.set_title(c0); ax.set_xlim(0, 600); ax.set_ylim(bottom=0)
        ax.set_xlabel('t (s)'); ax.set_ylabel(r'$\max_i W_i - \min_i W_i$')
    axes[0, 0].legend(loc='upper left', fontsize=8)
    fig.tight_layout()
    style.save(fig, OUT / 'range_vs_time')
    plt.close(fig)
