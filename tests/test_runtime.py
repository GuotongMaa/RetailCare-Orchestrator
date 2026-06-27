"""Checkpointer concurrency hardening (C5/D12)."""
from retailcare.graph import runtime


def test_checkpoint_connection_uses_wal_and_busy_timeout():
    mode = runtime._conn.execute("PRAGMA journal_mode").fetchone()[0]
    timeout = runtime._conn.execute("PRAGMA busy_timeout").fetchone()[0]
    assert mode.lower() == "wal"
    assert timeout >= 5000
