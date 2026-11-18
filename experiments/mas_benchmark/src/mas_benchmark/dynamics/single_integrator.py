import numpy as np

from ..core import Dynamics


class SingleIntegrator(Dynamics):
    """p' = u in the plane, ||u|| <= u_max imposed as n_faces half-planes (Sec. 11: 8 faces, 1.2)."""
    n_x = 2
    n_u = 2

    def __init__(self, u_max=1.2, n_faces=8):
        ang = 2 * np.pi * np.arange(n_faces) / n_faces
        self.A = np.stack([np.cos(ang), np.sin(ang)], axis=1)
        self.b = np.full(n_faces, u_max)
        self.u_max = u_max

    def step(self, x, u, dt):
        return x + dt * u

    def input_polytope(self):
        return self.A, self.b

    def position(self, x):
        return x
