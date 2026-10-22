# Local coordinator tests

Run `PYTHONPATH=src python3 -m unittest discover -s tests/unit -v` from the repository root. Fourteen executable tests exercise local SQLite behavior using temporary synthetic data. The coverage map and limitations are in `docs/implementation-validation.md`. S06 authority resolution, reciprocal external endpoints, full disk/power failures, concurrency and worker fencing are not established. Empty collections must never be reported as a passing acceptance suite.
