from abc import ABC, abstractmethod


class Scenario(ABC):
    """The world outside the solver: team initial states, targets, nominal inputs and external agents.

    All randomness of the world comes from the rng passed to `reset`, so one seed gives the same
    initial conditions and external trajectories for every method.
    """
    name: str
    n_agents: int
    v_env: float

    @abstractmethod
    def reset(self, rng):
        """-> team x0 (N, n_x). Also resets externals and targets."""

    @abstractmethod
    def weights(self):
        """-> (N,) cost weights w_i."""

    @abstractmethod
    def nominal_input(self, x):
        """-> (N, n_u) nominal inputs u0_i for team states x."""

    @abstractmethod
    def externals(self):
        """-> (ext_x (E, n_x), ext_u_prev (E, n_u))."""

    @abstractmethod
    def advance(self, x, dt):
        """Move externals one step (they may react to the team states x) and update targets."""
