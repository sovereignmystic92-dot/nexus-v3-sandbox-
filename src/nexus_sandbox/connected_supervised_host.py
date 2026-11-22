"""Opt-in transcript composition with a mandatory retained-receipt readback.

Uses the existing gated host, never lower-level processing primitives. The
trusted caller supplies authenticated source/receipt readers and grants.
No receipt writer, scheduler or independent-review authority is installed.
"""
import copy
import hashlib
import json

from .source_connection_plan import validate_connection_plan
from .transcript_supervised_host import execute_supervised


RECEIPT_SCHEMA = "nexus.connected-supervised-receipt.v1"


def _strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate receipt key")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("nonfinite receipt value")


def _same_execution(retained, current):
    """A create receipt can be reconciled by a later zero-create read-only run."""
    if type(retained) is not dict:
        return False
    writes = retained.get("create_requests")
    if type(writes) is not int or writes not in (0, 1):
        return False
    adjusted = {**retained, "create_requests": current["create_requests"]}
    return json.dumps(adjusted, sort_keys=True, allow_nan=False) == json.dumps(current, sort_keys=True)


def execute_connected_supervised(*, plan, consumer, supervised_kwargs,
                                 read_source_reference, read_retained_receipt):
    """Verify one consumer's source/output/receipt persistence milestone.

    read_source_reference(document_id) freshly returns the exact plan source
    reference. read_retained_receipt(work_key) returns None for confirmed
    absence, or exactly {reference: str, content: bytes}. Errors must propagate,
    never become absence. The host must authenticate scope, custody and reads.

    A first matched output yields PENDING_RECEIPT with receipt_to_retain. The
    caller saves that envelope via its separately authorized durable checkpoint
    path, then re-enters with the SAME plan and journal in read-only mode.
    No automatic receipt write or uncertain-write retry occurs here.
    """
    pinned = copy.deepcopy(plan)
    validate_connection_plan(pinned)
    matches = [item for item in pinned["consumers"] if item["consumer"] == consumer]
    if len(matches) != 1 or type(supervised_kwargs) is not dict:
        raise ValueError("known consumer and explicit supervised arguments required")
    if not callable(read_source_reference) or not callable(read_retained_receipt):
        raise ValueError("fresh source and retained-receipt readers required")
    args = dict(supervised_kwargs)
    source = pinned["source"]
    if (args.get("source_page") != source["document_id"].removeprefix("notion:")
            or args.get("source_sha256") != source["source_sha256"]):
        raise ValueError("supervised source does not match shared plan")
    gate = args.get("analysis_gate")
    if (type(gate) is not dict or type(gate.get("binding")) is not dict
            or gate["binding"].get("run_id") != pinned["mission_id"]):
        raise ValueError("complete analysis gate must bind the shared mission")
    # Callback implementations cannot mutate the pinned arguments between runs.
    for field in ("prepared", "analysis_gate"):
        args[field] = copy.deepcopy(args.get(field))

    def source_check():
        observed = read_source_reference(source["document_id"])
        if type(observed) is not dict or observed != source:
            raise ValueError("fresh source revision readback mismatch")

    original_request = args.get("request")
    if not callable(original_request):
        raise ValueError("authenticated supervised request callback required")
    work = matches[0]
    receipt_checked = False
    prior_retained = None

    def connected_request(operation, payload):
        nonlocal receipt_checked, prior_retained
        # Let execute_supervised validate the complete structural gate and
        # existing journal binding BEFORE even a source-metadata provider read.
        # Its first archive read and each later source check bind the revision.
        if operation == "archive_read":
            source_check()
            if not receipt_checked:
                prior_retained = copy.deepcopy(read_retained_receipt(work["work_key"]))
                receipt_checked = True
        if operation == "cortex_create" and (not receipt_checked or prior_retained is not None):
            raise PermissionError("retained receipt requires read-only reconciliation")
        return original_request(operation, payload)

    args["request"] = connected_request
    execution = execute_supervised(**args)
    base = {"consumer": consumer, "source_key": pinned["source_key"],
            "work_key": work["work_key"], "execution": execution,
            "other_consumers_verified": False, "audit_gate_promoted": False,
            "knowledge_promoted": False}
    if (execution["handoff"]["status"] != "READBACK_MATCHED"
            or execution.get("analysis_evidence_status") != "STRUCTURAL_READBACK_MATCHED"
            or execution.get("execution_mode") != "GATED"):
        return {**base, "status": "BLOCKED", "next_action": execution["handoff"]["next_action"]}
    binding = {"plan_id": pinned["plan_id"], "source": source,
               "source_key": pinned["source_key"], "work_key": work["work_key"],
               "consumer": consumer, "output_name": args["output_name"],
               "expected_owner": args["expected_owner"]}
    envelope = {"schema": RECEIPT_SCHEMA, "binding": binding, "execution": execution}
    retained = read_retained_receipt(work["work_key"])
    if prior_retained is not None and retained != prior_retained:
        raise ValueError("retained receipt changed or disappeared during reconciliation")
    if retained is None:
        source_check()
        return {**base, "status": "PENDING_RECEIPT", "receipt_to_retain": envelope,
                "next_action": "SAVE_THEN_INDEPENDENTLY_READ_RETAINED_RECEIPT"}
    if (type(retained) is not dict or set(retained) != {"reference", "content"}
            or type(retained["reference"]) is not str or not retained["reference"].strip()
            or type(retained["content"]) is not bytes
            or not 0 < len(retained["content"]) <= 1048576):
        raise ValueError("bounded exact retained receipt and identity required")
    saved = json.loads(retained["content"].decode("utf-8"),
                       object_pairs_hook=_strict_object, parse_constant=_reject_constant)
    if (type(saved) is not dict or set(saved) != {"schema", "binding", "execution"}
            or saved["schema"] != RECEIPT_SCHEMA or saved["binding"] != binding
            or not _same_execution(saved["execution"], execution)):
        raise ValueError("retained receipt does not match consumer execution")
    # Read the actual output again after fetching the receipt, through the same
    # guarded host and retained journal. Receipt metadata cannot release a hold.
    fresh_args = {**args, "allow_create": False}
    fresh = execute_supervised(**fresh_args)
    if not _same_execution(execution, fresh):
        raise ValueError("output changed during receipt verification")
    source_check()
    return {**base, "execution": fresh, "status": "CONSUMER_PERSISTENCE_READBACK_MATCHED",
            "receipt_ref": retained["reference"],
            "receipt_sha256": hashlib.sha256(retained["content"]).hexdigest(),
            "next_action": "RETAIN_LINK_AND_APPLY_CONSUMER_REVIEW_AND_PROMOTION_GATES"}
