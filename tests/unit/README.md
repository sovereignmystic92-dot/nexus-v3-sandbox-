# Local coordinator tests

Run `PYTHONPATH=src python3 -m unittest discover -s tests/unit -v` from the repository root. Twenty-four distinct executable tests exercise local SQLite behavior and structured authority/evidence contracts using temporary synthetic data. Run `python3 tools/validate.py --output local-validation.json` to reproduce the machine-readable report and sample attempts.

Current coverage and limitations are in `docs/authority-and-acceptance.md`. Full acceptance is BLOCKED on unverified host controls. Reciprocal external endpoints, full disk/power failures, concurrent workers and worker fencing are not established. Empty collections and duplicate test IDs cannot produce a successful validation report.
