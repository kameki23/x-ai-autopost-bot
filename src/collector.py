import logging
from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup

from .utils import retry

logger = logging.getLogger(__name__)


def collect_candidates(sources: dict) -> list[dict]:
    items: list[dict] = []

    for rss_url in sources.get("rss", []):
        try:
            feed = retry(lambda: feedparser.parse(rss_url))
            for entry in feed.entries[:20]:
                link = entry.get("link")
                if not link:
                    continue
                items.append(
                    {
                        "url": link,
                        "title": entry.get("title", ""),
                        "summary": entry.get("summary", ""),
                    }
                )
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("RSS collection failed: %s (%s)", rss_url, exc)

    for page_url in sources.get("list_pages", []):
        try:
            html = retry(lambda: requests.get(page_url, timeout=20).text)
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.select("a[href]")[:80]:
                href = a.get("href")
                if not href:
                    continue
                url = urljoin(page_url, href)
                if not url.startswith("http"):
                    continue
                text = a.get_text(" ", strip=True)
                if len(text) < 8:
                    continue
                items.append({"url": url, "title": text, "summary": ""})
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("List page collection failed: %s (%s)", page_url, exc)

    # URL dedupe in-memory
    seen = set()
    unique = []
    for it in items:
        if it["url"] in seen:
            continue
        seen.add(it["url"])
        unique.append(it)
    return unique
