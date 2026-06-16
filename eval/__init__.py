"""Eval package. Importing any eval.* module runs this first, so we isolate each
eval process in its own SQLite DB (avoids 'readonly database' under concurrent
runs). Respects an externally-set DATABASE_URL (e.g. Postgres)."""
import os
import tempfile

os.environ.setdefault(
    "DATABASE_URL", f"sqlite:///{tempfile.gettempdir()}/rc_eval_{os.getpid()}.db"
)
os.environ.setdefault(
    "CHECKPOINT_DB", f"{tempfile.gettempdir()}/rc_ckpt_{os.getpid()}.db"
)
