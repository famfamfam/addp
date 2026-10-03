"""Generate the standalone AMP 0.1 structural contract. No network access."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
MAX = 9007199254740991
S = {"type": "string", "minLength": 1, "maxLength": 4096}
URI = {**S, "format": "uri"}
URL = {**URI, "pattern": "^https://"}
TIME = {"type": "string", "format": "date-time", "pattern": "Z$"}
INT = {"type": "integer", "minimum": 0, "maximum": MAX}
POS = {**INT, "minimum": 1}
BOOL = {"type": "boolean"}
DIGEST = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
VERSION = {"const": "0.1"}
EXPONENT = {"type": "integer", "minimum": 0, "maximum": 4}
NETWORK_MESSAGES = {"QuoteRequest", "Quote", "Authorization", "OrderRequest", "Order",
                    "OrderAction", "OrderLookup", "OperationLookup", "OperationStatus"}
EXT = {"type": "object", "propertyNames": {"pattern": "^[a-z0-9]+(?:[.-][a-z0-9]+)+$"}}


def ref(name):
    return {"$ref": f"#/$defs/{name}"}


def enum(*values):
    return {"enum": list(values)}


def arr(item, minimum=0, maximum=10000):
    return {"type": "array", "items": item, "minItems": minimum, "maxItems": maximum}


def obj(fields, optional=()):
    return {"type": "object", "properties": fields,
            "required": [k for k in fields if k not in optional], "additionalProperties": False}


DEFS = {}
MESSAGES = []


def msg(name, fields, optional=()):
    if name in NETWORK_MESSAGES:
        fields = {"network_id": URI, **fields}
    DEFS[name] = obj({"version": VERSION, "kind": {"const": name}, "id": URI,
                      "issued_at": TIME, **fields, "extensions": EXT}, (*optional, "extensions"))
    MESSAGES.append(name)


def build():
    DEFS.clear()
    MESSAGES.clear()
    DEFS["Money"] = obj({"amount": INT, "currency": {"type": "string", "pattern": "^[A-Z]{3}$"},
                         "exponent": EXPONENT})
    DEFS["TokenAmount"] = obj({"asset": URI, "units": {"type": "string", "pattern": "^(0|[1-9][0-9]{0,77})$"}})
    DEFS["Attributes"] = obj({k: {"anyOf": [POS, {"type": "null"}]} for k in
                              ["ram_gb", "mass_g", "storage_gb", "screen_mm"]},
                             ["ram_gb", "mass_g", "storage_gb", "screen_mm"])
    DEFS["Filter"] = obj({"field": S, "op": enum("eq", "in", "gte", "lte"),
                          "value": {"oneOf": [S, INT, arr({"oneOf": [S, INT]}, 1, 100)]}})
    DEFS["ConstraintCheck"] = obj({"field": S, "result": enum("match", "no_match", "unknown", "unsupported"),
                                   "source": URI, "observed_at": TIME})
    DEFS["SourceFailure"] = obj({"source": URI, "code": S})
    DEFS["Coverage"] = obj({"catalogs": arr(URI), "description": S, "complete_for_declared_sources": BOOL})
    DEFS["PartReference"] = obj({"url": URL, "sha256": DIGEST})
    DEFS["Tombstone"] = obj({"offer_id": URI, "revision": POS})
    DEFS["Change"] = {"oneOf": [
        obj({"seq": POS, "action": {"const": "upsert"}, "offer_id": URI, "revision": POS, "offer": ref("Offer")}),
        obj({"seq": POS, "action": {"const": "delete"}, "offer_id": URI, "revision": POS})]}
    DEFS["Line"] = obj({"id": URI, "offer_id": URI, "variant_id": URI, "quantity": POS})
    DEFS["Candidate"] = obj({"offer": ref("Offer"), "indexed_at": TIME,
                             "checks": arr(ref("ConstraintCheck")), "sponsored": BOOL, "lookup_url": URL})
    DEFS["JWK"] = obj({"kty": {"const": "OKP"}, "crv": {"const": "Ed25519"},
                       "x": {"type": "string", "pattern": "^[A-Za-z0-9_-]{43}$"}})
    endpoints = ["search", "quote", "order_create", "operation_lookup", "order_lookup", "order_action", "registry_submit"]
    DEFS["Endpoints"] = obj({k: URL for k in endpoints}, endpoints)

    msg("NetworkDescriptor", {"network_id": URI, "registry_id": URI, "chain_profile": URI,
        "token_asset": URI, "bootstrap_indexes": arr(URL), "profile_status": enum("documentary", "operational"),
        "policy_url": URL, "max_unanchored_seconds": INT})
    msg("Discovery", {"operator": URI, "network_id": URI,
        "roles": arr(enum("publisher", "index", "checkout", "registry_gateway", "evidence", "reputation", "community", "content"), 1),
        "endpoints": ref("Endpoints"), "profiles": arr(S), "required_extensions": arr(S),
        "auth_bindings": arr(URI), "max_request_bytes": POS, "max_response_bytes": POS,
        "idempotency_retention_seconds": POS}, ["idempotency_retention_seconds"])
    msg("Seller", {"name": S, "origin": URL, "publishing_keys": arr(URI, 1), "policy_url": URL})
    msg("Product", {"name": S, "manufacturer": S, "model": S, "category_profile": {"const": "laptops/0.1"}})
    msg("Variant", {"product_id": URI, "name": S, "attributes": ref("Attributes")})
    msg("Offer", {"catalog_id": URI, "seller_id": URI, "product_id": URI, "variant_id": URI,
        "revision": POS, "title": S, "category_profile": {"const": "laptops/0.1"},
        "price": ref("Money"), "condition": enum("new", "refurbished", "used"),
        "attributes": ref("Attributes"), "delivery_regions": arr(S), "observed_at": TIME,
        "valid_until": TIME, "checkout_operator": URI, "lookup_url": URL,
        "platform_id": URI, "fulfillment_provider": URI}, ["platform_id", "fulfillment_provider"])
    msg("CatalogManifest", {"catalog_id": URI, "seller_id": URI, "publisher": URI, "revision": POS,
        "epoch": S, "head": INT, "oldest_sequence": POS, "category_profile": {"const": "laptops/0.1"},
        "snapshot_url": URL, "snapshot_sha256": DIGEST, "changes_url": URL,
        "mirror_urls": arr(URL), "rights_url": URL})
    msg("Snapshot", {"catalog_id": URI, "epoch": S, "through": INT,
        "parts": arr(ref("PartReference"), 1), "expires_at": TIME})
    msg("SnapshotPart", {"catalog_id": URI, "epoch": S, "snapshot_id": URI,
        "through": INT, "offers": arr(ref("Offer")), "tombstones": arr(ref("Tombstone"))})
    msg("Delta", {"catalog_id": URI, "publisher": URI, "epoch": S, "from_sequence": POS,
        "through": POS, "changes": arr(ref("Change"), 1)})
    msg("RegistryCheckpoint", {"network_id": URI, "registry_id": URI, "chain_profile": URI,
        "height": INT, "block_hash": DIGEST, "finality": enum("observed", "finalized", "simulated")})
    msg("CatalogRegistration", {"network_id": URI, "registry_id": URI, "catalog_id": URI,
        "owner": URI, "publishing_keys": arr(URI, 1), "revision": POS, "manifest_url": URL,
        "commitment": DIGEST, "lease_expires_at": TIME, "state": enum("active", "expired", "revoked"),
        "checkpoint_id": URI, "fee_schedule_id": URI})
    msg("RegistryOperation", {"network_id": URI, "registry_id": URI, "operation_id": URI,
        "catalog_id": URI, "action": enum("register", "publish", "renew", "revoke"),
        "expected_revision": INT, "payer": URI, "max_fee": ref("TokenAmount"), "fee_schedule_id": URI,
        "revision": POS, "manifest_url": URL, "commitment": DIGEST, "lease_expires_at": TIME},
        ["revision", "manifest_url", "commitment", "lease_expires_at"])
    msg("IndexDescriptor", {"network_id": URI, "operator": URI, "endpoint": URL,
        "category_profiles": arr(S, 1), "regions": arr(S), "filter_fields": arr(S),
        "ranking_policy": S, "coverage_description": S, "max_limit": POS,
        "freshness_seconds": POS, "service_terms_url": URL})
    msg("SearchQuery", {"network_id": URI, "category_profile": {"const": "laptops/0.1"},
        "currency": {"type": "string", "pattern": "^[A-Z]{3}$"}, "currency_exponent": EXPONENT, "destination_region": S,
        "hard_filters": arr(ref("Filter"), 0, 64), "preferences": arr(S, 0, 32),
        "text": S, "select": arr(S), "limit": {**POS, "maximum": 100}, "cursor": S}, ["text", "cursor"])
    msg("SearchResult", {"query_id": URI, "snapshot_id": URI, "checkpoint_id": URI,
        "coverage": ref("Coverage"), "candidates": arr(ref("Candidate"), 0, 100),
        "partial": BOOL, "failures": arr(ref("SourceFailure")), "next_cursor": S}, ["next_cursor"])
    msg("QuoteRequest", {"seller_id": URI, "offer_id": URI, "offer_revision": POS,
        "quantity": POS, "currency": {"type": "string", "pattern": "^[A-Z]{3}$"},
        "destination_ref": URI})
    msg("Quote", {"seller_id": URI, "checkout_operator": URI, "offer_id": URI, "offer_revision": POS,
        "destination_ref": URI, "quantity": POS, "subtotal": ref("Money"), "delivery": ref("Money"), "tax": ref("Money"),
        "discount": ref("Money"), "merchant_total": ref("Money"), "delivered_total_known": BOOL,
        "unknown_costs": arr(S), "delivery_by": TIME, "terms_sha256": DIGEST,
        "expires_at": TIME, "inventory_reserved": BOOL})
    msg("Authorization", {"buyer_subject": URI, "seller_id": URI, "checkout_operator": URI,
        "actions": arr(enum("order_create", "cancel", "refund_request"), 1),
        "max_quantity": POS, "limit": ref("Money"), "terms_sha256": DIGEST,
        "expires_at": TIME, "credential_ref": URI, "offer_id": URI, "order_id": URI,
        "destination_ref": URI, "delivery_deadline": TIME}, ["offer_id", "order_id", "destination_ref", "delivery_deadline"])
    msg("Attribution", {"referrer": URI, "agreement_id": URI, "referral_id": URI, "disclosed": BOOL})
    msg("OrderRequest", {"operation_id": URI, "seller_id": URI, "quote_id": URI,
        "quote_sha256": DIGEST, "authorization_id": URI, "quantity": POS,
        "expected_total": ref("Money"), "attribution_id": URI}, ["attribution_id"])
    msg("OperationLookup", {"operation_id": URI})
    msg("OrderLookup", {"order_id": URI})
    msg("OperationStatus", {"operation_id": URI, "state": enum("pending", "succeeded", "rejected", "unknown"),
        "request_sha256": DIGEST, "lookup_url": URL, "result_ref": URI, "reason": S}, ["result_ref", "reason"])
    msg("Order", {"seller_id": URI, "checkout_operator": URI, "buyer_subject": URI,
        "revision": POS, "quote_id": URI, "operation_id": URI, "lines": arr(ref("Line"), 1, 1),
        "total": ref("Money"), "order_state": enum("pending", "confirmed", "rejected", "cancelled", "completed"),
        "payment_state": enum("pending", "authorized", "captured", "failed", "voided", "partially_refunded", "refunded"),
        "fulfillment_state": enum("pending", "shipped", "delivered", "failed", "cancelled", "returned"),
        "refund_state": enum("none", "requested", "approved", "rejected", "paid", "failed"),
        "allowed_actions": arr(enum("cancel", "refund_request", "status")), "handoff_url": URL,
        "attribution_id": URI}, ["handoff_url", "attribution_id"])
    msg("OrderAction", {"operation_id": URI, "order_id": URI, "expected_revision": POS,
        "action": enum("cancel", "refund_request"), "reason": S, "authorization_id": URI})
    common_event = {"issuer": URI, "order_id": URI, "line_id": URI, "observed_at": TIME,
        "evidence_level": enum("simulated", "seller_asserted", "provider_attested"), "previous_event": URI}
    msg("PaymentEvent", {**common_event, "state": enum("pending", "authorized", "captured", "failed", "voided", "partially_refunded", "refunded"),
        "amount": ref("Money"), "payment_ref": URI}, ["previous_event"])
    msg("FulfillmentEvent", {**common_event, "state": enum("pending", "shipped", "delivered", "failed", "cancelled", "returned"),
        "fulfillment_ref": URI}, ["previous_event"])
    msg("RefundEvent", {**common_event, "state": enum("requested", "approved", "rejected", "paid", "failed"),
        "amount": ref("Money"), "payment_ref": URI}, ["previous_event"])
    msg("KeyDescriptor", {"owner": URI, "jwk": ref("JWK"), "valid_from": TIME, "valid_until": TIME,
        "status": enum("active", "revoked"), "roles": arr(S, 1)})
    msg("IssuerPolicy", {"owner": URI, "revision": POS, "accepted_issuers": arr(URI),
        "claim_types": arr(S), "key_status_policy": S, "retention_days": INT, "appeal_url": URL})
    msg("EvidenceStatement", {"issuer": URI, "subject": URI, "order_id": URI, "line_id": URI,
        "claim_type": S, "observed_at": TIME, "evidence_level": enum("simulated", "seller_asserted", "provider_attested"),
        "audience": URI, "nonce": S, "expires_at": TIME, "source_ref": URI, "supersedes": URI}, ["supersedes"])
    msg("PriceObservation", {"offer_id": URI, "source": URI, "observed_at": TIME,
        "scope": enum("public", "personalized", "transaction"), "price": ref("Money"),
        "included_charges": arr(S), "unknown_costs": arr(S)})
    msg("SalesObservation", {"source": URI, "subject": URI, "period_start": TIME, "period_end": TIME,
        "unit": enum("orders", "lines", "units"), "count": INT, "returns": INT,
        "overlap": enum("deduplicated", "unknown"), "evidence_refs": arr(URI)})
    msg("ReviewEligibility", {"issuer": URI, "order_id": URI, "line_id": URI, "seller_id": URI,
        "buyer_subject": URI, "policy_id": URI, "evidence_refs": arr(URI, 1), "expires_at": TIME})
    msg("BuyerReview", {"eligibility_id": URI, "seller_id": URI, "product_id": URI,
        "buyer_subject": URI, "revision": POS, "rating": {"type": "integer", "minimum": 1, "maximum": 5},
        "text": S, "experience_basis": enum("buyer_reported", "order_events", "automated_fact_check"),
        "conflicts": arr(S), "previous_review_digest": DIGEST}, ["previous_review_digest"])
    msg("CommunityPolicy", {"community": URI, "revision": POS, "reviewer_selection": S,
        "conflict_policy": S, "evidence_requirements": S, "response_days": POS, "appeal_days": POS,
        "insufficient_reviewers": S, "moderator_powers": arr(S)})
    msg("CommunityReview", {"author": URI, "subject": URI, "policy_id": URI, "text": S,
        "method": S, "evidence_refs": arr(URI), "conflicts": arr(S)})
    msg("ClaimCheck", {"community": URI, "subject": URI, "claim": S, "policy_id": URI,
        "state": enum("submitted", "reviewing", "concluded"),
        "conclusion": enum("supported", "contradicted", "inconclusive"),
        "evidence_refs": arr(URI), "reason": S}, ["conclusion"])
    msg("AbuseReport", {"reporter": URI, "subject": URI, "policy_id": URI, "reason": S,
        "evidence_refs": arr(URI)})
    msg("ModerationDecision", {"community": URI, "subject": URI, "policy_id": URI,
        "revision": POS, "action": enum("annotate", "limit_display", "remove", "restore"),
        "reason": S, "reviewers": arr(URI, 1), "evidence_refs": arr(URI),
        "previous_decision": URI}, ["previous_decision"])
    msg("Appeal", {"decision_id": URI, "appellant": URI, "grounds": S, "evidence_refs": arr(URI),
        "state": enum("submitted", "reviewing", "accepted", "rejected"), "replacement_decision": URI}, ["replacement_decision"])
    msg("ReputationAssessment", {"subject": URI, "policy_id": URI, "input_refs": arr(URI),
        "review_count": INT, "overlap": enum("deduplicated", "unknown"), "conclusion": S,
        "limitations": arr(S, 1)})
    msg("FeeSchedule", {"network_id": URI, "revision": POS, "resource_class": S,
        "period_seconds": POS, "fee": ref("TokenAmount"), "recipient": URI,
        "valid_from": TIME, "valid_until": TIME, "max_offers": POS, "max_bytes": POS})
    msg("PublicationPayment", {"operation_id": URI, "catalog_id": URI, "payer": URI,
        "recipient": URI, "fee_schedule_id": URI, "charge": ref("TokenAmount"),
        "state": enum("pending", "settled", "failed", "refunded", "simulated"), "receipt_ref": URI})
    msg("ServiceQuote", {"provider": URI, "client": URI, "service": enum("search", "storage"),
        "unit": S, "quantity": POS, "charge": ref("TokenAmount"), "max_charge": ref("TokenAmount"),
        "terms_url": URL, "expires_at": TIME})
    msg("TokenPolicy", {"network_id": URI, "asset": URI, "uses": arr(enum("registration", "renewal", "search", "storage"), 1),
        "status": enum("documentary", "operational"), "fee_authority": URI, "mint_authority": URI,
        "governance_url": URL, "supply_disclosure_url": URL, "allocation_disclosure_url": URL,
        "upgrade_disclosure_url": URL})
    msg("Error", {"code": enum("invalid_message", "unauthorized", "forbidden", "unsupported_requirement",
        "state_conflict", "idempotency_conflict", "cursor_expired", "quote_expired", "limit_exceeded", "unavailable"),
        "message": S, "retryable": BOOL, "field": S, "operation_id": URI}, ["field", "operation_id"])
    DEFS["SignedDocument"] = obj({"payload": {"oneOf": [ref(n) for n in MESSAGES]},
        "jws": {"type": "string", "pattern": "^[A-Za-z0-9_-]+\\.[A-Za-z0-9_-]+\\.[A-Za-z0-9_-]+$"}})
    return {"$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:amp:schema:0.1", "title": "AMP 0.1 experimental document bundle",
        "description": "Generated by tools/generate_schemas.py. Structure only; see SPEC.md.",
        "oneOf": [ref(n) for n in MESSAGES] + [ref("SignedDocument")], "$defs": DEFS}


def main():
    path = ROOT / "schemas" / "0.1" / "protocol.schema.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"Generated {len(MESSAGES)} message definitions and shared types")


if __name__ == "__main__":
    main()
