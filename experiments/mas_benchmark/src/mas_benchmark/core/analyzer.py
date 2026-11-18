from abc import ABC, abstractmethod


class Analyzer(ABC):
    """Log -> dict of named scalar metrics."""
    name = '?'

    @abstractmethod
    def __call__(self, log):
        ...
