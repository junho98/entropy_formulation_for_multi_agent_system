from abc import ABC, abstractmethod


class Dynamics(ABC):
    """Per-agent dynamics x+ = F(x, u, dt) with a polyhedral input set {u : A u <= b}."""
    n_x: int
    n_u: int

    @abstractmethod
    def step(self, x, u, dt):
        """x: (n_x,) or (N, n_x); u matching. Returns next state."""

    @abstractmethod
    def input_polytope(self):
        """-> (A, b) with the admissible inputs {u : A u <= b}."""

    @abstractmethod
    def position(self, x):
        """Planar position of a state (or a stack of states)."""
