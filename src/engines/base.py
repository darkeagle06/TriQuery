"""
Abstract Base Engine definition for TriQuery.
Enforces a consistent execution and explainability contract across Relational, Graph, and Vector engines.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict
from src.core.types import EngineResult, EngineType


class BaseEngine(ABC):
    """
    Abstract base class for all query engines in TriQuery.
    Ensures engine interchangeability and uniform result reporting.
    """

    @property
    @abstractmethod
    def engine_type(self) -> EngineType:
        """Returns the specific paradigm identifier of this engine."""
        pass

    @abstractmethod
    def is_healthy(self) -> bool:
        """Checks if the underlying data store or model is available."""
        pass

    @abstractmethod
    def execute(self, query: Any, **kwargs) -> EngineResult:
        """Executes a query or sub-query and returns standardized EngineResult."""
        pass

    @abstractmethod
    def explain(self, query: Any, **kwargs) -> Dict[str, Any]:
        """Returns engine-level performance estimation or query plan breakdown."""
        pass
