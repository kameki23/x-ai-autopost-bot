from datetime import datetime
from zoneinfo import ZoneInfo


def _parse_hm(value: str, default_h: int, default_m: int) -> tuple[int, int]:
    try:
        h, m = value.strip().split(":", 1)
        return int(h), int(m)
    except Exception:
        return default_h, default_m


def current_slot_jst(
    now: datetime | None = None,
    slots: dict | None = None,
    enabled_slots: list[int] | None = None,
    window_minutes: int = 59,
) -> int | None:
    now = now or datetime.now(ZoneInfo("Asia/Tokyo"))
    slots = slots or {"slot1": "09:00", "slot2": "13:00", "slot3": "20:00"}
    enabled = set(enabled_slots or [1, 2, 3])

    candidates = {
        1: _parse_hm(str(slots.get("slot1", "09:00")), 9, 0),
        2: _parse_hm(str(slots.get("slot2", "13:00")), 13, 0),
        3: _parse_hm(str(slots.get("slot3", "20:00")), 20, 0),
    }

    for slot, (h, m) in candidates.items():
        if slot not in enabled:
            continue
        if now.hour == h and 0 <= (now.minute - m) <= max(0, window_minutes):
            return slot
    return None
