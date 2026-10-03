"""Offline conformance assertions. No HTTP client, service, ledger or payment code."""
import base64
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from jsonschema import Draft202012Validator, FormatChecker
import rfc8785

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 3, 12, tzinfo=timezone.utc)


def require(condition, code):
    if not condition:
        raise ValueError(code)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate_key")
        result[key] = value
    return result


def strict_loads(data):
    if isinstance(data, bytes):
        data = data.decode("utf-8", errors="strict")
    def invalid_constant(value):
        raise ValueError("non_finite_number")
    value = json.loads(data, object_pairs_hook=unique_object, parse_constant=invalid_constant)
    # JCS also rejects integers outside the interoperable range and invalid Unicode.
    rfc8785.dumps(value)
    return value


def load(path):
    return strict_loads(Path(path).read_text(encoding="utf-8"))


def canonical(value):
    return rfc8785.dumps(value)


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def instant(value):
    require(value.endswith("Z"), "timestamp_not_utc")
    return datetime.fromisoformat(value[:-1] + "+00:00")


def b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def unb64(value):
    require(bool(value) and "=" not in value, "invalid_base64url")
    try:
        result = base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
    except Exception as exc:
        raise ValueError("invalid_base64url") from exc
    require(b64(result) == value, "noncanonical_base64url")
    return result


def validator():
    schema = load(ROOT / "schemas/0.1/protocol.schema.json")
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate(document):
    errors = list(validator().iter_errors(document))
    require(not errors, "schema_invalid")
    canonical(document)
    return document


def semantic(document):
    """Single-document assertions; cannot establish external truth or authority."""
    d = document
    k = d.get("kind")
    if "payload" in d:
        return semantic(d["payload"])
    if "observed_at" in d:
        require(instant(d["observed_at"]) <= instant(d["issued_at"]), "observation_after_issue")
    if k == "Offer":
        require(instant(d["valid_until"]) > instant(d["observed_at"]), "offer_time_order")
    elif k == "Delta":
        require(d["through"] - d["from_sequence"] + 1 == len(d["changes"]), "sequence_gap")
        require(all(c["seq"] == d["from_sequence"] + i for i, c in enumerate(d["changes"])), "sequence_gap")
        for c in d["changes"]:
            if c["action"] == "upsert":
                require(c["offer_id"] == c["offer"]["id"] and c["revision"] == c["offer"]["revision"], "change_identity")
                require(c["offer"]["catalog_id"] == d["catalog_id"], "catalog_mismatch")
                semantic(c["offer"])
    elif k == "SnapshotPart":
        ids = [o["id"] for o in d["offers"]] + [t["offer_id"] for t in d["tombstones"]]
        require(len(ids) == len(set(ids)), "duplicate_offer")
        for o in d["offers"]:
            require(o["catalog_id"] == d["catalog_id"], "catalog_mismatch")
            semantic(o)
    elif k == "CatalogManifest":
        require(d["oldest_sequence"] <= d["head"] + 1, "invalid_retention_boundary")
    elif k == "SearchQuery":
        for f in d["hard_filters"]:
            check_filter(f)
        require(set(d["select"]) <= {"id", "title", "price", "attributes", "delivery_regions", "seller_id"}, "unsupported_select")
    elif k == "SearchResult":
        require(not d["failures"] or d["partial"], "hidden_partial_failure")
        require(d["coverage"]["complete_for_declared_sources"] or d["partial"], "hidden_incomplete_coverage")
        ids = [c["offer"]["id"] for c in d["candidates"]]
        require(len(ids) == len(set(ids)), "duplicate_candidate")
        for c in d["candidates"]:
            semantic(c["offer"])
    elif k == "Quote":
        amounts = [d[key] for key in ["subtotal", "delivery", "tax", "discount", "merchant_total"]]
        require(len({(m["currency"], m["exponent"]) for m in amounts}) == 1, "currency_mismatch")
        total = d["subtotal"]["amount"] + d["delivery"]["amount"] + d["tax"]["amount"] - d["discount"]["amount"]
        require(total == d["merchant_total"]["amount"], "quote_total_mismatch")
        require(not d["delivered_total_known"] or not d["unknown_costs"], "unknown_delivered_cost")
        require(instant(d["expires_at"]) > instant(d["issued_at"]), "invalid_expiry")
    elif k == "Authorization":
        require("order_create" not in d["actions"] or "offer_id" in d, "authorization_offer_scope")
        require("order_create" not in d["actions"] or "destination_ref" in d, "authorization_destination_scope")
        require(not ({"cancel", "refund_request"} & set(d["actions"])) or "order_id" in d, "authorization_order_scope")
        require(instant(d["expires_at"]) > instant(d["issued_at"]), "invalid_expiry")
    elif k == "OperationStatus":
        require((d["state"] == "succeeded") == ("result_ref" in d), "operation_result_state")
    elif k == "ServiceQuote":
        require(d["charge"]["asset"] == d["max_charge"]["asset"], "asset_mismatch")
        require(int(d["charge"]["units"]) <= int(d["max_charge"]["units"]), "service_budget_exceeded")
    elif k == "FeeSchedule":
        require(instant(d["valid_until"]) > instant(d["valid_from"]), "invalid_expiry")
    elif k == "KeyDescriptor":
        require(instant(d["valid_until"]) > instant(d["valid_from"]), "invalid_expiry")
    elif k == "SalesObservation":
        require(instant(d["period_end"]) > instant(d["period_start"]), "invalid_period")
        require(d["returns"] <= d["count"], "returns_exceed_count")
    elif k == "BuyerReview":
        require((d["revision"] > 1) == ("previous_review_digest" in d), "review_revision_link")
    elif k == "ClaimCheck":
        require((d["state"] == "concluded") == ("conclusion" in d), "claim_conclusion_state")
    elif k == "ModerationDecision":
        require((d["revision"] > 1) == ("previous_decision" in d), "decision_revision_link")
    elif k == "Appeal":
        require((d["state"] == "accepted") == ("replacement_decision" in d), "appeal_replacement")
    elif k == "RegistryOperation":
        action = d["action"]
        present = set(d) & {"revision", "manifest_url", "commitment", "lease_expires_at"}
        wanted = {"register": {"revision", "manifest_url", "commitment", "lease_expires_at"},
                  "publish": {"revision", "manifest_url", "commitment"},
                  "renew": {"lease_expires_at"}, "revoke": set()}[action]
        require(present == wanted, "registry_action_fields")
        if action == "register":
            require(d["expected_revision"] == 0 and d["revision"] == 1, "registry_revision")
        if action == "publish":
            require(d["revision"] == d["expected_revision"] + 1, "registry_revision")
    return d


FILTERS = {
    "price.amount": (int, {"eq", "gte", "lte"}),
    "attributes.ram_gb": (int, {"eq", "in", "gte", "lte"}),
    "attributes.mass_g": (int, {"eq", "gte", "lte"}),
    "attributes.storage_gb": (int, {"eq", "in", "gte", "lte"}),
    "attributes.screen_mm": (int, {"eq", "gte", "lte"}),
    "condition": (str, {"eq", "in"}), "delivery_regions": (str, {"in"}),
}


def check_filter(f):
    require(f["field"] in FILTERS, "unsupported_filter")
    typ, ops = FILTERS[f["field"]]
    require(f["op"] in ops, "unsupported_operator")
    v = f["value"]
    values = v if f["op"] == "in" and isinstance(v, list) else [v]
    require((f["op"] == "in") == isinstance(v, list), "filter_value_shape")
    require(bool(values) and all(type(x) is typ for x in values), "filter_value_type")
    if f["field"] == "condition":
        require(all(x in {"new", "refurbished", "used"} for x in values), "condition_value")


def filter_result(offer, f, currency, currency_exponent=2):
    check_filter(f)
    if f["field"] == "price.amount" and (offer["price"]["currency"], offer["price"]["exponent"]) != (currency, currency_exponent):
        return "unknown"
    value = offer
    for key in f["field"].split("."):
        if not isinstance(value, dict) or key not in value or value[key] is None:
            return "unknown"
        value = value[key]
    target, op = f["value"], f["op"]
    if op == "in":
        ok = bool(set(value) & set(target)) if isinstance(value, list) else value in target
    elif op == "eq":
        ok = value == target
    elif op == "gte":
        ok = value >= target
    else:
        ok = value <= target
    return "match" if ok else "no_match"


def sign(payload, private_key, kid):
    header = {"alg": "Ed25519", "kid": kid, "typ": "amp+jws"}
    signing_input = b64(canonical(header)) + "." + b64(canonical(payload))
    return {"payload": payload, "jws": signing_input + "." + b64(private_key.sign(signing_input.encode("ascii")))}


def verify(envelope, trusted_key, role, now=NOW):
    validate(envelope)
    validate(trusted_key)
    semantic(trusted_key)
    header64, payload64, signature64 = envelope["jws"].split(".")
    raw_header, raw_payload = unb64(header64), unb64(payload64)
    header = strict_loads(raw_header)
    require(isinstance(header, dict) and set(header) == {"alg", "kid", "typ"}, "header_members")
    require(header["alg"] == "Ed25519" and header["typ"] == "amp+jws", "signature_algorithm")
    require(raw_header == canonical(header), "noncanonical_header")
    require(raw_payload == canonical(envelope["payload"]), "payload_mismatch")
    require(header["kid"] == trusted_key["id"], "untrusted_key")
    require(trusted_key["status"] == "active", "revoked_key")
    require(instant(trusted_key["valid_from"]) <= now < instant(trusted_key["valid_until"]), "key_expired")
    require(role in trusted_key["roles"], "key_role")
    bindings = {"CatalogManifest": ("publisher", "publisher"), "Delta": ("publisher", "publisher"),
                "Quote": ("checkout", "seller_id"), "EvidenceStatement": ("evidence", "issuer"),
                "ReviewEligibility": ("evidence", "issuer"), "BuyerReview": ("review", "buyer_subject"),
                "ModerationDecision": ("community", "community")}
    payload = envelope["payload"]
    require(payload["kind"] in bindings, "unsupported_fixture_signing_role")
    expected_role, owner_field = bindings[payload["kind"]]
    require(role == expected_role, "document_signing_role")
    require(payload[owner_field] == trusted_key["owner"], "signer_owner_binding")
    require(instant(payload["issued_at"]) <= now, "document_not_yet_issued")
    require(instant(trusted_key["valid_from"]) <= instant(payload["issued_at"]) < instant(trusted_key["valid_until"]), "key_not_valid_at_issue")
    pub = Ed25519PublicKey.from_public_bytes(unb64(trusted_key["jwk"]["x"]))
    pub.verify(unb64(signature64), f"{header64}.{payload64}".encode("ascii"))
    semantic(envelope["payload"])
    return envelope["payload"]


def eligible_offers(query, offers, now=NOW):
    """Finite fixture set only: not a text engine or proof of network coverage."""
    validate(query)
    semantic(query)
    for offer in offers:
        validate(offer)
        semantic(offer)
    return sorted([o["id"] for o in offers
        if o["category_profile"] == query["category_profile"] and instant(o["issued_at"]) <= now < instant(o["valid_until"])
        and query["destination_region"] in o["delivery_regions"]
        and (o["price"]["currency"], o["price"]["exponent"]) == (query["currency"], query["currency_exponent"])
        and all(filter_result(o, f, query["currency"], query["currency_exponent"]) == "match" for f in query["hard_filters"])])


def check_presentation(statement, audience, nonce, now=NOW):
    validate(statement)
    semantic(statement)
    require(instant(statement["issued_at"]) <= now, "document_not_yet_issued")
    require(statement["audience"] == audience and statement["nonce"] == nonce, "presentation_binding")
    require(now < instant(statement["expires_at"]), "presentation_expired")


def check_order(request, quote, auth, now=NOW, *, committed_amount=0, committed_quantity=0):
    """First-dispatch assertions; committed totals come from a trusted external ledger."""
    for d in [request, quote, auth]:
        validate(d)
        semantic(d)
        require(instant(d["issued_at"]) <= now, "document_not_yet_issued")
    require(request["network_id"] == quote["network_id"] == auth["network_id"], "network_binding")
    require(request["quote_id"] == quote["id"] and request["quote_sha256"] == digest(quote), "quote_binding")
    require(request["authorization_id"] == auth["id"], "authorization_binding")
    require(request["seller_id"] == quote["seller_id"] == auth["seller_id"], "seller_binding")
    require(quote["checkout_operator"] == auth["checkout_operator"], "operator_binding")
    require("order_create" in auth["actions"], "action_not_authorized")
    require(quote["offer_id"] == auth["offer_id"], "offer_binding")
    require(quote["destination_ref"] == auth["destination_ref"], "destination_binding")
    if "delivery_deadline" in auth:
        require(instant(quote["delivery_by"]) <= instant(auth["delivery_deadline"]), "delivery_deadline_exceeded")
    require(now < instant(quote["expires_at"]) and now < instant(auth["expires_at"]), "quote_or_permission_expired")
    require(quote["terms_sha256"] == auth["terms_sha256"], "terms_binding")
    require(request["quantity"] == quote["quantity"] <= auth["max_quantity"], "quantity_binding")
    require(request["expected_total"] == quote["merchant_total"], "expected_total_mismatch")
    total, limit = quote["merchant_total"], auth["limit"]
    require((total["currency"], total["exponent"]) == (limit["currency"], limit["exponent"]), "currency_mismatch")
    require(total["amount"] <= limit["amount"], "budget_exceeded")
    require(type(committed_amount) is int and type(committed_quantity) is int
            and committed_amount >= 0 and committed_quantity >= 0, "invalid_usage_context")
    require(total["amount"] + committed_amount <= limit["amount"], "aggregate_budget_exceeded")
    require(request["quantity"] + committed_quantity <= auth["max_quantity"], "aggregate_quantity_exceeded")
    require(quote["delivered_total_known"] and not quote["unknown_costs"], "unknown_delivered_cost")


def assemble_snapshot(manifest, snapshot, parts, previous=None, now=NOW):
    for d in [manifest, snapshot]:
        validate(d)
        semantic(d)
    require(digest(snapshot) == manifest["snapshot_sha256"], "snapshot_digest")
    require(snapshot["catalog_id"] == manifest["catalog_id"] and snapshot["epoch"] == manifest["epoch"], "snapshot_context")
    require(snapshot["through"] <= manifest["head"], "snapshot_ahead")
    require(snapshot["through"] + 1 >= manifest["oldest_sequence"], "snapshot_handoff_gap")
    require(instant(snapshot["expires_at"]) > now, "snapshot_expired")
    if previous is not None:
        require(previous["catalog_id"] == manifest["catalog_id"], "catalog_mismatch")
        require(previous["seller_id"] == manifest["seller_id"] and
                previous["category_profile"] == manifest["category_profile"], "catalog_identity_change")
        if previous["epoch"] == snapshot["epoch"]:
            require(snapshot["through"] >= previous["through"], "snapshot_rollback")
    require(set(parts) == {p["url"] for p in snapshot["parts"]}, "incomplete_snapshot")
    require(len(parts) == len(snapshot["parts"]), "duplicate_part")
    records, revisions = {}, {}
    for ref in snapshot["parts"]:
        part = parts[ref["url"]]
        validate(part)
        semantic(part)
        require(digest(part) == ref["sha256"], "part_digest")
        require((part["catalog_id"], part["epoch"], part["snapshot_id"], part["through"]) ==
                (snapshot["catalog_id"], snapshot["epoch"], snapshot["id"], snapshot["through"]), "part_context")
        for offer in part["offers"]:
            require(offer["id"] not in revisions, "duplicate_offer")
            require(offer["seller_id"] == manifest["seller_id"], "seller_binding")
            require(offer["category_profile"] == manifest["category_profile"], "profile_binding")
            records[offer["id"]] = deepcopy(offer)
            revisions[offer["id"]] = offer["revision"]
        for tombstone in part["tombstones"]:
            require(tombstone["offer_id"] not in revisions, "duplicate_offer")
            revisions[tombstone["offer_id"]] = tombstone["revision"]
    if previous is not None:
        require(all(revisions.get(k, 0) >= rev for k, rev in previous["revisions"].items()), "snapshot_revision_rollback")
        for key, rev in previous["revisions"].items():
            if revisions[key] == rev:
                require(previous["records"].get(key) == records.get(key), "snapshot_revision_conflict")
    return {"catalog_id": manifest["catalog_id"], "seller_id": manifest["seller_id"],
            "publisher": manifest["publisher"], "category_profile": manifest["category_profile"],
            "epoch": snapshot["epoch"], "through": snapshot["through"],
            "records": records, "revisions": revisions, "seen": {}}


def apply_delta(state, delta):
    """Pure fixture oracle: returns a new state; caller retains old state on error."""
    validate(delta)
    semantic(delta)
    require((state["catalog_id"], state["epoch"]) == (delta["catalog_id"], delta["epoch"]), "stream_context")
    require(state["publisher"] == delta["publisher"], "publisher_binding")
    result = deepcopy(state)
    for c in delta["changes"]:
        seq = c["seq"]
        if seq <= result["through"]:
            require(result["seen"].get(seq) == digest(c), "conflicting_or_unverifiable_replay")
            continue
        require(seq == result["through"] + 1, "sequence_gap")
        key = c["offer_id"]
        require(c["revision"] > result["revisions"].get(key, 0), "revision_rollback")
        if c["action"] == "upsert":
            require(c["offer"]["seller_id"] == state["seller_id"], "seller_binding")
            require(c["offer"]["category_profile"] == state["category_profile"], "profile_binding")
            result["records"][key] = deepcopy(c["offer"])
        else:
            result["records"].pop(key, None)
        result["revisions"][key] = c["revision"]
        result["through"] = seq
        result["seen"][seq] = digest(c)
    return result


def same_intention(original, retry):
    require(original["operation_id"] == retry["operation_id"], "different_operation")
    require(digest(original) == digest(retry), "idempotency_conflict")


def active_registration(registration, checkpoint, now=NOW):
    require(registration["checkpoint_id"] == checkpoint["id"], "checkpoint_binding")
    require((registration["network_id"], registration["registry_id"]) ==
            (checkpoint["network_id"], checkpoint["registry_id"]), "network_binding")
    require(checkpoint["finality"] == "finalized", "unverified_checkpoint")
    require(registration["state"] == "active" and now < instant(registration["lease_expires_at"]), "inactive_registration")
