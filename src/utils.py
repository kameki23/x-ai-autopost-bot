import hashlib
import logging
import os
import re
import time
from datetime import datetime
from zoneinfo import ZoneInfo


def setup_logging(level: str = "INFO") -> None:
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("logs/bot.log", encoding="utf-8"),
        ],
    )


def now_jst() -> datetime:
    return datetime.now(ZoneInfo("Asia/Tokyo"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[^\w\sぁ-んァ-ン一-龥]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def token_set(text: str) -> set[str]:
    return set(normalize_text(text).split())


def jaccard_similarity(a: str, b: str) -> float:
    sa, sb = token_set(a), token_set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def retry(operation, retries: int = 3, base_sleep: float = 1.0):
    last_exc = None
    for i in range(retries):
        try:
            return operation()
        except Exception as exc:  # pylint: disable=broad-except
            last_exc = exc
            time.sleep(base_sleep * (2**i))
    raise last_exc
