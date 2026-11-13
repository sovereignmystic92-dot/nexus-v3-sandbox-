"""Offline plugin-derived Skill Forge pilot. No network or provider writes."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
import sqlite3
from pathlib import Path

VERSION = "nexus.skill.v0.1"
SKILL_ID = "wolfram.factor-polynomial"
VALIDATOR_ID = "nexus.factor-result-validator"
FACTOR_REQUEST = re.compile(r"^Factor\[x\^([2-9]) - 1\]$")
FACTOR_RESULT = re.compile(r"^[\w\s()+*^\-]+$")


def canonical(data: dict) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def manifest(skill_id: str, *, upstream: str, capability: str, dependencies: list[str] | None = None) -> dict:
    return {
        "schema": VERSION, "id": skill_id, "version": "0.1.0",
        "upstream": upstream, "capability": capability,
        "dependencies": dependencies or [],
        "readiness": "offline-tested-only",
        "provider_permissions": [],
        "provenance": "https://reference.wolfram.com/language/Wolfram/AgentTools/tutorial/QuickStartforAICodingApplications",
        "limitations": "Local adapter and mock transport only; no Wolfram runtime or license transferred",
    }


class SkillLibrary:
    """SQLite-backed append-only identity bindings. Existing IDs cannot silently change."""
    def __init__(self, path: str | Path):
        self.db = sqlite3.connect(str(path))
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("CREATE TABLE IF NOT EXISTS skills (id TEXT PRIMARY KEY, digest TEXT NOT NULL, manifest TEXT NOT NULL)")
        self.db.commit()

    def register(self, data: dict) -> str:
        if data.get("schema") != VERSION or not isinstance(data.get("id"), str) or not data["id"]:
            raise ValueError("invalid skill manifest")
        if data.get("readiness") != "offline-tested-only" or data.get("provider_permissions") != []:
            raise PermissionError("pilot accepts offline-only skills")
        deps = data.get("dependencies")
        if not isinstance(deps, list) or any(not isinstance(d, str) or not d for d in deps):
            raise ValueError("invalid dependencies")
        payload = canonical(data)
        digest = hashlib.sha256(payload.encode()).hexdigest()
        with self.db:
            old = self.db.execute("SELECT digest FROM skills WHERE id=?", (data["id"],)).fetchone()
            if old and old[0] != digest:
                raise ValueError("conflicting skill identity")
            self.db.execute("INSERT OR IGNORE INTO skills VALUES (?,?,?)", (data["id"], digest, payload))
        return digest

    def get(self, skill_id: str) -> dict:
        row = self.db.execute("SELECT manifest FROM skills WHERE id=?", (skill_id,)).fetchone()
        if row is None:
            raise KeyError(skill_id)
        return json.loads(row[0])

    def export(self) -> str:
        rows = self.db.execute("SELECT manifest FROM skills ORDER BY id").fetchall()
        return canonical({"schema": VERSION, "skills": [json.loads(r[0]) for r in rows]})

    def close(self):
        self.db.close()


@dataclass(frozen=True)
class FactorRequest:
    expression: str

    def wolfram_code(self) -> str:
        """Strict bounded subset; never evaluate arbitrary user-supplied code."""
        if not FACTOR_REQUEST.fullmatch(self.expression):
            raise ValueError("unsupported or unsafe expression")
        return self.expression


def normalize_wolfram_output(raw: str) -> str:
    """Deliberate adaptation: strip Wolfram's Out[n]= wrapper, normalize whitespace."""
    if not isinstance(raw, str):
        raise ValueError("invalid output")
    clean = re.sub(r"^Out\[\d+\]\s*=\s*", "", raw.strip())
    clean = " ".join(clean.split())
    if not clean or not FACTOR_RESULT.fullmatch(clean) or len(clean) > 4096:
        raise ValueError("untrusted or malformed provider result")
    return clean


def execute_composed(library: SkillLibrary, request: FactorRequest, transport, *, approved: bool = False) -> dict:
    """Transport is an injected *offline fixture* callback; never a live provider client."""
    if not approved:
        raise PermissionError("explicit offline test approval required")
    first = library.get(SKILL_ID)
    second = library.get(VALIDATOR_ID)
    if first["readiness"] != "offline-tested-only" or second["readiness"] != "offline-tested-only":
        raise PermissionError("skill not approved for offline fixture")
    if second["dependencies"] != [SKILL_ID]:
        raise ValueError("unresolved or incompatible composition")
    expression = request.wolfram_code()
    raw = transport(expression)
    result = normalize_wolfram_output(raw)
    # Independent second skill: exact algebraic identity for the bounded x^4-1 fixture.
    if expression != "Factor[x^4 - 1]" or result.replace(" ", "") not in {
        "(-1+x)*(1+x)*(1+x^2)", "(x-1)*(x+1)*(x^2+1)"
    }:
        raise ValueError("independent validator rejected output")
    return {"request": expression, "result": result, "validated": True, "skills": [SKILL_ID, VALIDATOR_ID]}
