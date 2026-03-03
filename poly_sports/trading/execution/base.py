"""Execution adapter interfaces."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import ExecutionResult, OrderIntent


class ExecutionAdapter(ABC):
    """Abstract execution adapter for paper/live modes."""

    @abstractmethod
    def execute(self, intent: OrderIntent) -> ExecutionResult:
        """Execute order intent and return execution result."""
        raise NotImplementedError
