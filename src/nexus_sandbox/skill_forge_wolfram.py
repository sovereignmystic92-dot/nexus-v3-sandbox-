"""Offline plugin-derived Skill Forge pilot. No network or provider writes."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
import sqlite3
from pathlib import Path

VERSION = "nexus.skill.v0.1"
PILOT_SKILL_VERSION = "0.1.0"
SKILL_ID = "wolfram.factor-polynomial"
VALIDATOR_ID = "nexus.factor-result-validator"
FIXTURES = {"Factor[x^2 - 1]": 2, "Factor[x^4 - 1]": 4}
FACTOR_TERMS = {
    "x-1": (-1, 1), "-1+x": (-1, 1),
    "x+1": (1, 1), "1+x": (1, 1),
    "x^2+1": (1, 0, 1), "1+x^2": (1, 0, 1),
}
FACTOR_TEXT_SCHEMA = {"type": "string", "maxLength": 4096}
REQUEST_SCHEMA = {"type": "string", "enum": list(FIXTURES)}
EVIDENCE = "tests/unit/test_skill_forge_wolfram.py"
WOLFRAM_FACTOR = "https://reference.wolfram.com/language/ref/Factor.html"
FACTOR_RESULT = re.compile(r"^[\w\s()+*^\-]+$")


def canonical(data: dict) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def manifest(skill_id: str, *, upstream: str, capability: str, dependencies: list[str] | None = None) -> dict:
    validator = skill_id == VALIDATOR_ID
    deps = dependencies or []
    return {
        "contract": WOLFRAM_FACTOR if not validator else "Expand factors and compare coefficients to x^n - 1.",
        "input_schema": ({
            "type": "object", "required": ["request", "result"],
            "properties": {"request": REQUEST_SCHEMA, "result": FACTOR_TEXT_SCHEMA},
        } if validator else REQUEST_SCHEMA),
        "output_schema": ({"type": "boolean"} if validator else FACTOR_TEXT_SCHEMA),
        "fixtures": list(FIXTURES),
        "evidence_refs": [EVIDENCE],
        "adapter_path": "src/nexus_sandbox/skill_forge_wolfram.py",
        "dependency_versions": dict.fromkeys(deps, PILOT_SKILL_VERSION),
        "schema": VERSION, "id": skill_id, "version": PILOT_SKILL_VERSION,
        "upstream": upstream, "capability": capability,
        "dependencies": deps,
        "readiness": "offline-tested-only",
        "provider_permissions": [],
        "provenance": "https://reference.wolfram.com/language/Wolfram/AgentTools/tutorial/QuickStartforAICodingApplications",
        "limitations": "Locally computed fixtures; Wolfram runtime access requires separate verification",
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
        if data.get("readiness") not in ("offline-tested-only", "unavailable") or data.get("provider_permissions") != []:
            raise PermissionError("pilot accepts offline-only skills")
        deps = data.get("dependencies")
        if not isinstance(deps, list) or any(not isinstance(d, str) or not d for d in deps):
            raise ValueError("invalid dependencies")
        for field in ("version", "contract", "adapter_path"):
            if not isinstance(data.get(field), str) or not data[field]:
                raise ValueError(f"invalid manifest {field}")
        for field in ("input_schema", "output_schema"):
            if not isinstance(data.get(field), dict) or not data[field].get("type"):
                raise ValueError(f"invalid manifest {field}")
        for field in ("fixtures", "evidence_refs"):
            if not isinstance(data.get(field), list) or not all(
                isinstance(value, str) and value for value in data[field]
            ) or not data[field]:
                raise ValueError(f"invalid manifest {field}")
        versions = data.get("dependency_versions")
        if not isinstance(versions, dict) or set(versions) != set(deps) or not all(
            isinstance(version, str) and version for version in versions.values()
        ):
            raise ValueError("invalid dependency versions")
        payload = canonical(data)
        digest = hashlib.sha256(payload.encode()).hexdigest()
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO skills VALUES (?,?,?)", (data["id"], digest, payload))
            old = self.db.execute("SELECT digest FROM skills WHERE id=?", (data["id"],)).fetchone()
            if old[0] != digest:
                raise ValueError("conflicting skill identity")
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
        if not isinstance(self.expression, str) or self.expression not in FIXTURES:
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


def factor_locally(expression: str) -> str:
    """Apply difference of squares until the remaining difference is linear."""
    exponent = FIXTURES[expression]
    factors = []
    while exponent > 1:
        exponent //= 2
        power = "x" if exponent == 1 else f"x^{exponent}"
        factors.append(f"({power} + 1)")
    return "*".join(["(x - 1)", *reversed(factors)])


def verify_factorization(expression: str, result: str) -> bool:
    """Multiply the parsed factors and compare exact integer coefficients."""
    parts = result.replace(" ", "").split("*")
    if not 2 <= len(parts) <= 3:
        return False
    coefficients = [1]
    for part in parts:
        factor = FACTOR_TERMS.get(part[1:-1]) if part.startswith("(") and part.endswith(")") else None
        if factor is None:
            return False
        product = [0] * (len(coefficients) + len(factor) - 1)
        for degree, coefficient in enumerate(coefficients):
            for offset, term in enumerate(factor):
                product[degree + offset] += coefficient * term
        coefficients = product
    return coefficients == [-1, *([0] * (FIXTURES[expression] - 1)), 1]


def execute_composed(
    library: SkillLibrary, request: FactorRequest, transport=None, *, approved: bool = False,
) -> dict:
    """Compose local factoring and validation, with optional offline fixture injection."""
    if approved is not True:
        raise PermissionError("explicit offline test approval required")
    if not isinstance(request, FactorRequest):
        raise ValueError("invalid factor request")
    expression = FactorRequest.wolfram_code(request)
    first = library.get(SKILL_ID)
    second = library.get(VALIDATOR_ID)
    if any(skill["readiness"] != "offline-tested-only" or skill["provider_permissions"] != []
           for skill in (first, second)):
        raise PermissionError("skill not approved for offline fixture")
    if any(skill.get("version") != PILOT_SKILL_VERSION for skill in (first, second)):
        raise ValueError("incompatible skill version")
    if (first["dependencies"] or second["dependencies"] != [SKILL_ID]
            or second.get("dependency_versions") != {SKILL_ID: first["version"]}):
        raise ValueError("unresolved or incompatible composition")
    raw = factor_locally(expression) if transport is None else transport(expression)
    result = normalize_wolfram_output(raw)
    if not verify_factorization(expression, result):
        raise ValueError("independent validator rejected output")
    return {"request": expression, "result": result, "validated": True, "skills": [SKILL_ID, VALIDATOR_ID]}
