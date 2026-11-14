"""Local SQLite implementation of the synthetic Cortex transport."""

from contextlib import closing
import json
from pathlib import Path
from sqlite3 import connect
from uuid import uuid4

from nexus_sandbox.cortex_adapter import Module


class SQLiteMemoryTransport:
    def __init__(self, path: Path):
        self.path = Path(path)
        with closing(connect(self.path)) as db, db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS memory_modules (
                    name TEXT PRIMARY KEY NOT NULL,
                    id TEXT NOT NULL UNIQUE,
                    version INTEGER NOT NULL CHECK (version >= 1),
                    content TEXT NOT NULL,
                    dependencies TEXT NOT NULL
                )
            """)

    def get(self, name: str) -> Module | None:
        with closing(connect(self.path)) as db:
            row = db.execute(
                "SELECT id, version, content, dependencies FROM memory_modules WHERE name = ?",
                (name,),
            ).fetchone()
        if row is None:
            return None
        module_id, version, content, encoded_dependencies = row
        dependencies = json.loads(encoded_dependencies)
        if not isinstance(dependencies, list) or not all(isinstance(item, str) for item in dependencies):
            raise ValueError("Invalid stored memory dependencies")
        return Module(module_id, name, version, content, tuple(dependencies))

    def create(self, name: str, content: str, dependencies: tuple[str, ...]) -> None:
        with closing(connect(self.path)) as db, db:
            db.execute(
                "INSERT INTO memory_modules VALUES (?, ?, 1, ?, ?)",
                (name, f"synthetic:module:{uuid4().hex}", content, json.dumps(dependencies)),
            )

    def update(self, name: str, content: str, dependencies: tuple[str, ...]) -> None:
        with closing(connect(self.path)) as db, db:
            updated = db.execute(
                "UPDATE memory_modules SET version = version + 1, content = ?, dependencies = ? WHERE name = ?",
                (content, json.dumps(dependencies), name),
            )
            if updated.rowcount != 1:
                raise KeyError(name)
