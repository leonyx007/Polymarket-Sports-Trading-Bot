"""Live execution adapter placeholder (intentionally guarded)."""
from __future__ import annotations

from ..models import ExecutionResult, OrderIntent
from .base import ExecutionAdapter


class PolymarketLiveExecutionAdapter(ExecutionAdapter):
    """Disabled-by-default live adapter.

    This placeholder exists so the architecture supports later live rollout, but
    cannot place live orders until explicit implementation and runtime guards are set.
    """

    def execute(self, intent: OrderIntent) -> ExecutionResult:
        raise RuntimeError(
            "Live execution is disabled in this build. Use paper mode or implement "
            "a guarded live adapter with explicit ENABLE_LIVE_TRADING support."
        )
