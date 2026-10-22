-- Local synthetic harness schema. No cross-service atomicity or worker leases.
PRAGMA foreign_keys = ON;

CREATE TABLE transactions (
    transaction_id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    source_id TEXT NOT NULL,
    source_revision TEXT NOT NULL,
    destination_id TEXT NOT NULL CHECK (destination_id = 'synthetic:output'),
    payload_sha256 TEXT NOT NULL CHECK (length(payload_sha256) = 64),
    source_complete INTEGER NOT NULL CHECK (source_complete IN (0,1)),
    authority_revision TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN
        ('NEW','VALIDATED','ARCHIVED','OUTPUT_CREATED','REGISTERED','VERIFIED')),
    disposition TEXT NOT NULL CHECK (disposition IN ('OPEN','BLOCKED','INCOMPLETE','VERIFIED')),
    version INTEGER NOT NULL DEFAULT 0 CHECK (version >= 0),
    next_action TEXT NOT NULL,
    CHECK ((state = 'VERIFIED' AND disposition = 'VERIFIED') OR
           (state <> 'VERIFIED' AND disposition <> 'VERIFIED'))
);

CREATE TABLE events (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id TEXT NOT NULL REFERENCES transactions(transaction_id),
    prior_state TEXT,
    new_state TEXT NOT NULL,
    recorded_at_utc TEXT NOT NULL,
    evidence_ref TEXT NOT NULL
);

CREATE TABLE artifacts (
    artifact_id TEXT PRIMARY KEY,
    transaction_id TEXT NOT NULL REFERENCES transactions(transaction_id),
    kind TEXT NOT NULL CHECK (kind IN ('archive','output','registry')),
    destination_id TEXT NOT NULL CHECK (destination_id IN ('synthetic:archive','synthetic:output')),
    payload TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL CHECK (length(payload_sha256) = 64),
    UNIQUE(transaction_id, kind)
);

CREATE TABLE attempts (
    attempt_id TEXT PRIMARY KEY,
    transaction_id TEXT NOT NULL REFERENCES transactions(transaction_id),
    envelope_json TEXT NOT NULL
);
