from .oracle import Oracle
from .pcca import PCCA
from .reciprocal import Reciprocal
from .risk_ratio import RiskRatio
from .tan import Tan
from .thermo import Thermo, ThermoBeta, ThermoFair, ThermoGas, ThermoRho


def make_solver(name):
    """'oracle', 'tan', 'tan_gradient', 'pcca', 'risk_ratio', 'reciprocal', 'ours_eps0.1' (any eps),
    'ours_eps0.1_w0.9' (following prior 0.9), 'ours_eps0.1_plain' (v40 exchange law, unweighted),
    'ours_eps0.1_s0.5' (exchange step x0.5), 'ours_eps0.1_newton' (local-curvature step),
    'ours_eps0.1_mem' / 'ours_eps0.1_mem10' (agreements kept across exits, forever / up to 10 s),
    'ours_eps0.1_region' / 'ours_eps0.1_region_damp' (trust-region exchange step)."""
    if name.startswith('beta_eps'):
        eps, rest = name[len('beta_eps'):].split('_W0')
        w0, leak = rest.split('_leak')
        leak, *flags = leak.split('_')
        bmax = [float(f[4:]) for f in flags if f.startswith('bmax')]
        cbar = [float(f[4:]) for f in flags if f.startswith('cbar')]
        return ThermoBeta(eps=float(eps), W0=float(w0), tau_leak=float(leak), read_constrained='rc' in flags,
                          read='read' in flags, beta_max=bmax[0] if bmax else 4.0, cbar=cbar[0] if cbar else None,
                          per_step='step' in flags)
    if name.startswith('fair_eps'):
        eps, rest = name[len('fair_eps'):].split('_W0')
        w0, *flags = rest.split('_')
        return ThermoFair(eps=float(eps), W0=float(w0), fix=flags[0] if flags else None)
    if name.startswith('gas_eps'):
        parts = name[len('gas_eps'):].split('_')
        return ThermoGas(eps=float(parts[0]), coverage='pair' if 'pair' in parts else 'closest',
                         replica='pair' if 'reppair' in parts else 'seen')
    if name.startswith('ours_eps'):
        parts = name[len('ours_eps'):].split('_')
        kw = dict(eps=float(parts[0]))
        for p in parts[1:]:
            if p in ('plain', 'mutual'):
                kw['law'] = p
            elif p == 'riskU':
                kw['risk_allotment'] = 'uniform'
            elif p == 'riskT':
                kw['risk_allotment'] = 'temperature'
            elif p == 'proj':
                kw['projection'] = True
            elif p == 'iso':
                kw['isolation'] = True
            elif p == 'damp':
                kw['damp_rows'] = True
            elif p in ('newton', 'kappa', 'region'):
                kw['step'] = p
            elif p.startswith('mem'):
                kw['agreement_memory'] = True
                kw['memory_s'] = float(p[3:]) if p[3:] else None
            elif p.startswith('w'):
                kw['follow_prior'] = float(p[1:])
            elif p.startswith('s'):
                kw['step_scale'] = float(p[1:])
        return Thermo(**kw)
    if name == 'tan_gradient':
        return Tan(law='gradient')
    return dict(oracle=Oracle, tan=Tan, pcca=PCCA, risk_ratio=RiskRatio, reciprocal=Reciprocal)[name]()
