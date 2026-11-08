"""SQLite helper that always closes connections.

``with sqlite3.connect(...) as db`` only commits or rolls back; it leaves the
file open. On Windows an open handle blocks deleting or replacing the file
(temporary test profiles, backups, uninstall), so every store uses this.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Callable, Iterator


@contextmanager
def managed(opener: Callable[[], sqlite3.Connection]) -> Iterator[sqlite3.Connection]:
    database = opener()
    try:
        yield database
        database.commit()
    except BaseException:
        database.rollback()
        raise
    finally:
        database.close()
