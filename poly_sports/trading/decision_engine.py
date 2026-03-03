"""Signal normalization and idempotent decision helpers."""
from __future__ import annotations

import hashlib
from typing import Dict, Iterable, List, Set, Tuple

from .models import Opportunity, Signal, utc_now_iso


def generate_signal_id(
    market_id: str,
    outcome_name: str,
    side: str,
    suggested_price: float,
    cycle_bucket: str,
) -> str:
    raw = f"{market_id}|{outcome_name.lower()}|{side}|{suggested_price:.4f}|{cycle_bucket}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def opportunity_from_dict(raw: Dict[str, object]) -> Opportunity:
    """Convert arbitrage result dict into typed opportunity."""
    matched = raw.get("matched_outcomes", [])
    first_match = matched[0] if isinstance(matched, list) and matched else {}
    return Opportunity(
        market_id=str(raw.get("pm_market_id", "")),
        event_id=str(raw.get("pm_event_id", "")),
        outcome_name=str(first_match.get("pm_outcome", "")),
        entry_price=float(first_match.get("pm_price", 0.0) or 0.0),
        target_price=float(first_match.get("sb_implied_prob", 0.0) or 0.0),
        expected_profit_pct=float(raw.get("profit_margin", 0.0) or 0.0),
        liquidity=float(raw.get("pm_liquidity", raw.get("liquidity", 0.0)) or 0.0),
        spread=float(raw.get("pm_spread", 0.0) or 0.0),
        confidence=float(raw.get("match_confidence", 0.0) or 0.0),
        raw=raw,
    )


def build_signals(
    opportunities: Iterable[Opportunity],
    cycle_bucket: str,
) -> List[Signal]:
    signals: List[Signal] = []
    now = utc_now_iso()
    for opp in opportunities:
        if not opp.market_id or not opp.outcome_name or opp.entry_price <= 0:
            continue
        signal_id = generate_signal_id(
            market_id=opp.market_id,
            outcome_name=opp.outcome_name,
            side="BUY",
            suggested_price=opp.entry_price,
            cycle_bucket=cycle_bucket,
        )
        signals.append(
            Signal(
                signal_id=signal_id,
                market_id=opp.market_id,
                event_id=opp.event_id,
                outcome_name=opp.outcome_name,
                side="BUY",
                order_type="ENTRY",
                suggested_price=opp.entry_price,
                target_price=opp.target_price,
                confidence=opp.confidence,
                expected_profit_pct=opp.expected_profit_pct,
                liquidity=opp.liquidity,
                spread=opp.spread,
                created_at=now,
                metadata={"raw_opportunity": opp.raw},
            )
        )
    return signals


def should_open_signal(signal_id: str, seen_signal_ids: Set[str]) -> bool:
    """Idempotency gate. Do not open the same signal twice."""
    if signal_id in seen_signal_ids:
        return False
    seen_signal_ids.add(signal_id)
    return True


def latest_price_map_from_opportunities(opps: Iterable[Opportunity]) -> Dict[Tuple[str, str], float]:
    """Build quick lookup for latest PM outcome price by market/outcome."""
    result: Dict[Tuple[str, str], float] = {}
    for opp in opps:
        if opp.entry_price > 0:
            result[(opp.market_id, opp.outcome_name)] = opp.entry_price
    return result
