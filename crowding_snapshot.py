"""Persist one point-in-time institutional crowding snapshot.

The production API is read-only. This script is intended for the scheduled
GitHub workflow (and manual maintenance runs), which commits the resulting JSON
back to the repository so revenue revisions and risk changes stay point-in-time.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from policy_engine import (
    CROWDING_HISTORY_FILE,
    CROWDING_WATCHLIST,
    build_crowding_snapshot,
    load_crowding_history,
)


def main() -> None:
    snapshot = build_crowding_snapshot()
    rows = snapshot.get("rows") or []
    if len(rows) != len(CROWDING_WATCHLIST):
        raise RuntimeError(
            f"received {len(rows)}/{len(CROWDING_WATCHLIST)} crowding rows; refusing to persist a partial snapshot"
        )
    history = load_crowding_history()
    snapshots = [
        item for item in history.get("snapshots", [])
        if isinstance(item, dict) and item.get("date") != snapshot["date"]
    ]
    snapshots.append(snapshot)
    snapshots = sorted(snapshots, key=lambda item: str(item.get("date") or ""))[-400:]
    payload = {
        "version": "1.0",
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "benchmark": "SOXX",
        "snapshots": snapshots,
    }
    temporary = CROWDING_HISTORY_FILE.with_suffix(".json.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(temporary, CROWDING_HISTORY_FILE)
    print(f"Saved {snapshot['date']}: {len(rows)} tickers, {len(snapshots)} total snapshots")


if __name__ == "__main__":
    main()
