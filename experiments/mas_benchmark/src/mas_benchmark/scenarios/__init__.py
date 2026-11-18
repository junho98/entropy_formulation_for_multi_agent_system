import dataclasses

from .circle import CircleArena, CircleConfig
from .encounter import Encounter, EncounterConfig

# Sec. 12.1 scenarios. Heading noise 2 rad/sqrt(s) for all externals (read off the v40 table).
PRESETS = {
    'S1': CircleConfig(name='S1', weights=(1.0, 3.0), v_env=1.2),
    'S2': CircleConfig(name='S2', n_ext=8, ext_speed=0.8, reactive=True, v_env=1.0),
    'S3': CircleConfig(name='S3', n_ext=4, ext_speed=0.5, v_env=0.6),
    'S4': CircleConfig(name='S4', n_ext=8, ext_speed=0.8, v_env=1.0),
}
# 2x3 grid: team (HOM all w = 1 | HET w alternating 1, 3) x outsiders (E0 none | E4 | E8, as in S4: speed 0.8, heading
# noise 2, non-reactive). Only the count changes. E0 uses v_env 1.2 as S1 (no externals, so it only enters as the
# public capability). HET-E0 is S1 and HOM-E8 is S4.
for _team, _w in (('HOM', (1.0,)), ('HET', (1.0, 3.0))):
    PRESETS[f'{_team}-E0'] = CircleConfig(name=f'{_team}-E0', weights=_w, v_env=1.2)
    for _n in (4, 8):
        PRESETS[f'{_team}-E{_n}'] = CircleConfig(name=f'{_team}-E{_n}', weights=_w, n_ext=_n, ext_speed=0.8, v_env=1.0)
GRID2X3 = ('HOM-E0', 'HOM-E4', 'HOM-E8', 'HET-E0', 'HET-E4', 'HET-E8')


def make_scenario(name):
    """'HOM-E0' or with a nominal right-hand bias: 'HOM-E0+b0.1' (always) / 'HOM-E0+bn0.1' (only with a body ahead),
    'HOM-E0+bb0.1' (sidestep to the right of the nearest body ahead within 2); 'HOM-E0+ts2' (targets at least 2 apart)."""
    base, *opts = name.split('+')
    cfg = PRESETS[base]
    for o in opts:
        if o.startswith('ts'):
            cfg = dataclasses.replace(cfg, target_sep=float(o[2:]))
        elif o.startswith('bb'):
            cfg = dataclasses.replace(cfg, bias=float(o[2:]), bias_mode='body', near_range=2.0)
        elif o.startswith('bn'):
            cfg = dataclasses.replace(cfg, bias=float(o[2:]), bias_mode='near')
        elif o.startswith('b'):
            cfg = dataclasses.replace(cfg, bias=float(o[1:]), bias_mode='always')
        else:
            raise ValueError(name)
    if opts:
        cfg = dataclasses.replace(cfg, name=name)
    return CircleArena(cfg)
