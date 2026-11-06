"""Read-only deterministic transcript comparison."""
from dataclasses import dataclass
from difflib import SequenceMatcher
from hashlib import sha256

@dataclass(frozen=True)
class TranscriptDiff:
    original_sha256: str
    candidate_sha256: str
    original_utf16_units: int
    candidate_utf16_units: int
    original_provenance: str
    candidate_provenance: str
    identical: bool
    changes: tuple
    status: str = "REVIEW_REQUIRED_NOT_AUTHORIZED"

def compare_transcripts(*, original, candidate, original_provenance, candidate_provenance):
    """Compare exact text and return non-equal word spans; never mutate sources."""
    if any(type(s) is not str or not s.strip() for s in (original, candidate)):
        raise ValueError("Both complete transcripts are required")
    if any(type(p) is not str or not p.strip() for p in (original_provenance, candidate_provenance)) or original_provenance == candidate_provenance:
        raise ValueError("Distinct source provenance required")
    a, b = original.split(), candidate.split()
    changes = tuple(op for op in SequenceMatcher(None, a, b, autojunk=False).get_opcodes() if op[0] != 'equal')
    return TranscriptDiff(
        original_sha256=sha256(original.encode()).hexdigest(),
        candidate_sha256=sha256(candidate.encode()).hexdigest(),
        original_utf16_units=len(original.encode('utf-16-le')) // 2,
        candidate_utf16_units=len(candidate.encode('utf-16-le')) // 2,
        original_provenance=original_provenance,
        candidate_provenance=candidate_provenance,
        identical=original == candidate,
        changes=changes,
    )
