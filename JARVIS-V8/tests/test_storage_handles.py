"""Every SQLite store must close its connection (Windows locks open files)."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core import audit, config, conversation, workspace


class StorageHandleTests(unittest.TestCase):
    def test_stores_close_every_connection(self):
        opened = []
        real_connect = sqlite3.connect

        def tracking_connect(*args, **kwargs):
            connection = real_connect(*args, **kwargs)
            opened.append(connection)
            return connection

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(config, "APP_DIR", root), patch.object(config, "CONFIG_PATH", root / "c.json"), \
                 patch.object(workspace, "APP_DIR", root), patch.object(audit, "APP_DIR", root), \
                 patch("sqlite3.connect", side_effect=tracking_connect):
                workspace.save("Projects", "School", "Chapter one")
                self.assertEqual(len(workspace.records("Projects")), 1)
                conversation.remember_exchange("hello", "hi")
                conversation.recent_messages(4)
                audit.record("wait", "1", "verified")
                audit.recent(5)
                with self.assertRaises(RuntimeError):
                    with workspace.connect() as db:
                        db.execute("INSERT INTO records(category,title,body) VALUES ('x','y','z')")
                        raise RuntimeError("boom")
                self.assertEqual(len(workspace.records("x")), 0, "failed transaction must roll back")
            self.assertGreaterEqual(len(opened), 7)
            for connection in opened:
                with self.assertRaises(sqlite3.ProgrammingError):
                    connection.execute("SELECT 1")


if __name__ == "__main__":
    unittest.main()
