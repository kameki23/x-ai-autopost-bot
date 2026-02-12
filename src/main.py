import argparse
import json
import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from .collector import collect_candidates
from .extractor import extract_article
from .ranker import rank_article
from .scheduler import current_slot_jst
from .store import Store
from .thumbnail import generate_thumbnail
from .utils import jaccard_similarity, now_jst, setup_logging, sha256_text
from .writer import write_three_posts
from .x_client import XClient

logger = logging.getLogger(__name__)


def _load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _cooldown_ok(store: Store, cooldown_seconds: int) -> bool:
    t = store.last_post_time()
    if not t:
        return True
    dt = datetime.fromisoformat(t)
    return (now_jst() - dt).total_seconds() >= cooldown_seconds


def _is_near_duplicate(store: Store, candidate: dict, days: int) -> bool:
    if store.recently_posted_hash(candidate["article_hash"], days):
        return True
    for old in store.recent_posts(days):
        if old["article_url"] == candidate["article_url"]:
            return True
        if old["person"] and candidate.get("person") and old["person"] == candidate.get("person"):
            return True
        if jaccard_similarity(old["topic"] or "", candidate.get("topic") or "") >= 0.8:
            return True
    return False


def build_queue(store: Store, sources: dict, people: list[dict], rules: dict, dedupe_days: int) -> None:
    candidates = collect_candidates(sources)
    logger.info("Collected %s candidates", len(candidates))

    for c in candidates:
        art = extract_article(c["url"])
        if not art:
            continue
        art["title"] = art.get("title") or c.get("title")
        if len(art.get("body", "")) < 400:
            continue

        score, topic, person, image_source = rank_article(art, people, rules.get("themes", []))
        art_hash = sha256_text(art["url"])
        row = {
            "article_hash": art_hash,
            "article_url": art["url"],
            "title": art["title"],
            "body": art["body"],
            "topic": topic,
            "person": person,
            "image_url": art.get("image_url"),
            "image_source": image_source,
            "score": score,
            "selected_at": now_jst().isoformat(),
        }
        if _is_near_duplicate(store, row, dedupe_days):
            continue
        store.queue_upsert(row)


def run(slot_override: int | None = None) -> int:
    load_dotenv()
    setup_logging(os.getenv("LOG_LEVEL", "INFO"))

    store = Store(os.getenv("DB_PATH", "data/bot.sqlite3"))
    x = XClient()
    rules = _load_json("config/rules.json")
    sources = _load_json("config/sources.json")
    people = _load_json("config/people.json")

    try:
        slot = slot_override or current_slot_jst()
        if slot is None:
            logger.info("Outside slot window (JST). Skip.")
            return 0

        if not _cooldown_ok(store, int(os.getenv("COOLDOWN_SECONDS", "600"))):
            logger.info("Cooldown active. Skip posting.")
            return 0

        build_queue(store, sources, people, rules, int(os.getenv("DEDUPE_DAYS", "14")))
        best = store.best_queue_candidate()
        if not best:
            logger.warning("No queue candidate found.")
            return 0

        article = dict(best)
        posts = write_three_posts(article, rules)
        text = posts[slot]

        # Safety switch: face/person image usage only when ALLOW_IMAGE=true
        allow_image = os.getenv("ALLOW_IMAGE", "false").lower() == "true"
        thumb = generate_thumbnail(article, allow_image=allow_image, out_path=f"data/thumb_slot{slot}.jpg")

        media_id = x.upload_media_chunked(thumb)
        tweet_id = x.create_post(text, media_id=media_id)

        store.save_post(
            article_url=article["article_url"],
            article_hash=article["article_hash"],
            topic=article.get("topic"),
            person=article.get("person"),
            slot=slot,
            text=text,
            tweet_id=tweet_id,
            image_source=article.get("image_source") if allow_image else "no-face-card",
        )
        logger.info("Slot%s posted. tweet_id=%s", slot, tweet_id)
        return 0
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Fatal run error: %s", exc)
        return 1
    finally:
        store.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="X AI case bot")
    parser.add_argument("--slot", type=int, choices=[1, 2, 3], default=None, help="force slot")
    args = parser.parse_args()
    raise SystemExit(run(slot_override=args.slot))


if __name__ == "__main__":
    main()
