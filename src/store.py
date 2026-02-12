import os
import sqlite3
from datetime import timedelta
from typing import Any

from .utils import now_jst


class Store:
    def __init__(self, db_path: str) -> None:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_url TEXT NOT NULL,
                article_hash TEXT NOT NULL,
                topic TEXT,
                person TEXT,
                slot INTEGER NOT NULL,
                text TEXT NOT NULL,
                tweet_id TEXT,
                image_source TEXT,
                posted_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS article_queue (
                article_hash TEXT PRIMARY KEY,
                article_url TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                topic TEXT,
                person TEXT,
                image_url TEXT,
                image_source TEXT,
                score REAL,
                selected_at TEXT NOT NULL
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_posts_posted_at ON posts(posted_at)")
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def recent_posts(self, days: int = 14) -> list[sqlite3.Row]:
        since = (now_jst() - timedelta(days=days)).isoformat()
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM posts WHERE posted_at >= ?", (since,))
        return cur.fetchall()

    def recently_posted_hash(self, article_hash: str, days: int = 14) -> bool:
        since = (now_jst() - timedelta(days=days)).isoformat()
        cur = self.conn.cursor()
        cur.execute(
            "SELECT 1 FROM posts WHERE article_hash = ? AND posted_at >= ? LIMIT 1",
            (article_hash, since),
        )
        return cur.fetchone() is not None

    def queue_upsert(self, item: dict[str, Any]) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO article_queue(article_hash, article_url, title, body, topic, person, image_url,
                                      image_source, score, selected_at)
            VALUES(:article_hash, :article_url, :title, :body, :topic, :person, :image_url,
                   :image_source, :score, :selected_at)
            ON CONFLICT(article_hash) DO UPDATE SET
              article_url=excluded.article_url,
              title=excluded.title,
              body=excluded.body,
              topic=excluded.topic,
              person=excluded.person,
              image_url=excluded.image_url,
              image_source=excluded.image_source,
              score=excluded.score,
              selected_at=excluded.selected_at
            """,
            item,
        )
        self.conn.commit()

    def get_queued_article(self, article_hash: str) -> sqlite3.Row | None:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM article_queue WHERE article_hash = ?", (article_hash,))
        return cur.fetchone()

    def best_queue_candidate(self) -> sqlite3.Row | None:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM article_queue ORDER BY score DESC, selected_at DESC LIMIT 1")
        return cur.fetchone()

    def save_post(
        self,
        article_url: str,
        article_hash: str,
        topic: str,
        person: str,
        slot: int,
        text: str,
        tweet_id: str | None,
        image_source: str | None,
    ) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO posts(article_url, article_hash, topic, person, slot, text, tweet_id, image_source, posted_at)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                article_url,
                article_hash,
                topic,
                person,
                slot,
                text,
                tweet_id,
                image_source,
                now_jst().isoformat(),
            ),
        )
        self.conn.commit()

    def last_post_time(self) -> str | None:
        cur = self.conn.cursor()
        cur.execute("SELECT posted_at FROM posts ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        return row["posted_at"] if row else None
