from datetime import datetime
from zoneinfo import ZoneInfo


def current_slot_jst(now: datetime | None = None) -> int | None:
    now = now or datetime.now(ZoneInfo("Asia/Tokyo"))
    hm = now.hour * 100 + now.minute
    if 900 <= hm < 1300:
        return 1
    if 1300 <= hm < 2000:
        return 2
    if 2000 <= hm < 2359:
        return 3
    return None
