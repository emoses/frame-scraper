import sqlite3
from typing import List
import logging

LOGGER = logging.Logger(__name__)

class Db:
    def __init__(self, filename: str):
        self.conn = sqlite3.connect(filename)
        self._migrate()

    def _migrate(self):
        self.conn.execute('''CREATE TABLE IF NOT EXISTS uploaded(
        id INTEGER PRIMARY KEY,
        filename TEXT NOT NULL,
        uploaded_at TEXT)''')

    def add(self, filename: str):
        res = self.conn.execute('''INSERT INTO uploaded
        (filename, uploaded_at)
        VALUES (?, datetime('now'))''', (filename,))
        self.conn.commit()

        LOGGER.debug("Added name %s: %r", filename, res)

    def list(self) -> List[str]:
        res = self.conn.execute('''SELECT filename
        FROM uploaded
        ORDER BY uploaded_at ASC''')
        return [f[0] for f in res.fetchall()]

    def delete(self, names: List[str]) -> None:
        if len(names) == 0:
            return
        self.conn.execute(f"DELETE FROM uploaded WHERE filename IN ({','.join('?'*len(names))})", names)
        self.conn.commit()
