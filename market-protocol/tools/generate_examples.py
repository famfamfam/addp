"""Reproducible documentary fixtures; never contacts merchants or blockchains."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from tools.validation import b64, digest, sign
from tools.generate_schemas import NETWORK_MESSAGES

ROOT = Path(__file__).resolve().parents[1]
T = "2026-10-03T10:00:00Z"
END = "2026-10-04T10:00:00Z"
NET = "urn:amp:network:documentary:1"
REG = "urn:amp:registry:documentary:1"
CHAIN = "urn:amp:chain:documentary:1"
ASSET = "urn:amp:asset:documentary:1:test-token"
SELLER = "https://seller-a.example/identity"
BUYER = "urn:amp:buyer:seller-a:demo"
ISSUER = "https://issuer.example/identity"
COMMUNITY = "https://community.example/identity"
CHECKOUT = "https://seller-a.example/checkout-operator"
DOCS = {}


def document(kind, slug, **fields):
    if kind in NETWORK_MESSAGES:
        fields = {"network_id": NET, **fields}
    d = {"version": "0.1", "kind": kind, "id": "urn:amp:example:" + slug, "issued_at": T, **fields}
    DOCS[slug] = d
    return d


def money(amount):
    return {"amount": amount, "currency": "EUR", "exponent": 2}


def tokens(units):
    return {"asset": ASSET, "units": str(units)}


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def fixtures():
    DOCS.clear()
    network = document("NetworkDescriptor", "network", network_id=NET, registry_id=REG,
        chain_profile=CHAIN, token_asset=ASSET, bootstrap_indexes=["https://index-a.example/descriptor", "https://index-b.example/descriptor"],
        profile_status="documentary", policy_url="https://network.example/policy", max_unanchored_seconds=300)
    checkpoint = document("RegistryCheckpoint", "checkpoint", network_id=NET, registry_id=REG,
        chain_profile=CHAIN, height=42, block_hash=hashlib.sha256(b"documentary block; not a chain proof").hexdigest(), finality="simulated")
    keys = {}
    for label, owner, roles in [("seller-a", SELLER, ["publisher", "checkout"]),
        ("issuer", ISSUER, ["evidence"]), ("buyer", BUYER, ["review"]), ("community", COMMUNITY, ["community"])]:
        # PUBLIC FIXTURE KEY MATERIAL. Never use this derivation or key in production.
        seed = hashlib.sha256(("AMP PUBLIC TEST KEY ONLY / " + label).encode()).digest()
        private = Ed25519PrivateKey.from_private_bytes(seed)
        public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        key = document("KeyDescriptor", "key-" + label, owner=owner,
            jwk={"kty": "OKP", "crv": "Ed25519", "x": b64(public)},
            valid_from="2026-10-01T00:00:00Z", valid_until="2027-10-01T00:00:00Z", status="active", roles=roles)
        key["id"] = "https://keys.example/" + label
        keys[label] = (private, key)
    document("Discovery", "discovery", operator=SELLER, network_id=NET,
        roles=["publisher", "checkout"], endpoints={
            "quote": "https://seller-a.example/amp/quote", "order_create": "https://seller-a.example/amp/orders",
            "operation_lookup": "https://seller-a.example/amp/operations/lookup", "order_lookup": "https://seller-a.example/amp/orders/lookup",
            "order_action": "https://seller-a.example/amp/orders/action"}, profiles=["laptops/0.1"],
        required_extensions=[], auth_bindings=["urn:amp:binding:documentary-only"],
        max_request_bytes=65536, max_response_bytes=1048576, idempotency_retention_seconds=604800)
    product = document("Product", "product", name="Demonstration laptop", manufacturer="Example Hardware",
        model="Demo 14", category_profile="laptops/0.1")
    variant = document("Variant", "variant", product_id=product["id"], name="16 GB / 512 GB",
        attributes={"ram_gb": 16, "mass_g": 1350, "storage_gb": 512, "screen_mm": 356})
    fee = document("FeeSchedule", "fee", network_id=NET, revision=1, resource_class="demo-small",
        period_seconds=2592000, fee=tokens(100), recipient="urn:amp:treasury:documentary", valid_from=T,
        valid_until="2026-11-03T10:00:00Z", max_offers=1000, max_bytes=10485760)
    offers = []
    for label, price in [("a", 89900), ("b", 94900), ("c", 92900)]:
        origin = f"https://seller-{label}.example"
        seller = document("Seller", "seller-" + label, name="Demonstration seller " + label.upper(),
            origin=origin, publishing_keys=["https://keys.example/seller-" + label], policy_url=origin + "/terms")
        seller["id"] = origin + "/identity"
        catalog_id = origin + "/catalog"
        offer = document("Offer", "offer-" + label, catalog_id=catalog_id, seller_id=seller["id"],
            product_id=product["id"], variant_id=variant["id"], revision=1, title="Demo 14, 16 GB",
            category_profile="laptops/0.1", price=money(price), condition="new", attributes=deepcopy(variant["attributes"]),
            delivery_regions=["DE-BE"], observed_at=T, valid_until=END,
            checkout_operator=origin + "/checkout-operator", lookup_url=origin + "/offers/demo-14")
        offer["id"] = origin + "/offers/demo-14"
        if label == "c":
            offer["platform_id"] = "https://marketplace.example/identity"
            offer["checkout_operator"] = "https://marketplace.example/checkout-operator"
            offer["fulfillment_provider"] = "https://marketplace.example/fulfillment"
        offers.append(offer)
        snapshot_id = origin + "/snapshot/1"
        part = document("SnapshotPart", "part-" + label, catalog_id=catalog_id, epoch="epoch-1",
            snapshot_id=snapshot_id, through=1, offers=[deepcopy(offer)], tombstones=[])
        part["id"] = origin + "/snapshot/1/part-1"
        snapshot = document("Snapshot", "snapshot-" + label, catalog_id=catalog_id, epoch="epoch-1", through=1,
            parts=[{"url": part["id"], "sha256": digest(part)}], expires_at=END)
        snapshot["id"] = snapshot_id
        manifest = document("CatalogManifest", "manifest-" + label, catalog_id=catalog_id,
            seller_id=seller["id"], publisher=seller["id"], revision=1, epoch="epoch-1", head=1, oldest_sequence=2,
            category_profile="laptops/0.1", snapshot_url=snapshot_id, snapshot_sha256=digest(snapshot),
            changes_url=origin + "/changes", mirror_urls=[], rights_url=origin + "/reuse-terms")
        manifest["id"] = origin + "/manifest"
        document("CatalogRegistration", "registration-" + label, network_id=NET, registry_id=REG,
            catalog_id=catalog_id, owner=seller["id"], publishing_keys=seller["publishing_keys"], revision=1,
            manifest_url=manifest["id"], commitment=digest(manifest), lease_expires_at="2026-11-02T10:00:00Z",
            state="active", checkpoint_id=checkpoint["id"], fee_schedule_id=fee["id"])
    document("RegistryOperation", "registry-operation", network_id=NET, registry_id=REG,
        operation_id="urn:amp:operation:register-a", catalog_id=offers[0]["catalog_id"], action="register",
        expected_revision=0, payer=SELLER, max_fee=tokens(100), fee_schedule_id=fee["id"],
        revision=1, manifest_url=DOCS["manifest-a"]["id"], commitment=digest(DOCS["manifest-a"]),
        lease_expires_at="2026-11-02T10:00:00Z")
    document("PublicationPayment", "publication-payment", operation_id="urn:amp:operation:register-a",
        catalog_id=offers[0]["catalog_id"], payer=SELLER, recipient=fee["recipient"], fee_schedule_id=fee["id"],
        charge=tokens(100), state="simulated", receipt_ref="urn:amp:receipt:documentary-registration")
    updated = deepcopy(offers[0])
    updated["revision"] = 2
    updated["price"] = money(90900)
    document("Delta", "delta-upsert", catalog_id=offers[0]["catalog_id"], publisher=SELLER, epoch="epoch-1", from_sequence=2,
        through=2, changes=[{"seq": 2, "action": "upsert", "offer_id": updated["id"], "revision": 2, "offer": updated}])
    document("Delta", "delta-delete", catalog_id=offers[0]["catalog_id"], publisher=SELLER, epoch="epoch-1", from_sequence=3,
        through=3, changes=[{"seq": 3, "action": "delete", "offer_id": updated["id"], "revision": 3}])
    deleted_part = document("SnapshotPart", "part-after-delete", catalog_id=offers[0]["catalog_id"],
        epoch="epoch-1", snapshot_id="https://seller-a.example/snapshot/3", through=3, offers=[],
        tombstones=[{"offer_id": updated["id"], "revision": 3}])
    deleted_part["id"] = "https://seller-a.example/snapshot/3/part-1"
    deleted_snapshot = document("Snapshot", "snapshot-after-delete", catalog_id=offers[0]["catalog_id"],
        epoch="epoch-1", through=3, parts=[{"url": deleted_part["id"], "sha256": digest(deleted_part)}], expires_at=END)
    deleted_snapshot["id"] = deleted_part["snapshot_id"]
    deleted_manifest = deepcopy(DOCS["manifest-a"])
    deleted_manifest.update(revision=3, head=3, oldest_sequence=4, snapshot_url=deleted_snapshot["id"],
                            snapshot_sha256=digest(deleted_snapshot))
    DOCS["manifest-after-delete"] = deleted_manifest
    for label in ["a", "b"]:
        document("IndexDescriptor", "index-" + label, network_id=NET, operator=f"https://index-{label}.example/identity",
            endpoint=f"https://index-{label}.example/search", category_profiles=["laptops/0.1"], regions=["DE-BE"],
            filter_fields=["price.amount", "attributes.ram_gb", "attributes.mass_g", "delivery_regions"],
            ranking_policy="id/0.1", coverage_description="Three documentary seller catalogs", max_limit=100,
            freshness_seconds=300, service_terms_url=f"https://index-{label}.example/terms")
    query = document("SearchQuery", "query", network_id=NET, category_profile="laptops/0.1", currency="EUR", currency_exponent=2,
        destination_region="DE-BE", hard_filters=[{"field": "price.amount", "op": "lte", "value": 100000},
            {"field": "attributes.ram_gb", "op": "gte", "value": 16},
            {"field": "delivery_regions", "op": "in", "value": ["DE-BE"]}],
        preferences=["lower mass"], text="laptop for travel", select=["id", "price", "attributes"], limit=10)
    document("SearchResult", "search-result", query_id=query["id"], snapshot_id="urn:amp:index-view:demo-1",
        checkpoint_id=checkpoint["id"], coverage={"catalogs": [o["catalog_id"] for o in offers],
            "description": "Documentary data, not live registered offers", "complete_for_declared_sources": True},
        candidates=[{"offer": o, "indexed_at": "2026-10-03T10:01:00Z", "checks": [
            {"field": f["field"], "result": "match", "source": o["id"], "observed_at": T} for f in query["hard_filters"]],
            "sponsored": False, "lookup_url": o["lookup_url"]} for o in offers], partial=False, failures=[])
    document("QuoteRequest", "quote-request", seller_id=SELLER, offer_id=offers[0]["id"], offer_revision=1,
        quantity=1, currency="EUR", destination_ref="urn:amp:private-destination:demo")
    quote = document("Quote", "quote", seller_id=SELLER, checkout_operator=CHECKOUT, offer_id=offers[0]["id"],
        offer_revision=1, destination_ref="urn:amp:private-destination:demo", quantity=1,
        subtotal=money(89900), delivery=money(1000), tax=money(0), discount=money(0),
        merchant_total=money(90900), delivered_total_known=True, unknown_costs=[],
        delivery_by="2026-10-06T18:00:00Z", terms_sha256=hashlib.sha256(b"documentary terms v1").hexdigest(),
        expires_at="2026-10-03T13:00:00Z", inventory_reserved=False)
    auth = document("Authorization", "authorization", buyer_subject=BUYER, seller_id=SELLER,
        checkout_operator=CHECKOUT, actions=["order_create"], offer_id=offers[0]["id"], max_quantity=1,
        destination_ref=quote["destination_ref"], delivery_deadline="2026-10-07T18:00:00Z",
        limit=money(100000), terms_sha256=quote["terms_sha256"], expires_at=quote["expires_at"],
        credential_ref="urn:amp:credential:NON-OPERATIONAL-DEMO")
    attribution = document("Attribution", "attribution", referrer="https://agent.example/identity",
        agreement_id="urn:amp:agreement:demo", referral_id="urn:amp:referral:demo", disclosed=True)
    request = document("OrderRequest", "order-request", operation_id="urn:amp:operation:purchase-1", seller_id=SELLER,
        quote_id=quote["id"], quote_sha256=digest(quote), authorization_id=auth["id"], quantity=1,
        expected_total=money(90900), attribution_id=attribution["id"])
    order = document("Order", "order", seller_id=SELLER, checkout_operator=CHECKOUT, buyer_subject=BUYER,
        revision=1, quote_id=quote["id"], operation_id=request["operation_id"],
        lines=[{"id": "urn:amp:line:1", "offer_id": offers[0]["id"], "variant_id": variant["id"], "quantity": 1}],
        total=money(90900), order_state="confirmed", payment_state="captured", fulfillment_state="pending",
        refund_state="none", allowed_actions=["cancel", "refund_request", "status"],
        handoff_url="https://seller-a.example/orders/demo", attribution_id=attribution["id"])
    document("OperationLookup", "operation-lookup", operation_id=request["operation_id"])
    document("OrderLookup", "order-lookup", order_id=order["id"])
    document("OperationStatus", "operation-status", operation_id=request["operation_id"], state="succeeded",
        request_sha256=digest(request), lookup_url="https://seller-a.example/operations/demo", result_ref=order["id"])
    document("OrderAction", "refund-request", operation_id="urn:amp:operation:refund-1", order_id=order["id"],
        expected_revision=1, action="refund_request", reason="Buyer reports a defect", authorization_id=auth["id"])
    event = dict(issuer=ISSUER, order_id=order["id"], line_id="urn:amp:line:1", observed_at=T, evidence_level="simulated")
    payment = document("PaymentEvent", "payment", **event, state="captured", amount=money(90900), payment_ref="urn:amp:payment:demo")
    document("FulfillmentEvent", "delivery", **{**event, "observed_at": "2026-10-06T12:00:00Z"},
        state="delivered", fulfillment_ref="urn:amp:delivery:demo")
    document("RefundEvent", "refund", **{**event, "observed_at": "2026-10-09T12:00:00Z"},
        state="paid", amount=money(90900), payment_ref=payment["payment_ref"])
    policy = document("IssuerPolicy", "issuer-policy", owner=COMMUNITY, revision=1,
        accepted_issuers=[ISSUER], claim_types=["payment_captured", "delivery", "refund"],
        key_status_policy="Current trusted descriptor; historical claims require policy review", retention_days=90,
        appeal_url="https://community.example/appeals")
    evidence = document("EvidenceStatement", "evidence", issuer=ISSUER, subject=BUYER, order_id=order["id"],
        line_id="urn:amp:line:1", claim_type="payment_captured", observed_at=T, evidence_level="simulated",
        audience=COMMUNITY, nonce="documentary-challenge-1", expires_at=END, source_ref=payment["id"])
    document("PriceObservation", "price-observation", offer_id=offers[0]["id"], source=SELLER, observed_at=T,
        scope="public", price=money(89900), included_charges=["item, tax included in displayed price"], unknown_costs=["delivery"])
    document("SalesObservation", "sales-observation", source=ISSUER, subject=SELLER,
        period_start="2026-10-01T00:00:00Z", period_end="2026-11-01T00:00:00Z", unit="orders", count=1,
        returns=1, overlap="unknown", evidence_refs=[payment["id"]])
    eligible = document("ReviewEligibility", "eligibility", issuer=ISSUER, order_id=order["id"], line_id="urn:amp:line:1",
        seller_id=SELLER, buyer_subject=BUYER, policy_id=policy["id"], evidence_refs=[evidence["id"]], expires_at="2026-12-01T00:00:00Z")
    review = document("BuyerReview", "review", eligibility_id=eligible["id"], seller_id=SELLER, product_id=product["id"],
        buyer_subject=BUYER, revision=1, rating=2, text="Fictional buyer reports a keyboard defect.",
        experience_basis="buyer_reported", conflicts=[])
    community_policy = document("CommunityPolicy", "community-policy", community=COMMUNITY, revision=1,
        reviewer_selection="Two disclosed reviewers with relevant subject experience",
        conflict_policy="Disclose relationships; recuse from own commercial disputes",
        evidence_requirements="Specific assertion, source documents and response opportunity",
        response_days=7, appeal_days=30, insufficient_reviewers="Publish inconclusive and the limitation",
        moderator_powers=["annotate", "limit_display", "remove", "restore"])
    cr = document("CommunityReview", "community-review", author="urn:amp:reviewer:1", subject=product["id"],
        policy_id=community_policy["id"], text="Illustrative inspection report", method="Documentary example; no physical test",
        evidence_refs=[review["id"]], conflicts=["No real test was conducted"])
    claim = document("ClaimCheck", "claim-check", community=COMMUNITY, subject=product["id"], claim="All units have a defective keyboard",
        policy_id=community_policy["id"], state="concluded", conclusion="inconclusive", evidence_refs=[review["id"]],
        reason="One fictional report cannot establish a model-wide defect")
    document("AbuseReport", "abuse-report", reporter="urn:amp:reviewer:2", subject=cr["id"],
        policy_id=community_policy["id"], reason="Report appears to generalize one account", evidence_refs=[claim["id"]])
    decision = document("ModerationDecision", "decision", community=COMMUNITY, subject=cr["id"],
        policy_id=community_policy["id"], revision=1, action="annotate", reason="Limited documentary evidence",
        reviewers=["urn:amp:reviewer:1", "urn:amp:reviewer:2"], evidence_refs=[claim["id"]])
    replacement = document("ModerationDecision", "decision-after-appeal", community=COMMUNITY, subject=cr["id"],
        policy_id=community_policy["id"], revision=2, action="restore", reason="Annotation incorrectly implied a completed test",
        reviewers=["urn:amp:reviewer:3", "urn:amp:reviewer:4"], evidence_refs=[claim["id"]], previous_decision=decision["id"])
    document("Appeal", "appeal", decision_id=decision["id"], appellant=BUYER, grounds="Correct the interpretation of the example",
        evidence_refs=[cr["id"]], state="accepted", replacement_decision=replacement["id"])
    document("ReputationAssessment", "assessment", subject=SELLER, policy_id=policy["id"], input_refs=[review["id"]],
        review_count=1, overlap="unknown", conclusion="Insufficient real-world evidence",
        limitations=["All events are simulated", "Buyer independence is not established"])
    document("ServiceQuote", "service-quote", provider="https://index-a.example/identity", client=SELLER,
        service="search", unit="query", quantity=100, charge=tokens(10), max_charge=tokens(10),
        terms_url="https://index-a.example/terms", expires_at=END)
    document("TokenPolicy", "token-policy", network_id=NET, asset=ASSET,
        uses=["registration", "renewal", "search", "storage"], status="documentary",
        fee_authority="urn:amp:authority:undecided", mint_authority="urn:amp:authority:undecided",
        governance_url="https://network.example/undecided/governance", supply_disclosure_url="https://network.example/undecided/supply",
        allocation_disclosure_url="https://network.example/undecided/allocation", upgrade_disclosure_url="https://network.example/undecided/upgrades")
    document("Error", "error", code="unsupported_requirement", message="The requested field is not supported",
        retryable=False, field="attributes.unrecognized")
    # Documentary chronology: later observations cannot be issued before they occur.
    for slug in ["delivery", "refund"]:
        DOCS[slug]["issued_at"] = DOCS[slug]["observed_at"]
    later = {
        "review": "2026-10-07T10:00:00Z", "refund-request": "2026-10-08T10:00:00Z",
        "community-review": "2026-10-10T10:00:00Z", "claim-check": "2026-10-10T11:00:00Z",
        "abuse-report": "2026-10-10T12:00:00Z", "decision": "2026-10-10T13:00:00Z",
        "appeal": "2026-10-11T10:00:00Z", "decision-after-appeal": "2026-10-11T10:00:00Z",
        "assessment": "2026-10-11T11:00:00Z", "sales-observation": "2026-11-01T00:00:00Z",
    }
    for slug, issued_at in later.items():
        DOCS[slug]["issued_at"] = issued_at
    DOCS["refund-request"]["authorization_id"] = "urn:amp:example:after-sales-authorization"
    after_sales = document("Authorization", "after-sales-authorization", buyer_subject=BUYER, seller_id=SELLER,
        checkout_operator=CHECKOUT, actions=["refund_request"], order_id=order["id"], max_quantity=1, limit=money(90900),
        terms_sha256=quote["terms_sha256"], expires_at="2026-10-09T00:00:00Z",
        credential_ref="urn:amp:credential:NON-OPERATIONAL-AFTER-SALES")
    after_sales["issued_at"] = "2026-10-08T09:00:00Z"
    return keys


def main():
    keys = fixtures()
    for slug, doc in DOCS.items():
        write(ROOT / "examples/valid" / (slug + ".json"), doc)
    signed_cases = []
    for slug, signer, role in [("manifest-a", "seller-a", "publisher"), ("delta-upsert", "seller-a", "publisher"),
        ("quote", "seller-a", "checkout"), ("evidence", "issuer", "evidence"),
        ("eligibility", "issuer", "evidence"), ("review", "buyer", "review"), ("decision", "community", "community")]:
        private, key = keys[signer]
        write(ROOT / "examples/signed" / (slug + ".json"), sign(DOCS[slug], private, key["id"]))
        signed_cases.append({"file": "signed/" + slug + ".json", "key": "valid/key-" + signer + ".json", "role": role,
                             "as_of": max("2026-10-03T12:00:00Z", DOCS[slug]["issued_at"])})
    invalid = []

    def negative(name, source, mutate, stage, error):
        d = deepcopy(DOCS[source])
        mutate(d)
        write(ROOT / "examples/invalid" / (name + ".json"), d)
        invalid.append({"file": "invalid/" + name + ".json", "stage": stage, "error": error})

    negative("negative-money", "offer-a", lambda d: d["price"].update(amount=-1), "schema", "schema_invalid")
    negative("float-money", "offer-a", lambda d: d["price"].update(amount=12.5), "schema", "schema_invalid")
    negative("unknown-field", "query", lambda d: d.update(ignore_constraints=True), "schema", "schema_invalid")
    negative("wrong-version", "query", lambda d: d.update(version="9.9"), "schema", "schema_invalid")
    negative("bad-timestamp", "offer-a", lambda d: d.update(observed_at="2026-99-99T00:00:00Z"), "schema", "schema_invalid")
    negative("quote-total", "quote", lambda d: d["merchant_total"].update(amount=1), "semantic", "quote_total_mismatch")
    negative("quote-currency", "quote", lambda d: d["delivery"].update(currency="USD"), "semantic", "currency_mismatch")
    negative("hidden-cost", "quote", lambda d: d.update(unknown_costs=["customs"]), "semantic", "unknown_delivered_cost")
    negative("feed-gap", "delta-upsert", lambda d: d.update(through=3), "semantic", "sequence_gap")
    negative("offer-mismatch", "delta-upsert", lambda d: d["changes"][0].update(offer_id="urn:amp:wrong-offer"), "semantic", "change_identity")
    negative("unsupported-filter", "query", lambda d: d["hard_filters"][0].update(field="attributes.magic"), "semantic", "unsupported_filter")
    negative("wrong-filter-type", "query", lambda d: d["hard_filters"][0].update(value="100000"), "semantic", "filter_value_type")
    negative("hidden-source-failure", "search-result", lambda d: d.update(failures=[{"source": "https://seller-a.example", "code": "unavailable"}]), "semantic", "hidden_partial_failure")
    negative("duplicate-snapshot-offer", "part-a", lambda d: d["offers"].append(deepcopy(d["offers"][0])), "semantic", "duplicate_offer")
    negative("service-overspend", "service-quote", lambda d: d["charge"].update(units="11"), "semantic", "service_budget_exceeded")
    negative("unlinked-review-edit", "review", lambda d: d.update(revision=2), "semantic", "review_revision_link")
    negative("premature-verdict", "claim-check", lambda d: d.update(state="reviewing"), "semantic", "claim_conclusion_state")
    negative("missing-appeal-result", "appeal", lambda d: d.pop("replacement_decision"), "semantic", "appeal_replacement")
    negative("wrong-registry-fields", "registry-operation", lambda d: d.update(action="renew"), "semantic", "registry_action_fields")
    negative("false-operation-success", "operation-status", lambda d: d.update(state="unknown"), "semantic", "operation_result_state")
    negative("unbounded-feed-range", "delta-upsert", lambda d: d.update(through=9007199254740991), "semantic", "sequence_gap")
    negative("live-deleted-collision", "part-a", lambda d: d["tombstones"].append({"offer_id": d["offers"][0]["id"], "revision": 2}), "semantic", "duplicate_offer")
    negative("missing-destination-consent", "authorization", lambda d: d.pop("destination_ref"), "semantic", "authorization_destination_scope")
    write(ROOT / "examples/cases.json", {"as_of": "2026-10-03T12:00:00Z",
        "all_external_events": "simulated", "valid": ["valid/" + k + ".json" for k in DOCS],
        "signed": signed_cases, "invalid": invalid})
    print(f"Generated {len(DOCS)} documents, {len(signed_cases)} signatures, {len(invalid)} negative cases")


if __name__ == "__main__":
    main()
