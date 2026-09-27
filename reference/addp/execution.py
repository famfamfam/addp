"""Durable local journal, runtime checks, and a sandbox transaction service.

Nothing here moves money. The sandbox service keeps quotes, grants and
operations in one database, which is the easy case for the binding
requirements; a real payment flow spreads them over several services.
"""
from contextlib import contextmanager
import json
import secrets
import sqlite3
import time

from .protocol import canonical, digest, origin, ProtocolError, require, strict_json, timestamp

OPEN_OR_SPENT = ("not_started", "in_progress", "pending", "unknown", "succeeded")
TERMINAL = ("succeeded", "failed", "cancelled")
PAYLOAD_FIELDS = ("session", "ref", "quantity", "total", "capability_digest")


def new_operation_id():
    """128 random bits: unique across every runtime acting for the same user."""
    return secrets.token_urlsafe(16)


class Database:
    def __init__(self, path):
        self.path = str(path)
        # A file lets separate connections and restarts see the same state.
        require(self.path != ":memory:", detail="use a file-backed database")

    @contextmanager
    def connect(self, write=False):
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA synchronous=FULL")
        try:
            if write:
                connection.execute("BEGIN IMMEDIATE")
            yield connection
            if write:
                connection.commit()
        except BaseException:
            if write:
                connection.rollback()
            raise
        finally:
            connection.close()


class Journal(Database):
    def __init__(self, path, validator, clock=time.time):
        super().__init__(path)
        self.validator = validator
        self.clock = clock
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS intents(id TEXT PRIMARY KEY, body TEXT NOT NULL,
                    cancelled INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS operations(id TEXT PRIMARY KEY, intent_id TEXT NOT NULL,
                    payload TEXT NOT NULL, amount INTEGER NOT NULL, status TEXT NOT NULL, binding TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS audit(n INTEGER PRIMARY KEY, operation_id TEXT, status TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS intent_revisions(intent_id TEXT NOT NULL, revision INTEGER NOT NULL,
                    body TEXT NOT NULL, approved_at REAL, approval_method TEXT,
                    PRIMARY KEY(intent_id, revision));
            """)
        with self.connect(write=True) as db:
            # Old journals retain only the current revision; its approval metadata is unknown.
            for row in db.execute("SELECT id,body FROM intents").fetchall():
                revision = json.loads(row["body"])["revision"]
                db.execute("INSERT OR IGNORE INTO intent_revisions VALUES(?,?,?,NULL,NULL)",
                           (row["id"], revision, row["body"]))

    def _check_approval(self, intent, approval_method):
        self.validator.check("intent", intent)
        approved_at = self.clock()
        require(timestamp(intent["expires_at"]) > approved_at, "forbidden")
        require(isinstance(approval_method, str) and 1 <= len(approval_method) <= 128 and
                approval_method.isascii() and all(c.isalnum() or c in "._-" for c in approval_method),
                detail="approval_method must be a non-secret method label")
        return approved_at

    def approve(self, intent, *, approval_method):
        """Trusted host API: record approval with a non-secret label, never a credential."""
        approved_at = self._check_approval(intent, approval_method)
        with self.connect(write=True) as db:
            old = db.execute("SELECT body FROM intents WHERE id=?", (intent["id"],)).fetchone()
            if old:
                require(old["body"] == canonical(intent), "state_conflict", "use amend for a new revision")
                return
            db.execute("INSERT INTO intents(id,body) VALUES(?,?)", (intent["id"], canonical(intent)))
            db.execute("INSERT INTO intent_revisions VALUES(?,?,?,?,?)",
                       (intent["id"], intent["revision"], canonical(intent), approved_at, approval_method))

    def amend(self, intent, *, approval_method):
        approved_at = self._check_approval(intent, approval_method)
        with self.connect(write=True) as db:
            old = db.execute("SELECT * FROM intents WHERE id=?", (intent["id"],)).fetchone()
            require(old and not old["cancelled"], "forbidden")
            previous = json.loads(old["body"])
            require(intent["revision"] == previous["revision"] + 1, "state_conflict")
            require(intent["constraints"]["max_total"]["currency"] ==
                    previous["constraints"]["max_total"]["currency"], "forbidden")
            operations = db.execute("SELECT * FROM operations WHERE intent_id=?", (intent["id"],)).fetchall()
            require(all(o["status"] in TERMINAL for o in operations), "state_conflict", "unresolved operation")
            spent = sum(o["amount"] for o in operations if o["status"] == "succeeded")
            require(spent <= intent["constraints"]["max_total"]["amount_minor"], "constraint_failed")
            db.execute("INSERT INTO intent_revisions VALUES(?,?,?,?,?)",
                       (intent["id"], intent["revision"], canonical(intent), approved_at, approval_method))
            db.execute("UPDATE intents SET body=? WHERE id=?", (canonical(intent), intent["id"]))

    def intent(self, identifier):
        with self.connect() as db:
            row = db.execute("SELECT * FROM intents WHERE id=?", (identifier,)).fetchone()
        require(row is not None, "not_found")
        return json.loads(row["body"]), bool(row["cancelled"])

    def reserve(self, operation_id, payload, binding=""):
        """Checks and reservation in one transaction, so concurrent operations cannot overspend."""
        self.validator.check("operation", payload)
        with self.connect(write=True) as db:
            old = db.execute("SELECT * FROM operations WHERE id=?", (operation_id,)).fetchone()
            if old:
                require(old["payload"] == canonical(payload), "state_conflict", "identifier reused")
                return old["status"]
            row = db.execute("SELECT * FROM intents WHERE id=?", (payload["intent_id"],)).fetchone()
            require(row and not row["cancelled"], "forbidden")
            intent = json.loads(row["body"])
            require(timestamp(intent["expires_at"]) > self.clock(), "forbidden")
            require(intent["permissions"]["purchase"], "forbidden", "search is not purchase approval")
            require(intent["revision"] == payload["intent_revision"], "state_conflict")
            require(intent["target"]["ref"] == payload["ref"] and
                    intent["target"]["quantity"] == payload["quantity"], "constraint_failed")
            require(intent["capability_digest"] == payload["capability_digest"], "state_conflict")
            budget = intent["constraints"]["max_total"]
            require(budget["currency"] == payload["total"]["currency"], "constraint_failed")
            rows = db.execute("SELECT amount,status FROM operations WHERE intent_id=?",
                              (payload["intent_id"],)).fetchall()
            held = [r for r in rows if r["status"] in OPEN_OR_SPENT]
            require(len(held) < intent["constraints"]["max_count"], "constraint_failed", "operation count used up")
            require(sum(r["amount"] for r in held) + payload["total"]["amount_minor"] <= budget["amount_minor"],
                    "constraint_failed", "limit exceeded")
            db.execute("INSERT INTO operations VALUES(?,?,?,?,?,?)", (operation_id, payload["intent_id"],
                       canonical(payload), payload["total"]["amount_minor"], "not_started", binding))
            db.execute("INSERT INTO audit(operation_id,status) VALUES(?,?)", (operation_id, "not_started"))
            return "not_started"

    def operation(self, identifier):
        with self.connect() as db:
            row = db.execute("SELECT * FROM operations WHERE id=?", (identifier,)).fetchone()
        require(row is not None, "not_found")
        return {**dict(row), "payload": json.loads(row["payload"])}

    def dispatch(self, identifier):
        """Mark as sent. After this the reservation is released only on a known outcome."""
        with self.connect(write=True) as db:
            op = db.execute("SELECT * FROM operations WHERE id=?", (identifier,)).fetchone()
            require(op is not None, "not_found")
            if op["status"] != "not_started":
                return False
            row = db.execute("SELECT * FROM intents WHERE id=?", (op["intent_id"],)).fetchone()
            body = json.loads(row["body"])
            if row["cancelled"] or timestamp(body["expires_at"]) <= self.clock():
                db.execute("UPDATE operations SET status='cancelled' WHERE id=?", (identifier,))
                db.execute("INSERT INTO audit(operation_id,status) VALUES(?,?)", (identifier, "cancelled"))
                return False
            db.execute("UPDATE operations SET status='in_progress' WHERE id=?", (identifier,))
            db.execute("INSERT INTO audit(operation_id,status) VALUES(?,?)", (identifier, "in_progress"))
            return True

    def observe(self, identifier, status):
        require(status in ("pending", "unknown", *TERMINAL))
        with self.connect(write=True) as db:
            row = db.execute("SELECT status FROM operations WHERE id=?", (identifier,)).fetchone()
            require(row is not None, "not_found")
            if row["status"] in TERMINAL:
                require(row["status"] == status, "state_conflict", "final outcome changed")
                return
            db.execute("UPDATE operations SET status=? WHERE id=?", (status, identifier))
            db.execute("INSERT INTO audit(operation_id,status) VALUES(?,?)", (identifier, status))

    def cancel(self, identifier):
        with self.connect(write=True) as db:
            require(db.execute("SELECT id FROM intents WHERE id=?", (identifier,)).fetchone(), "not_found")
            db.execute("UPDATE intents SET cancelled=1 WHERE id=?", (identifier,))
            # Operations that may have been sent keep their reservation.
            db.execute("INSERT INTO audit(operation_id,status) SELECT id,'cancelled' FROM operations "
                       "WHERE intent_id=? AND status='not_started'", (identifier,))
            db.execute("UPDATE operations SET status='cancelled' WHERE intent_id=? AND status='not_started'",
                       (identifier,))

    def held(self, identifier):
        with self.connect() as db:
            rows = db.execute("SELECT amount,status FROM operations WHERE intent_id=?", (identifier,)).fetchall()
        return sum(r["amount"] for r in rows if r["status"] in OPEN_OR_SPENT)


class SandboxService(Database):
    """Execution binding "addp-sandbox" 0.1, operation "commit".

    Meets the binding requirements because everything is one database:
    1. rejects an operation that does not match the current quote;
    2. records every outcome for an operation identifier, rejections included,
       and returns it for a repeat of the identical operation;
    3. answers status requests ("not_found" if the identifier was never seen);
    4. checks its own grants (intent, publisher, currency, ceiling, expiry, revocation).
    """
    def __init__(self, path, validator, clock=time.time):
        super().__init__(path)
        self.validator = validator
        self.clock = clock
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS quotes(id TEXT PRIMARY KEY, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS grants(id TEXT PRIMARY KEY, intent_id TEXT NOT NULL,
                    publisher TEXT NOT NULL, currency TEXT NOT NULL, maximum INTEGER NOT NULL,
                    expires REAL NOT NULL, revoked INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS effects(id TEXT PRIMARY KEY, payload TEXT NOT NULL,
                    status TEXT NOT NULL, reason TEXT NOT NULL);
            """)

    def put_quote(self, quote):
        self.validator.check("quote", quote)
        with self.connect(write=True) as db:
            db.execute("INSERT OR REPLACE INTO quotes VALUES(?,?)", (quote["id"], canonical(quote)))

    def issue(self, grant_id, intent_id, publisher, currency, maximum, expires):
        # Stands in for an authorization server; separate from Journal.approve().
        with self.connect(write=True) as db:
            db.execute("INSERT INTO grants(id,intent_id,publisher,currency,maximum,expires) VALUES(?,?,?,?,?,?)",
                       (grant_id, intent_id, publisher, currency, maximum, expires))

    def revoke(self, grant_id):
        with self.connect(write=True) as db:
            db.execute("UPDATE grants SET revoked=1 WHERE id=?", (grant_id,))

    def _rejection(self, db, payload, grant):
        if grant["revoked"] or grant["expires"] <= self.clock():
            return "grant expired or revoked"
        if grant["currency"] != payload["total"]["currency"] or payload["total"]["amount_minor"] > grant["maximum"]:
            return "grant does not cover the amount"
        row = db.execute("SELECT body FROM quotes WHERE id=?", (payload["quote_id"],)).fetchone()
        if row is None:
            return "unknown quote"
        quote = json.loads(row["body"])
        if timestamp(quote["expires_at"]) <= self.clock():
            return "quote expired"
        if quote["revision"] != payload["quote_revision"] or any(quote[f] != payload[f] for f in PAYLOAD_FIELDS):
            return "operation does not match the current quote"
        for other in db.execute("SELECT payload,status FROM effects").fetchall():
            if json.loads(other["payload"])["intent_id"] == payload["intent_id"] and other["status"] in ("pending", "succeeded"):
                return "grant already used"
        return None

    def execute(self, key, payload, grant_id, lose_response=False, pending=False):
        """Returns "succeeded", "pending" or "failed". Raises only for requests it cannot attribute."""
        self.validator.check("operation", payload)
        with self.connect(write=True) as db:
            grant = db.execute("SELECT * FROM grants WHERE id=?", (grant_id,)).fetchone()
            # Unauthenticated requests are not recorded; otherwise anyone could burn an identifier.
            require(grant and grant["intent_id"] == payload["intent_id"] and
                    grant["publisher"] == payload["ref"]["publisher"], "forbidden")
            old = db.execute("SELECT * FROM effects WHERE id=?", (key,)).fetchone()
            if old:
                require(old["payload"] == canonical(payload), "state_conflict", "identifier reused")
                result = old["status"]
            else:
                reason = self._rejection(db, payload, grant)
                result = "failed" if reason else ("pending" if pending else "succeeded")
                db.execute("INSERT INTO effects VALUES(?,?,?,?)", (key, canonical(payload), result, reason or ""))
        if lose_response:
            raise TimeoutError("simulated lost response after the service committed")
        return result

    def status(self, key, payload):
        """Recorded outcome, "not_found", or "conflict" if another operation holds the identifier."""
        with self.connect() as db:
            row = db.execute("SELECT status,payload FROM effects WHERE id=?", (key,)).fetchone()
        if row is None:
            return "not_found"
        return row["status"] if row["payload"] == canonical(payload) else "conflict"

    def finish(self, key, status="succeeded"):
        require(status in TERMINAL)
        with self.connect(write=True) as db:
            row = db.execute("SELECT status FROM effects WHERE id=?", (key,)).fetchone()
            require(row and row["status"] == "pending", "state_conflict")
            db.execute("UPDATE effects SET status=? WHERE id=?", (status, key))

    def compensate(self, key, payload):
        require(self.status(key, payload) == "succeeded", "state_conflict")
        return "failed"  # No refund primitive exists here; an order is never erased.


class Runtime:
    """Performs approved operations through bindings installed by the operator."""
    def __init__(self, journal, bindings):
        self.journal = journal
        # {(protocol, protocol_version, operation): service}. Never taken from a publisher.
        self.bindings = dict(bindings)

    def run(self, operation_id, intent_id, quote, grant_id, capability_bytes, **faults):
        validator = self.journal.validator
        intent, cancelled = self.journal.intent(intent_id)
        require(not cancelled, "forbidden")
        # The runtime hashes the document it is about to use; it does not trust a digest it is told.
        capability = validator.check("capability", strict_json(capability_bytes))
        computed = digest(capability_bytes)
        require(computed == intent["capability_digest"], "state_conflict", "capability document changed")
        binding = capability["binding"]
        key = (binding["protocol"], binding["protocol_version"], binding["operation"])
        service = self.bindings.get(key)
        require(service is not None, "unsupported_profile", "no installed binding")
        require(origin(binding["endpoint"]) == intent["target"]["ref"]["publisher"], "forbidden")
        validator.check("quote", quote)
        require(quote["capability_digest"] == computed, "state_conflict")
        require(timestamp(quote["expires_at"]) > self.journal.clock(), "state_conflict", "quote expired")
        payload = {"intent_id": intent_id, "intent_revision": intent["revision"],
                   "quote_id": quote["id"], "quote_revision": quote["revision"],
                   **{k: quote[k] for k in PAYLOAD_FIELDS}}
        state = self.journal.reserve(operation_id, payload, "|".join(key))
        if state != "not_started":
            return self.recover(operation_id, grant_id)
        if not self.journal.dispatch(operation_id):
            return self.journal.operation(operation_id)["status"]
        return self._send(operation_id, service, payload, grant_id, **faults)

    def _send(self, operation_id, service, payload, grant_id, **faults):
        try:
            state = service.execute(operation_id, payload, grant_id, **faults)
        except ProtocolError:
            # Rejected without a recorded outcome. Only a recorded outcome settles an
            # identifier, so keep the reservation and ask for the status.
            self.journal.observe(operation_id, "unknown")
            return self.recover(operation_id)
        except (TimeoutError, OSError):
            state = "unknown"
        self.journal.observe(operation_id, state)
        return state

    def recover(self, operation_id, grant_id=None):
        """Settle an operation whose outcome is not known.

        "not_found" is ambiguous: the request may still be in flight. Resending the
        identical operation under the same identifier is safe, because the service
        records one outcome per identifier. Without a grant to resend with, the
        operation stays "unknown" and keeps its reservation. "conflict" means another
        operation holds the identifier, so this one can never be accepted.
        """
        operation = self.journal.operation(operation_id)
        if operation["status"] in TERMINAL or operation["status"] == "not_started":
            return operation["status"]
        service = self.bindings[tuple(operation["binding"].split("|"))]
        state = service.status(operation_id, operation["payload"])
        if state == "conflict":
            state = "failed"
        elif state == "not_found":
            if grant_id is None:
                self.journal.observe(operation_id, "unknown")
                return "unknown"
            return self._send(operation_id, service, operation["payload"], grant_id)
        self.journal.observe(operation_id, state)
        return state
