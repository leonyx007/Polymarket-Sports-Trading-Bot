"""Append-only JSONL journal helpers for trading audit logs."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


def append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


class TradeJournal:
    """Centralized writer for all trading events."""

    def __init__(self, base_dir: str = "data/trading") -> None:
        self.base = Path(base_dir)
        self.paths = {
            "signals": self.base / "signals.jsonl",
            "orders": self.base / "orders.jsonl",
            "fills": self.base / "fills.jsonl",
            "positions": self.base / "positions.jsonl",
            "risk": self.base / "risk_events.jsonl",
        }

    def log_signal(self, payload: Dict[str, Any]) -> None:
        append_jsonl(self.paths["signals"], payload)

    def log_order(self, payload: Dict[str, Any]) -> None:
        append_jsonl(self.paths["orders"], payload)

    def log_fill(self, payload: Dict[str, Any]) -> None:
        append_jsonl(self.paths["fills"], payload)

    def log_position(self, payload: Dict[str, Any]) -> None:
        append_jsonl(self.paths["positions"], payload)

    def log_risk(self, payload: Dict[str, Any]) -> None:
        append_jsonl(self.paths["risk"], payload)

    def load_entries(self, entry_type: str) -> List[Dict[str, Any]]:
        path = self.paths.get(entry_type)
        if path is None:
            return []
        return read_jsonl(path)

    def load_seen_entry_signal_ids(self) -> set[str]:
        seen: set[str] = set()
        for row in self.load_entries("orders"):
            if row.get("order_type") == "ENTRY" and row.get("signal_id"):
                seen.add(str(row["signal_id"]))
        return seen
