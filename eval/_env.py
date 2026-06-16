"""Import FIRST in eval entrypoints: isolate each eval process in its own SQLite
DB so concurrent eval/ablation runs never collide (avoids 'readonly database').
Respects an externally-set DATABASE_URL (e.g. Postgres)."""
import os
import tempfile

os.environ.setdefault(
    "DATABASE_URL", f"sqlite:///{tempfile.gettempdir()}/rc_eval_{os.getpid()}.db"
)
