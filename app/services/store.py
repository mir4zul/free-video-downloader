"""Transactional local settings and download history."""
import json
import os
from pathlib import Path
import sqlite3


class Store:
    def __init__(self, path=None):
        root = Path(os.environ.get("FVD_DATA_DIR") or
                    Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "free-video-downloader")
        if path is None:
            root.mkdir(parents=True, exist_ok=True)
            path = root / "state.sqlite3"
        self.db = sqlite3.connect(str(path))
        self.db.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
        self.db.execute("CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, data TEXT)")
        self.db.commit()

    def setting(self, key, default):
        row = self.db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set_setting(self, key, value):
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (key, json.dumps(value)))

    def save(self, task):
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO tasks VALUES (?,?)", (task["id"], json.dumps(task)))

    def tasks(self):
        return [json.loads(row[0]) for row in self.db.execute("SELECT data FROM tasks ORDER BY rowid")]
