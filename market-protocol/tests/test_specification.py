"""Executable conformance vectors; external service behavior remains documentary."""
from copy import deepcopy
from datetime import timedelta
import json

from cryptography.exceptions import InvalidSignature
import pytest

from tools import generate_examples, generate_schemas
from tools.check import check_examples, check_links
from tools.validation import (ROOT, NOW, load, validate, semantic, canonical, digest, strict_loads,
    b64, unb64, verify, sign, check_order, check_presentation, assemble_snapshot, apply_delta,
    filter_result, same_intention, active_registration, eligible_offers, instant)

CASES = load(ROOT / "examples/cases.json")


def example(name):
    return load(ROOT / "examples/valid" / (name + ".json"))


@pytest.mark.parametrize("name", CASES["valid"])
def test_valid_structure_and_semantics(name):
    d = load(ROOT / "examples" / name)
    validate(d)
    semantic(d)


@pytest.mark.parametrize("case", CASES["invalid"], ids=lambda c: c["file"])
def test_expected_rejection(case):
    d = load(ROOT / "examples" / case["file"])
    if case["stage"] == "semantic":
        validate(d)
    with pytest.raises(ValueError, match="^" + case["error"] + "$"):
        (validate if case["stage"] == "schema" else semantic)(d)


@pytest.mark.parametrize("case", CASES["signed"], ids=lambda c: c["file"])
def test_signatures(case):
    verify(load(ROOT / "examples" / case["file"]), load(ROOT / "examples" / case["key"]), case["role"], instant(case["as_of"]))


def test_generated_files_reproducible():
    assert generate_schemas.build() == load(ROOT / "schemas/0.1/protocol.schema.json")
    keys = generate_examples.fixtures()
    for slug, d in generate_examples.DOCS.items():
        assert d == example(slug)
    private, key = keys["seller-a"]
    assert sign(example("manifest-a"), private, key["id"]) == load(ROOT / "examples/signed/manifest-a.json")


def test_complete_inventory_and_links():
    check_examples()
    assert check_links() > 30


@pytest.mark.parametrize("raw", ['{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}', '{"x":9007199254740992}'])
def test_strict_json(raw):
    with pytest.raises(ValueError):
        strict_loads(raw)


def test_jcs_not_json_whitespace_or_insertion_order():
    assert canonical({"z": 1, "a": "ü"}) == b'{"a":"\xc3\xbc","z":1}'
    assert digest({"z": 1, "a": 2}) == digest({"a": 2, "z": 1})


def test_tampered_payload():
    envelope = load(ROOT / "examples/signed/quote.json")
    envelope["payload"]["quantity"] = 2
    with pytest.raises(ValueError, match="payload_mismatch"):
        verify(envelope, example("key-seller-a"), "checkout")


def test_tampered_signature():
    envelope = load(ROOT / "examples/signed/quote.json")
    header, payload, signature = envelope["jws"].split(".")
    corrupted = bytearray(unb64(signature))
    corrupted[0] ^= 1
    envelope["jws"] = ".".join([header, payload, b64(bytes(corrupted))])
    with pytest.raises(InvalidSignature):
        verify(envelope, example("key-seller-a"), "checkout")


@pytest.mark.parametrize("change,error", [
    (lambda k: k.update(status="revoked"), "revoked_key"),
    (lambda k: k.update(id="https://attacker.example/key"), "untrusted_key"),
    (lambda k: k.update(roles=["review"]), "key_role"),
    (lambda k: k.update(valid_until="2026-10-03T12:00:00Z"), "key_expired"),
])
def test_key_policy(change, error):
    key = example("key-seller-a")
    change(key)
    with pytest.raises(ValueError, match=error):
        verify(load(ROOT / "examples/signed/quote.json"), key, "checkout")


@pytest.mark.parametrize("header", [
    {"alg": "none", "kid": "https://keys.example/seller-a", "typ": "amp+jws"},
    {"alg": "EdDSA", "kid": "https://keys.example/seller-a", "typ": "amp+jws"},
    {"alg": "Ed25519", "kid": "https://keys.example/seller-a", "typ": "amp+jws", "jku": "https://attacker.example/key"},
])
def test_unaccepted_signature_header(header):
    envelope = load(ROOT / "examples/signed/quote.json")
    _, payload, signature = envelope["jws"].split(".")
    envelope["jws"] = ".".join([b64(canonical(header)), payload, signature])
    with pytest.raises(ValueError):
        verify(envelope, example("key-seller-a"), "checkout")


def test_presentation_context_and_expiry():
    d = example("evidence")
    check_presentation(d, d["audience"], d["nonce"])
    with pytest.raises(ValueError, match="presentation_binding"):
        check_presentation(d, "https://another.example", d["nonce"])
    with pytest.raises(ValueError, match="presentation_binding"):
        check_presentation(d, d["audience"], "different-challenge")
    with pytest.raises(ValueError, match="presentation_expired"):
        check_presentation(d, d["audience"], d["nonce"], NOW + timedelta(days=2))


def test_order_conditions():
    check_order(example("order-request"), example("quote"), example("authorization"))


@pytest.mark.parametrize("target,change,error", [
    ("request", lambda d: d["expected_total"].update(amount=1), "expected_total_mismatch"),
    ("request", lambda d: d.update(quantity=2), "quantity_binding"),
    ("request", lambda d: d.update(quote_id="urn:amp:other-quote"), "quote_binding"),
    ("auth", lambda d: d["limit"].update(amount=100), "budget_exceeded"),
    ("auth", lambda d: d["limit"].update(currency="USD"), "currency_mismatch"),
    ("auth", lambda d: d.update(seller_id="https://other.example/identity"), "seller_binding"),
    ("auth", lambda d: d.update(checkout_operator="https://other.example/checkout"), "operator_binding"),
    ("auth", lambda d: d.update(actions=["cancel"], order_id="urn:amp:example:order"), "action_not_authorized"),
    ("auth", lambda d: d.update(offer_id="https://seller-a.example/other-offer"), "offer_binding"),
    ("auth", lambda d: d.update(expires_at="2026-10-03T12:00:00Z"), "quote_or_permission_expired"),
    ("auth", lambda d: d.update(terms_sha256="0" * 64), "terms_binding"),
])
def test_order_rejects_changed_context(target, change, error):
    docs = {"request": example("order-request"), "quote": example("quote"), "auth": example("authorization")}
    change(docs[target])
    with pytest.raises(ValueError, match=error):
        check_order(docs["request"], docs["quote"], docs["auth"])


def test_requoted_unknown_total_cannot_pass_budget():
    q, r, a = example("quote"), example("order-request"), example("authorization")
    q.update(delivered_total_known=False, unknown_costs=["customs"])
    r["quote_sha256"] = digest(q)
    with pytest.raises(ValueError, match="unknown_delivered_cost"):
        check_order(r, q, a)


def test_same_operation_cannot_change_request():
    r = example("order-request")
    same_intention(r, deepcopy(r))
    changed = deepcopy(r)
    changed["quantity"] = 2
    with pytest.raises(ValueError, match="idempotency_conflict"):
        same_intention(r, changed)


def snapshot():
    m, s, p = example("manifest-a"), example("snapshot-a"), example("part-a")
    return m, s, {p["id"]: p}


def test_feed_upsert_delete_replay_and_rebuild():
    state = assemble_snapshot(*snapshot())
    updated = apply_delta(state, example("delta-upsert"))
    assert state["through"] == 1
    assert updated["records"][example("offer-a")["id"]]["price"]["amount"] == 90900
    assert apply_delta(updated, example("delta-upsert")) == updated
    deleted = apply_delta(updated, example("delta-delete"))
    assert deleted["records"] == {}
    assert deleted["revisions"][example("offer-a")["id"]] == 3
    assert apply_delta(apply_delta(assemble_snapshot(*snapshot()), example("delta-upsert")), example("delta-delete")) == deleted


def test_feed_gap_does_not_mutate_previous_state():
    state = assemble_snapshot(*snapshot())
    previous = deepcopy(state)
    with pytest.raises(ValueError, match="sequence_gap"):
        apply_delta(state, example("delta-delete"))
    assert state == previous


def test_feed_epoch_and_conflicting_replay():
    state = assemble_snapshot(*snapshot())
    d = example("delta-upsert")
    d["epoch"] = "other-epoch"
    with pytest.raises(ValueError, match="stream_context"):
        apply_delta(state, d)
    state = apply_delta(state, example("delta-upsert"))
    d = example("delta-upsert")
    d["changes"][0]["offer"]["price"]["amount"] = 1
    with pytest.raises(ValueError, match="conflicting_or_unverifiable_replay"):
        apply_delta(state, d)


def test_deleted_offer_cannot_return_with_old_revision():
    state = apply_delta(apply_delta(assemble_snapshot(*snapshot()), example("delta-upsert")), example("delta-delete"))
    d = example("delta-upsert")
    d.update(from_sequence=4, through=4)
    d["changes"][0]["seq"] = 4
    with pytest.raises(ValueError, match="revision_rollback"):
        apply_delta(state, d)


def test_snapshot_missing_or_tampered_part():
    m, s, parts = snapshot()
    with pytest.raises(ValueError, match="incomplete_snapshot"):
        assemble_snapshot(m, s, {})
    next(iter(parts.values()))["offers"][0]["price"]["amount"] = 1
    with pytest.raises(ValueError, match="part_digest"):
        assemble_snapshot(m, s, parts)


def test_snapshot_part_context_not_just_hash():
    m, s, parts = snapshot()
    p = next(iter(parts.values()))
    p["through"] = 99
    s["parts"][0]["sha256"] = digest(p)
    m["snapshot_sha256"] = digest(s)
    with pytest.raises(ValueError, match="part_context"):
        assemble_snapshot(m, s, parts)


def test_hard_filters_unknown_and_no_match():
    o = example("offer-a")
    f = {"field": "attributes.ram_gb", "op": "gte", "value": 16}
    assert filter_result(o, f, "EUR") == "match"
    o["attributes"]["ram_gb"] = 8
    assert filter_result(o, f, "EUR") == "no_match"
    o["attributes"]["ram_gb"] = None
    assert filter_result(o, f, "EUR") == "unknown"
    del o["attributes"]["ram_gb"]
    assert filter_result(o, f, "EUR") == "unknown"
    assert filter_result(o, {"field": "price.amount", "op": "lte", "value": 100000}, "USD") == "unknown"
    assert filter_result(o, {"field": "delivery_regions", "op": "in", "value": ["FR-IDF"]}, "EUR") == "no_match"


def test_simulated_checkpoint_is_not_finalized_evidence():
    with pytest.raises(ValueError, match="unverified_checkpoint"):
        active_registration(example("registration-a"), example("checkpoint"))


def test_registry_context_and_expiry_offline_predicates_only():
    r, cp = example("registration-a"), example("checkpoint")
    cp["finality"] = "finalized"  # Synthetic predicate input, NOT a verified chain proof.
    active_registration(r, cp)
    r["network_id"] = "urn:amp:other-network"
    with pytest.raises(ValueError, match="network_binding"):
        active_registration(r, cp)
    r = example("registration-a")
    with pytest.raises(ValueError, match="inactive_registration"):
        active_registration(r, cp, NOW + timedelta(days=40))


def test_renewal_does_not_refresh_offer():
    offer, query = example("offer-a"), example("query")
    assert eligible_offers(query, [offer]) == [offer["id"]]
    registration = example("registration-a")
    registration["lease_expires_at"] = "2027-01-01T00:00:00Z"
    cp = example("checkpoint")
    cp["finality"] = "finalized"  # Predicate fixture, not a proof.
    active_registration(registration, cp, NOW + timedelta(days=2))
    assert eligible_offers(query, [offer], NOW + timedelta(days=2)) == []


def test_default_order_and_partial_facts():
    offers = [example("offer-c"), example("offer-a"), example("offer-b")]
    expected = sorted(o["id"] for o in offers)
    assert eligible_offers(example("query"), offers) == expected
    offers[0]["attributes"]["ram_gb"] = None
    assert offers[0]["id"] not in eligible_offers(example("query"), offers)


def test_signature_cannot_claim_another_issuer():
    private, key = generate_examples.fixtures()["issuer"]
    evidence = example("evidence")
    evidence["issuer"] = "https://other-issuer.example/identity"
    forged = sign(evidence, private, key["id"])
    with pytest.raises(ValueError, match="signer_owner_binding"):
        verify(forged, key, "evidence")


def test_publication_excludes_private_working_directories():
    rules = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "/notes/" in rules and "/work/" in rules and "/.venv/" in rules
    for p in list(ROOT.glob("*.md")) + list((ROOT / "docs").glob("*.md")):
        assert "../notes/" not in p.read_text(encoding="utf-8")
