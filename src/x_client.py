import logging
import os

import requests
from requests_oauthlib import OAuth1

from .utils import retry

logger = logging.getLogger(__name__)


class XClient:
    UPLOAD_URL = "https://upload.twitter.com/1.1/media/upload.json"
    POST_URL = "https://api.twitter.com/2/tweets"

    def __init__(self) -> None:
        self.dry_run = os.getenv("DRY_RUN", "true").lower() != "false"
        api_secret = os.getenv("X_API_SECRET", "") or os.getenv("X_API_KEY_SECRET", "")
        self.auth = OAuth1(
            os.getenv("X_API_KEY", ""),
            api_secret,
            os.getenv("X_ACCESS_TOKEN", ""),
            os.getenv("X_ACCESS_TOKEN_SECRET", ""),
        )

    def _request(self, method: str, url: str, **kwargs):
        def op():
            r = requests.request(method, url, auth=self.auth, timeout=30, **kwargs)
            if r.status_code >= 400:
                raise RuntimeError(f"X API error {r.status_code}: {r.text[:300]}")
            return r

        return retry(op, retries=3)

    def upload_media_chunked(self, image_path: str) -> str | None:
        if self.dry_run:
            logger.info("[DRY_RUN] skip media upload: %s", image_path)
            return None

        total_bytes = os.path.getsize(image_path)
        init = self._request(
            "POST",
            self.UPLOAD_URL,
            data={"command": "INIT", "media_type": "image/jpeg", "total_bytes": total_bytes},
        ).json()
        media_id = init["media_id_string"]

        with open(image_path, "rb") as fh:
            segment = 0
            while True:
                chunk = fh.read(4 * 1024 * 1024)
                if not chunk:
                    break
                self._request(
                    "POST",
                    self.UPLOAD_URL,
                    data={"command": "APPEND", "media_id": media_id, "segment_index": segment},
                    files={"media": chunk},
                )
                segment += 1

        self._request("POST", self.UPLOAD_URL, data={"command": "FINALIZE", "media_id": media_id})
        return media_id

    def create_post(self, text: str, media_id: str | None = None) -> str | None:
        payload = {"text": text}
        if media_id:
            payload["media"] = {"media_ids": [media_id]}

        if self.dry_run:
            logger.info("[DRY_RUN] tweet: %s", text)
            return None

        res = self._request("POST", self.POST_URL, json=payload)
        return res.json().get("data", {}).get("id")
