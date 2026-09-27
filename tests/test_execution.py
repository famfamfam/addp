from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import sqlite3

import pytest

from addp.execution import Journal, new_operation_id, Runtime, SandboxService
from addp.protocol import ProtocolError
from conftest import load, ROOT

BINDING = ("addp-sandbox", "0.1", "commit")
CAPABILITY = (ROOT / "examples/valid/capability.json").read_bytes()
PAYLOAD = load("valid/operation.json")  # The operation built from the example quote.


@pytest.fixture
def setup(tmp_path, validator, clock):
    journal = Journal(tmp_path / "journal.sqlite", validator, clock)
    service = SandboxService(tmp_path / "service.sqlite", validator, clock)
    intent, quote = load("valid/intent.json"), load("valid/quote.json")
    journal.approve(intent, approval_method="test-user-confirmation")
    service.put_quote(quote)
    service.issue("g1", "i7", quote["ref"]["publisher"], "EUR", 35000, clock() + 3600)
    return Runtime(journal, {BINDING: service}), intent, quote


def run(runtime, quote, op="op1", capability=CAPABILITY, **faults):
    return runtime.run(op, "i7", quote, "g1", capability, **faults)


def test_example_digests_match_files():
    import hashlib
    intent = load("valid/intent.json")
    capability = json.loads(CAPABILITY)
    assert intent["capability_digest"] == hashlib.sha256(CAPABILITY).hexdigest()
    schema = (ROOT / "schemas/0.1/operation.json").read_bytes()
    assert capability["input_schema"]["sha256"] == hashlib.sha256(schema).hexdigest()
    assert b"\r\n" not in CAPABILITY + schema  # Digests must not depend on the platform.


def test_commit_and_duplicate(setup):
    runtime, _, quote = setup
    assert run(runtime, quote) == "succeeded"
    assert run(runtime, quote) == "succeeded"  # Same identifier: no second effect.
    assert runtime.journal.held("i7") == 33399
    with pytest.raises(ProtocolError, match="constraint_failed"):
        run(runtime, quote, op="op2")


def test_lost_reply_and_restart(setup, validator, clock):
    runtime, _, quote = setup
    assert run(runtime, quote, lose_response=True) == "unknown"
    service = runtime.bindings[BINDING]
    assert service.status("op1", PAYLOAD) == "succeeded"
    assert runtime.journal.held("i7") == 33399
    restarted = Runtime(Journal(runtime.journal.path, validator, clock),
                        {BINDING: SandboxService(service.path, validator, clock)})
    assert restarted.recover("op1") == "succeeded"
    assert restarted.journal.held("i7") == 33399


def test_quote_changed_at_service(setup):
    runtime, _, quote = setup
    updated = deepcopy(quote)
    updated["total"]["amount_minor"] = 38900
    updated["revision"] = "2"
    runtime.bindings[BINDING].put_quote(updated)
    assert run(runtime, quote) == "failed"
    assert runtime.journal.held("i7") == 0
    assert runtime.bindings[BINDING].status("op1", PAYLOAD) == "failed"  # Recorded, so a late copy cannot run.


@pytest.mark.parametrize("change", ["price", "currency", "quote-digest", "target"])
def test_local_checks_stop_before_dispatch(setup, change):
    runtime, _, quote = setup
    if change == "price":
        quote["total"]["amount_minor"] = 35001
    elif change == "currency":
        quote["total"]["currency"] = "USD"
    elif change == "quote-digest":
        quote["capability_digest"] = "f" * 64
    else:
        quote["ref"]["id"] += "-substitute"
    with pytest.raises(ProtocolError):
        run(runtime, quote)
    assert runtime.journal.held("i7") == 0
    assert runtime.bindings[BINDING].status("op1", PAYLOAD) == "not_found"


def test_changed_capability_document(setup):
    runtime, _, quote = setup
    changed = json.loads(CAPABILITY)
    changed["revision"] = "c2"
    with pytest.raises(ProtocolError, match="state_conflict"):
        run(runtime, quote, capability=json.dumps(changed, indent=2).encode() + b"\n")
    reformatted = json.dumps(json.loads(CAPABILITY)).encode()  # Same content, other bytes.
    with pytest.raises(ProtocolError, match="state_conflict"):
        run(runtime, quote, capability=reformatted)
    assert runtime.bindings[BINDING].status("op1", PAYLOAD) == "not_found"


def test_binding_must_be_installed(setup):
    runtime, _, quote = setup
    bare = Runtime(runtime.journal, {})
    with pytest.raises(ProtocolError, match="unsupported_profile"):
        run(bare, quote)


def test_find_is_not_buy(tmp_path, validator, clock):
    journal = Journal(tmp_path / "journal.sqlite", validator, clock)
    intent = load("valid/intent.json")
    intent["permissions"]["purchase"] = False
    journal.approve(intent, approval_method="test-user-confirmation")
    with pytest.raises(ProtocolError, match="forbidden"):
        journal.reserve("op1", load("valid/operation.json"))


def test_concurrent_reservations(setup):
    runtime, _, _ = setup
    payload = load("valid/operation.json")

    def reserve(key):
        try:
            return runtime.journal.reserve(key, payload)
        except ProtocolError as error:
            return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(reserve, ("a", "b")))
    assert sorted(results) == ["constraint_failed", "not_started"]
    assert runtime.journal.held("i7") == 33399


@pytest.mark.parametrize("change", ["expiry", "revoke"])
def test_grant_blocks_effect(setup, clock, change):
    runtime, _, quote = setup
    if change == "expiry":
        clock.now += 3601
    else:
        runtime.bindings[BINDING].revoke("g1")
    assert run(runtime, quote) == "failed"
    assert runtime.journal.held("i7") == 0
    assert runtime.bindings[BINDING].status("op1", PAYLOAD) == "failed"


def test_cancel_pending_does_not_release(setup):
    runtime, _, quote = setup
    assert run(runtime, quote, pending=True) == "pending"
    runtime.journal.cancel("i7")
    assert runtime.journal.held("i7") == 33399
    runtime.bindings[BINDING].finish("op1")
    assert runtime.recover("op1") == "succeeded"
    with pytest.raises(ProtocolError, match="forbidden"):
        run(runtime, quote, op="op2")


def test_cancel_before_dispatch_releases(setup):
    runtime, _, _ = setup
    runtime.journal.reserve("op1", load("valid/operation.json"), "|".join(BINDING))
    runtime.journal.cancel("i7")
    assert runtime.journal.held("i7") == 0
    assert not runtime.journal.dispatch("op1")


def test_crash_after_dispatch_resends_same_identifier(setup):
    runtime, _, _ = setup
    runtime.journal.reserve("op1", load("valid/operation.json"), "|".join(BINDING))
    assert runtime.journal.dispatch("op1")  # Marked as sent, then the runtime crashed.
    assert runtime.recover("op1") == "unknown"  # "not_found" alone proves nothing.
    assert runtime.journal.held("i7") == 33399
    assert runtime.recover("op1", grant_id="g1") == "succeeded"  # Identical resend, same identifier.
    assert runtime.recover("op1", grant_id="g1") == "succeeded"
    assert runtime.journal.held("i7") == 33399


def test_late_copy_after_rejection_is_fenced(setup):
    runtime, _, quote = setup
    service = runtime.bindings[BINDING]
    payload = load("valid/operation.json")
    stale = deepcopy(quote)
    stale["revision"] = "0"
    service.put_quote(stale)
    assert service.execute("op1", payload, "g1") == "failed"
    service.put_quote(quote)  # A fresh operation would now succeed ...
    assert service.execute("op1", payload, "g1") == "failed"  # ... but this identifier is settled.


def test_identifier_taken_by_another_operation(setup):
    runtime, _, _ = setup
    service = runtime.bindings[BINDING]
    other = load("valid/operation.json")
    other["quote_revision"] = "0"  # A different operation, e.g. from another device.
    assert service.execute("op1", other, "g1") == "failed"
    runtime.journal.reserve("op1", PAYLOAD, "|".join(BINDING))
    assert runtime.journal.dispatch("op1")
    assert runtime.recover("op1", grant_id="g1") == "failed"  # "conflict": ours can never run.
    assert runtime.journal.held("i7") == 0


def test_unattributed_request_is_not_recorded(setup):
    runtime, _, _ = setup
    service = runtime.bindings[BINDING]
    with pytest.raises(ProtocolError, match="forbidden"):
        service.execute("op1", load("valid/operation.json"), "no-such-grant")
    assert service.status("op1", PAYLOAD) == "not_found"  # A stranger cannot burn the identifier.


def test_failed_compensation_keeps_spend(setup):
    runtime, _, quote = setup
    assert run(runtime, quote) == "succeeded"
    assert runtime.bindings[BINDING].compensate("op1", PAYLOAD) == "failed"
    assert runtime.journal.held("i7") == 33399
    assert runtime.bindings[BINDING].status("op1", PAYLOAD) == "succeeded"


def test_identifier_reused_with_other_operation(setup):
    runtime, _, quote = setup
    run(runtime, quote)
    quote["total"]["amount_minor"] -= 1
    with pytest.raises(ProtocolError, match="state_conflict"):
        run(runtime, quote)


def test_service_replay_survives_restart(setup, validator, clock):
    runtime, _, quote = setup
    run(runtime, quote)
    payload = runtime.journal.operation("op1")["payload"]
    service = SandboxService(runtime.bindings[BINDING].path, validator, clock)
    assert service.execute("op1", payload, "g1") == "succeeded"
    changed = deepcopy(payload)
    changed["total"]["amount_minor"] -= 1
    with pytest.raises(ProtocolError, match="state_conflict"):
        service.execute("op1", changed, "g1")


def test_revision_is_immutable_and_spend_survives_amendment(setup):
    runtime, intent, quote = setup
    run(runtime, quote)
    changed = deepcopy(intent)
    changed["constraints"]["max_total"]["amount_minor"] = 40000
    with pytest.raises(ProtocolError, match="state_conflict"):
        runtime.journal.approve(changed, approval_method="test-user-confirmation")
    changed["revision"] = 2
    runtime.journal.amend(changed, approval_method="test-user-confirmation")
    assert runtime.journal.held("i7") == 33399
    with pytest.raises(ProtocolError, match="constraint_failed"):
        run(runtime, quote, op="op2")


def test_amend_while_pending_rejected(setup):
    runtime, intent, quote = setup
    run(runtime, quote, pending=True)
    intent["revision"] = 2
    with pytest.raises(ProtocolError, match="state_conflict"):
        runtime.journal.amend(intent, approval_method="test-user-confirmation")


def test_expired_intent_before_dispatch(setup, clock):
    runtime, _, _ = setup
    runtime.journal.reserve("op1", load("valid/operation.json"), "|".join(BINDING))
    clock.now += 86401
    assert not runtime.journal.dispatch("op1")
    assert runtime.journal.held("i7") == 0


def test_operation_identifiers_are_random():
    ids = {new_operation_id() for _ in range(1000)}
    assert len(ids) == 1000 and all(len(i) == 22 for i in ids)  # 16 bytes, base64url.


def test_intent_revisions_are_retained(setup, validator, clock):
    runtime, intent, _ = setup
    changed = deepcopy(intent)
    changed["revision"] = 2
    changed["constraints"]["max_total"]["amount_minor"] = 40000
    runtime.journal.amend(changed, approval_method="test-user-confirmation")
    restarted = Journal(runtime.journal.path, validator, clock)
    with restarted.connect() as db:
        rows = db.execute("SELECT body FROM intent_revisions WHERE intent_id=? ORDER BY revision",
                          (intent["id"],)).fetchall()
    assert [json.loads(row["body"]) for row in rows] == [intent, changed]
    assert restarted.intent("i7") == (changed, False)


def test_approval_metadata_is_not_overwritten(setup, validator, clock):
    runtime, intent, _ = setup
    approved_at = clock()
    clock.now += 10
    runtime.journal.approve(intent, approval_method="different-confirmation-path")
    changed = deepcopy(intent)
    changed["revision"] = 2
    runtime.journal.amend(changed, approval_method="settings-confirmation")
    restarted = Journal(runtime.journal.path, validator, clock)
    with restarted.connect() as db:
        rows = db.execute("SELECT revision,approved_at,approval_method FROM intent_revisions "
                          "WHERE intent_id='i7' ORDER BY revision").fetchall()
    assert [tuple(row) for row in rows] == [
        (1, approved_at, "test-user-confirmation"),
        (2, clock(), "settings-confirmation"),
    ]


@pytest.mark.parametrize("method", [None, "", "contains spaces", "x" * 129, 123])
def test_invalid_approval_method_changes_nothing(tmp_path, validator, clock, method):
    journal = Journal(tmp_path / "journal.sqlite", validator, clock)
    intent = load("valid/intent.json")
    with pytest.raises(ProtocolError, match="invalid_message"):
        journal.approve(intent, approval_method=method)
    with journal.connect() as db:
        assert db.execute("SELECT count(*) FROM intents").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM intent_revisions").fetchone()[0] == 0


def test_rejected_amendment_leaves_history_unchanged(setup):
    runtime, intent, quote = setup
    run(runtime, quote, pending=True)
    changed = deepcopy(intent)
    changed["revision"] = 2
    with pytest.raises(ProtocolError, match="state_conflict"):
        runtime.journal.amend(changed, approval_method="test-user-confirmation")
    with runtime.journal.connect() as db:
        bodies = [json.loads(row["body"]) for row in db.execute("SELECT body FROM intent_revisions")]
    assert bodies == [intent]
    assert runtime.journal.intent("i7") == (intent, False)


def test_legacy_journal_keeps_current_revision_and_reservation(tmp_path, validator, clock):
    path = tmp_path / "old.sqlite"
    intent = load("valid/intent.json")
    intent["revision"] = 2  # The older implementation already discarded revision 1.
    payload = deepcopy(PAYLOAD)
    payload["intent_revision"] = 2
    db = sqlite3.connect(path)
    db.executescript("""
        CREATE TABLE intents(id TEXT PRIMARY KEY, body TEXT NOT NULL, cancelled INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE operations(id TEXT PRIMARY KEY, intent_id TEXT NOT NULL, payload TEXT NOT NULL,
            amount INTEGER NOT NULL, status TEXT NOT NULL, binding TEXT NOT NULL);
        CREATE TABLE audit(n INTEGER PRIMARY KEY, operation_id TEXT, status TEXT NOT NULL);
    """)
    db.execute("INSERT INTO intents VALUES(?,?,1)", ("i7", json.dumps(intent)))
    db.execute("INSERT INTO operations VALUES(?,?,?,?,?,?)",
               ("op1", "i7", json.dumps(payload), 33399, "unknown", "|".join(BINDING)))
    db.execute("INSERT INTO audit(operation_id,status) VALUES('op1','unknown')")
    db.commit()
    db.close()
    Journal(path, validator, clock)
    restarted = Journal(path, validator, clock)
    with restarted.connect() as db:
        rows = db.execute("SELECT * FROM intent_revisions").fetchall()
        assert len(rows) == 1 and rows[0]["revision"] == 2
        assert json.loads(rows[0]["body"]) == intent
        assert rows[0]["approved_at"] is None and rows[0]["approval_method"] is None
        assert db.execute("SELECT status FROM audit").fetchone()[0] == "unknown"
    assert restarted.intent("i7") == (intent, True)
    assert restarted.operation("op1")["payload"] == payload
    assert restarted.held("i7") == 33399


def test_cancel_records_outcome(setup):
    runtime, _, _ = setup
    runtime.journal.reserve("op1", PAYLOAD)
    runtime.journal.cancel("i7")
    runtime.journal.cancel("i7")
    with runtime.journal.connect() as db:
        states = [row["status"] for row in db.execute(
            "SELECT status FROM audit WHERE operation_id='op1' ORDER BY n")]
    assert states == ["not_started", "cancelled"]
    assert runtime.journal.held("i7") == 0
