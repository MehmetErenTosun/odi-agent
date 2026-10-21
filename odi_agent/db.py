import sqlite3
from pathlib import Path

from odi_agent.seed import DEFAULT_DB_PATH


def connect_readonly(db_path=DEFAULT_DB_PATH):
    """Yazmaya izin vermeyen bağlantı açar; ajan yalnızca okuma sorgusu çalıştırır."""
    db_path = Path(db_path).resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"{db_path} yok; önce: python -m odi_agent.seed")
    conn = sqlite3.connect(f"{db_path.as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn
