"""Budget enforcement and cross-session circuit breaker.

Simplest viable implementation:
- check_budget(): tiered alerts (50/75/90%) + hard limit (>100%)
- check_circuit_breaker(): sliding-window abort counter; trips after 5
  aborts within 1 hour, cools down for 10 minutes
- record_abort(): called when a variant exceeds the budget

Design notes:
- Pure functions, no I/O, no external state store. The deque lives in
  process memory, which is sufficient for the single-worker uvicorn setup
  used by screenshot-to-code.
- Multi-process deployments would need to swap the deque for Redis; left
  as a future extension.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from time import time
from typing import Optional

from config import GENERATION_MAX_COST_USD

# Alert thresholds (fraction of GENERATION_MAX_COST_USD)
_WARN_THRESHOLD = 0.50
_ALERT_THRESHOLD = 0.75
_CRITICAL_THRESHOLD = 0.90

# Circuit breaker params
_ABORT_WINDOW = 3600  # 1 hour sliding window
_ABORT_THRESHOLD = 5  # aborts before breaker trips
_COOLDOWN_DURATION = 600  # 10 minutes cooldown

# Module-level state (single-process)
_RECENT_ABORTS: deque = deque()
_last_cooldown_start: Optional[float] = None


@dataclass
class BudgetDecision:
    """Result of a budget check."""

    allow: bool
    alert_level: str  # "none" | "warn" | "alert" | "critical" | "exceeded"
    spent_usd: float
    limit_usd: float
    reason: str = ""


def check_budget(spent: Optional[float]) -> BudgetDecision:
    """Check single-variant spend against the hard budget.

    Returns a BudgetDecision describing whether to proceed and what alert
    level (if any) to surface. Call record_abort() externally when
    level == "exceeded".
    """
    if spent is None:
        return BudgetDecision(True, "none", 0.0, GENERATION_MAX_COST_USD)

    ratio = spent / GENERATION_MAX_COST_USD
    if ratio > 1.0:
        return BudgetDecision(
            False,
            "exceeded",
            spent,
            GENERATION_MAX_COST_USD,
            f"${spent:.2f} exceeds ${GENERATION_MAX_COST_USD:.2f}",
        )
    if ratio >= _CRITICAL_THRESHOLD:
        return BudgetDecision(True, "critical", spent, GENERATION_MAX_COST_USD)
    if ratio >= _ALERT_THRESHOLD:
        return BudgetDecision(True, "alert", spent, GENERATION_MAX_COST_USD)
    if ratio >= _WARN_THRESHOLD:
        return BudgetDecision(True, "warn", spent, GENERATION_MAX_COST_USD)
    return BudgetDecision(True, "none", spent, GENERATION_MAX_COST_USD)


def record_abort() -> None:
    """Record that a variant exceeded the budget. Used by circuit breaker."""
    _RECENT_ABORTS.append(time())


def check_circuit_breaker() -> Optional[str]:
    """Return a reason string if the breaker is open, else None (allow)."""
    global _last_cooldown_start

    # If in cooldown, remain open until it expires
    if _last_cooldown_start is not None:
        elapsed = time() - _last_cooldown_start
        if elapsed < _COOLDOWN_DURATION:
            remaining = int(_COOLDOWN_DURATION - elapsed)
            return (
                f"Circuit breaker open: cooldown {remaining}s remaining "
                f"(triggered by {_ABORT_THRESHOLD} aborts in {_ABORT_WINDOW}s)"
            )
        # Cooldown over, reset
        _last_cooldown_start = None

    # Expire old aborts
    now = time()
    while _RECENT_ABORTS and now - _RECENT_ABORTS[0] > _ABORT_WINDOW:
        _RECENT_ABORTS.popleft()

    # Trip if threshold reached
    if len(_RECENT_ABORTS) >= _ABORT_THRESHOLD:
        _last_cooldown_start = now
        _RECENT_ABORTS.clear()
        return (
            f"Circuit breaker tripped: {_ABORT_THRESHOLD} budget aborts "
            f"within {_ABORT_WINDOW}s — cooldown {_COOLDOWN_DURATION}s"
        )

    return None


def reset() -> None:
    """Reset all state. For testing only."""
    global _last_cooldown_start
    _RECENT_ABORTS.clear()
    _last_cooldown_start = None
