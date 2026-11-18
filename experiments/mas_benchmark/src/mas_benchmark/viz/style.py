"""One style for every figure: a fixed colour per method, slide-readable sizes."""
import matplotlib
from matplotlib.colors import LinearSegmentedColormap

# fixed categorical order (validated palette); red is reserved for violations, grey for outsiders
METHOD = {
    'final': ('Ours', '#2a78d6'),
    'centred': (r'Ours, centred $\beta$', '#6250d6'),
    'oracle': ('Oracle', '#008300'),
    'tan': ('Tan', '#eb6834'),
    'pcca': ('PCCA', '#eda100'),
    'risk_ratio': ('Risk ratio', '#e87ba4'),
    'reciprocal': ('Reciprocal', '#1baf7a'),
}
VIOL = '#e34948'
OUTSIDER = '#9a9893'
INK, INK2, GRID = '#0b0b0b', '#52514e', '#e4e3df'
WEIGHT = {1.0: '#2a78d6', 3.0: '#1baf7a'}          # team colour by w_i (S1 alternates 1, 3)
# accumulated work W_i: one hue, light -> dark
WORK = LinearSegmentedColormap.from_list('work', ['#cfe0f6', '#5b9be3', '#1f5fae', '#0d2f5e'])


def label(key):
    return METHOD[key][0]


def colour(key):
    return METHOD[key][1]


def use():
    matplotlib.rcParams.update({
        'font.size': 10, 'axes.titlesize': 11, 'axes.labelsize': 10, 'legend.fontsize': 9,
        'xtick.labelsize': 9, 'ytick.labelsize': 9, 'pdf.fonttype': 42, 'ps.fonttype': 42,
        'axes.edgecolor': INK2, 'axes.labelcolor': INK, 'xtick.color': INK2, 'ytick.color': INK2,
        'axes.spines.top': False, 'axes.spines.right': False, 'axes.grid': True, 'grid.color': GRID,
        'grid.linewidth': 0.6, 'axes.axisbelow': True, 'lines.linewidth': 2.0, 'legend.frameon': False,
        'savefig.dpi': 200, 'savefig.bbox': 'tight',
    })


def save(fig, path):
    """path without extension -> .pdf (vector) and .png."""
    fig.savefig(f'{path}.pdf')
    fig.savefig(f'{path}.png')
