from __future__ import annotations

import glob
import json
import os
import sqlite3
import subprocess
from pathlib import Path
from typing import Any

from flask import Flask, flash, redirect, render_template, request, url_for

ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"
CONFIG_DIR = ROOT_DIR / "config"
LOGS_DIR = ROOT_DIR / "logs"
DEFAULT_DB_PATH = "data/bot.sqlite3"

CONFIG_FILES = {
    "sources": CONFIG_DIR / "sources.json",
    "people": CONFIG_DIR / "people.json",
    "rules": CONFIG_DIR / "rules.json",
}

SECRET_KEYS = [
    "X_API_KEY",
    "X_API_SECRET",
    "X_API_KEY_SECRET",
    "X_ACCESS_TOKEN",
    "X_ACCESS_TOKEN_SECRET",
]
ENV_EDIT_KEYS = [
    "X_API_KEY",
    "X_API_SECRET",
    "X_API_KEY_SECRET",
    "X_ACCESS_TOKEN",
    "X_ACCESS_TOKEN_SECRET",
    "DRY_RUN",
]

app = Flask(__name__)
app.secret_key = os.getenv("WEBAPP_SECRET", "dev-local-webapp-secret")


def read_env_lines() -> list[str]:
    if not ENV_PATH.exists():
        return []
    return ENV_PATH.read_text(encoding="utf-8").splitlines()


def parse_env() -> dict[str, str]:
    env_map: dict[str, str] = {}
    for line in read_env_lines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        env_map[key.strip()] = value.strip()
    return env_map


def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 6:
        return "*" * len(value)
    return f"{value[:3]}{'*' * (len(value) - 6)}{value[-3:]}"


def masked_env(env_map: dict[str, str]) -> dict[str, str]:
    out = dict(env_map)
    for k in SECRET_KEYS:
        if k in out and out[k]:
            out[k] = mask_secret(out[k])
    return out


def bool_from_env(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_db_path(env_map: dict[str, str]) -> Path:
    db_rel = env_map.get("DB_PATH", DEFAULT_DB_PATH)
    return (ROOT_DIR / db_rel).resolve()


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    )
    return cur.fetchone() is not None


def db_stats(db_path: Path) -> dict[str, Any]:
    stats = {
        "posts_count": 0,
        "errors_count": 0,
        "recent_posts": [],
        "error_source": "errors",
    }
    if not db_path.exists():
        return stats

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        if table_exists(conn, "posts"):
            stats["posts_count"] = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
            stats["recent_posts"] = conn.execute(
                """
                SELECT id, posted_at, slot, topic, person, article_url, tweet_id
                FROM posts
                ORDER BY id DESC
                LIMIT 20
                """
            ).fetchall()

        if table_exists(conn, "errors"):
            stats["errors_count"] = conn.execute("SELECT COUNT(*) FROM errors").fetchone()[0]
            stats["error_source"] = "errors"
        elif table_exists(conn, "failed_runs"):
            stats["errors_count"] = conn.execute("SELECT COUNT(*) FROM failed_runs").fetchone()[0]
            stats["error_source"] = "failed_runs"
        else:
            stats["errors_count"] = 0
            stats["error_source"] = "none"
    finally:
        conn.close()
    return stats


def tail_file(path: Path, lines: int = 120) -> str:
    try:
        content = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(content[-lines:])
    except Exception as exc:  # pylint: disable=broad-except
        return f"[read error] {exc}"


def logs_tail() -> list[dict[str, str]]:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    out: list[dict[str, str]] = []
    for file_path in sorted(glob.glob(str(LOGS_DIR / "*.log"))):
        p = Path(file_path)
        out.append({"name": p.name, "content": tail_file(p)})
    return out


def read_json_text(path: Path) -> str:
    if not path.exists():
        return "{}"
    return path.read_text(encoding="utf-8")


def load_configs() -> dict[str, str]:
    return {name: read_json_text(path) for name, path in CONFIG_FILES.items()}


def safe_save_env(new_values: dict[str, str]) -> None:
    lines = read_env_lines()
    seen: set[str] = set()
    updated: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            updated.append(line)
            continue

        key = line.split("=", 1)[0].strip()
        if key in new_values:
            updated.append(f"{key}={new_values[key]}")
            seen.add(key)
        else:
            updated.append(line)

    for key in ENV_EDIT_KEYS:
        if key in new_values and key not in seen:
            updated.append(f"{key}={new_values[key]}")

    ENV_PATH.write_text("\n".join(updated).rstrip() + "\n", encoding="utf-8")


@app.route("/", methods=["GET"])
def index():
    env_map = parse_env()
    db_path = get_db_path(env_map)
    stats = db_stats(db_path)
    return render_template(
        "index.html",
        env_map=env_map,
        env_masked=masked_env(env_map),
        dry_run=bool_from_env(env_map.get("DRY_RUN"), default=True),
        db_path=str(db_path),
        stats=stats,
        configs=load_configs(),
        logs=logs_tail(),
    )


@app.route("/env/save", methods=["POST"])
def save_env():
    env_map = parse_env()

    x_api_secret = request.form.get("X_API_SECRET", "").strip()
    x_api_key_secret = request.form.get("X_API_KEY_SECRET", "").strip()

    new_values = {
        "X_API_KEY": request.form.get("X_API_KEY", "").strip() or env_map.get("X_API_KEY", ""),
        "X_API_SECRET": x_api_secret or x_api_key_secret or env_map.get("X_API_SECRET", ""),
        "X_API_KEY_SECRET": x_api_key_secret or x_api_secret or env_map.get("X_API_KEY_SECRET", ""),
        "X_ACCESS_TOKEN": request.form.get("X_ACCESS_TOKEN", "").strip() or env_map.get("X_ACCESS_TOKEN", ""),
        "X_ACCESS_TOKEN_SECRET": request.form.get("X_ACCESS_TOKEN_SECRET", "").strip() or env_map.get("X_ACCESS_TOKEN_SECRET", ""),
        "DRY_RUN": "true" if request.form.get("DRY_RUN") == "on" else "false",
    }

    safe_save_env(new_values)
    flash(".env updated.", "success")
    return redirect(url_for("index"))


@app.route("/run", methods=["POST"])
def run_manual():
    slot = request.form.get("slot", "auto").strip().lower()

    cmd = ["python", "-m", "src.main"]
    if slot in {"1", "2", "3"}:
        cmd += ["--slot", slot]

    try:
        result = subprocess.run(
            cmd,
            cwd=ROOT_DIR,
            text=True,
            capture_output=True,
            timeout=600,
            check=False,
        )
        output = (
            f"$ {' '.join(cmd)}\n"
            f"exit_code={result.returncode}\n\n"
            f"--- STDOUT ---\n{result.stdout}\n"
            f"--- STDERR ---\n{result.stderr}"
        )
        flash("Manual run finished.", "success" if result.returncode == 0 else "warning")
    except Exception as exc:  # pylint: disable=broad-except
        output = f"$ {' '.join(cmd)}\n[run error] {exc}"
        flash("Manual run failed to start.", "danger")

    env_map = parse_env()
    db_path = get_db_path(env_map)
    stats = db_stats(db_path)
    return render_template(
        "index.html",
        env_map=env_map,
        env_masked=masked_env(env_map),
        dry_run=bool_from_env(env_map.get("DRY_RUN"), default=True),
        db_path=str(db_path),
        stats=stats,
        configs=load_configs(),
        logs=logs_tail(),
        run_output=output,
    )


@app.route("/config/save/<name>", methods=["POST"])
def save_config(name: str):
    if name not in CONFIG_FILES:
        flash("Unknown config name.", "danger")
        return redirect(url_for("index"))

    raw = request.form.get("content", "")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        flash(f"Invalid JSON for {name}: {exc}", "danger")
        return redirect(url_for("index"))

    CONFIG_FILES[name].write_text(json.dumps(parsed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    flash(f"Saved config/{name}.json", "success")
    return redirect(url_for("index"))


if __name__ == "__main__":
    os.chdir(ROOT_DIR)
    app.run(host="127.0.0.1", port=5001, debug=False)
