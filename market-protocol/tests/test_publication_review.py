"""Adversarial vectors found during the pre-publication review."""
from copy import deepcopy

import pytest

from tools.validation import (ROOT, NOW, load, semantic, digest, instant, strict_loads,
    eligible_offers, assemble_snapshot, apply_delta, check_order, check_presentation, verify)


def e(name):
    return load(ROOT / "examples/valid" / (name + ".json"))


def state():
    m, s, p = e("manifest-a"), e("snapshot-a"), e("part-a")
    return assemble_snapshot(m, s, {p["id"]: p})


def test_price_unit_cannot_turn_expensive_offer_into_match():
    offer = e("offer-a")
    offer["price"].update(amount=9000, exponent=0)
    assert eligible_offers(e("query"), [offer]) == []


def test_destination_is_required_without_redundant_filter():
    query = e("query")
    query["hard_filters"] = []
    query["destination_region"] = "FR-IDF"
    assert eligible_offers(query, [e("offer-a")]) == []


def test_future_offer_is_not_current():
    offer = e("offer-a")
    offer["issued_at"] = "2026-10-03T12:01:00Z"
    assert eligible_offers(e("query"), [offer]) == []


@pytest.mark.parametrize("target", ["request", "quote", "auth"])
def test_future_purchase_document(target):
    docs = {"request": e("order-request"), "quote": e("quote"), "auth": e("authorization")}
    docs[target]["issued_at"] = "2026-10-03T12:30:00Z"
    with pytest.raises(ValueError, match="document_not_yet_issued"):
        check_order(docs["request"], docs["quote"], docs["auth"])


def test_purchase_permission_is_network_bound():
    auth = e("authorization")
    auth["network_id"] = "urn:amp:network:other"
    with pytest.raises(ValueError, match="network_binding"):
        check_order(e("order-request"), e("quote"), auth)


def test_quote_for_another_address_is_not_authorized():
    quote, request = e("quote"), e("order-request")
    quote["destination_ref"] = "urn:amp:destination:other"
    request["quote_sha256"] = digest(quote)
    with pytest.raises(ValueError, match="destination_binding"):
        check_order(request, quote, e("authorization"))


def test_delivery_deadline_is_enforced_after_requote():
    quote, request = e("quote"), e("order-request")
    quote["delivery_by"] = "2026-10-08T18:00:00Z"
    request["quote_sha256"] = digest(quote)
    with pytest.raises(ValueError, match="delivery_deadline_exceeded"):
        check_order(request, quote, e("authorization"))


@pytest.mark.parametrize("usage,error", [
    ({"committed_amount": 20000}, "aggregate_budget_exceeded"),
    ({"committed_quantity": 1}, "aggregate_quantity_exceeded"),
    ({"committed_amount": -1}, "invalid_usage_context"),
])
def test_new_operation_does_not_reset_permission(usage, error):
    request = e("order-request")
    request["operation_id"] = "urn:amp:operation:new-intention"
    with pytest.raises(ValueError, match=error):
        check_order(request, e("quote"), e("authorization"), **usage)


def test_delta_cannot_change_seller():
    delta = e("delta-upsert")
    delta["changes"][0]["offer"]["seller_id"] = "https://other.example/identity"
    original = state()
    copy = deepcopy(original)
    with pytest.raises(ValueError, match="seller_binding"):
        apply_delta(original, delta)
    assert original == copy


def test_delta_cannot_change_publisher_without_new_manifest():
    delta = e("delta-upsert")
    delta["publisher"] = "https://other.example/identity"
    with pytest.raises(ValueError, match="publisher_binding"):
        apply_delta(state(), delta)


def test_rebuilt_snapshot_retains_deleted_revision():
    original = apply_delta(apply_delta(state(), e("delta-upsert")), e("delta-delete"))
    m, s, p = e("manifest-after-delete"), e("snapshot-after-delete"), e("part-after-delete")
    rebuilt = assemble_snapshot(m, s, {p["id"]: p})
    assert rebuilt["records"] == original["records"]
    assert rebuilt["revisions"] == original["revisions"]
    delta = e("delta-upsert")
    delta.update(from_sequence=4, through=4)
    delta["changes"][0]["seq"] = 4
    with pytest.raises(ValueError, match="revision_rollback"):
        apply_delta(rebuilt, delta)


def test_epoch_change_cannot_drop_known_deleted_identity():
    original = apply_delta(apply_delta(state(), e("delta-upsert")), e("delta-delete"))
    m, s, p = e("manifest-after-delete"), e("snapshot-after-delete"), e("part-after-delete")
    for d in [m, s, p]:
        d["epoch"] = "epoch-2"
    p["tombstones"] = []
    s["parts"][0]["sha256"] = digest(p)
    m["snapshot_sha256"] = digest(s)
    with pytest.raises(ValueError, match="snapshot_revision_rollback"):
        assemble_snapshot(m, s, {p["id"]: p}, previous=original)


def test_snapshot_cannot_rollback_sequence():
    original = apply_delta(state(), e("delta-upsert"))
    m, s, p = e("manifest-a"), e("snapshot-a"), e("part-a")
    with pytest.raises(ValueError, match="snapshot_rollback"):
        assemble_snapshot(m, s, {p["id"]: p}, previous=original)


def test_snapshot_cannot_change_content_at_same_revision():
    original = state()
    m, s, p = e("manifest-a"), e("snapshot-a"), e("part-a")
    p["offers"][0]["price"]["amount"] = 1
    s["parts"][0]["sha256"] = digest(p)
    m["snapshot_sha256"] = digest(s)
    with pytest.raises(ValueError, match="snapshot_revision_conflict"):
        assemble_snapshot(m, s, {p["id"]: p}, previous=original)


def test_snapshot_handoff_requires_retained_delta_window():
    m, s, p = e("manifest-a"), e("snapshot-a"), e("part-a")
    m.update(head=10, oldest_sequence=5)
    with pytest.raises(ValueError, match="snapshot_handoff_gap"):
        assemble_snapshot(m, s, {p["id"]: p})


def test_reject_huge_sequence_range_in_bounded_work():
    delta = e("delta-upsert")
    delta["through"] = 9007199254740991
    with pytest.raises(ValueError, match="sequence_gap"):
        semantic(delta)


def test_future_signed_review_is_not_current():
    envelope = load(ROOT / "examples/signed/review.json")
    with pytest.raises(ValueError, match="document_not_yet_issued"):
        verify(envelope, e("key-buyer"), "review", NOW)
    verify(envelope, e("key-buyer"), "review", instant(envelope["payload"]["issued_at"]))


def test_key_must_be_valid_at_issue_not_only_at_verification():
    key = e("key-seller-a")
    key["valid_from"] = "2026-10-03T11:00:00Z"
    with pytest.raises(ValueError, match="key_not_valid_at_issue"):
        verify(load(ROOT / "examples/signed/quote.json"), key, "checkout")


def test_future_presentation_rejected():
    d = e("evidence")
    d["issued_at"] = "2026-10-03T12:01:00Z"
    with pytest.raises(ValueError, match="document_not_yet_issued"):
        check_presentation(d, d["audience"], d["nonce"])


def test_utf16_is_not_accepted_as_utf8_json():
    with pytest.raises(UnicodeError):
        strict_loads('{"value": 1}'.encode("utf-16"))
