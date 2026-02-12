import logging

import requests
from bs4 import BeautifulSoup
from readability import Document

from .utils import retry

logger = logging.getLogger(__name__)


def extract_article(url: str) -> dict | None:
    try:
        html = retry(lambda: requests.get(url, timeout=25, headers={"User-Agent": "Mozilla/5.0"}).text)
        doc = Document(html)
        title = doc.short_title() or ""
        content_html = doc.summary(html_partial=True)
        soup = BeautifulSoup(content_html, "html.parser")
        text = soup.get_text("\n", strip=True)
        if len(text) < 300:
            # fallback to full page extraction
            full = BeautifulSoup(html, "html.parser").get_text("\n", strip=True)
            text = full[:10000]
        image_url = None
        img = soup.find("img")
        if img and img.get("src", "").startswith("http"):
            image_url = img["src"]
        return {"url": url, "title": title.strip(), "body": text.strip(), "image_url": image_url}
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Extraction failed: %s (%s)", url, exc)
        return None
