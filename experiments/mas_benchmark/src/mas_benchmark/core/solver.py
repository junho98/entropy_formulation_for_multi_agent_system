from abc import ABC, abstractmethod


class Solver(ABC):
    """One method. `act` returns every team member's input at once.

    Decentralised methods loop over agents inside `act` and use only what agent i may see
    (obs.neighbours[i] without the `external` flag, its own nominal input and weight);
    centralised ones (oracle) may use the whole observation.
    """
    name = '?'

    def reset(self, scenario, dynamics, spec, dt):
        self.scenario = scenario
        self.dynamics = dynamics
        self.spec = spec
        self.dt = dt

    @abstractmethod
    def act(self, obs):
        """-> (u (N, n_u), info dict). `info` is stored per step in Log.info."""
