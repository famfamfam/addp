"""Publisher, index, query semantics, resolution and the model-facing view."""
from copy import deepcopy
import secrets
import time
from threading import RLock
import unicodedata

from .protocol import CURRENCIES, ProtocolError, origin, ref_key, require, timestamp, validate_ref

CORE = {"type": {"eq", "in"}, "publisher": {"eq", "in"}}
OFFER = {**CORE, "currency": {"eq"}, "unit_price_minor": {"gte", "lte"}, "condition": {"eq", "in"}}
PREDICATES = {"core/0.1": CORE, "offer-search/0.1": OFFER}
FIELDS = {"core/0.1": {"name"},
          "offer-search/0.1": {"name", "unit_price_minor", "currency", "condition", "colour", "availability", "gtin"}}


def fold(text):
    """Canonical caseless form (Unicode Standard, definition D145)."""
    return unicodedata.normalize("NFD", unicodedata.normalize("NFD", text).casefold())


def check_value(field, op, value):
    if field == "unit_price_minor":
        require(type(value) is int and op in ("gte", "lte"), "unsupported_query")
    elif op == "in":
        require(isinstance(value, list) and 0 < len(value) <= 32 and all(isinstance(v, str) for v in value),
                "unsupported_query")
    else:
        require(isinstance(value, str), "unsupported_query")
    values = value if isinstance(value, list) else [value]
    if field == "currency":
        require(all(v in CURRENCIES for v in values), "unsupported_query")
    if field == "condition":
        require(set(values) <= {"new", "used", "refurbished"}, "unsupported_query")


def check_query(query, validator):
    validator.check("query", query)
    if "cursor" in query:
        return
    profile = query["profile"]
    require(profile in FIELDS, "unsupported_profile")
    require(set(query["select"]) <= FIELDS[profile], "unsupported_query")
    currencies = 0
    price = False
    for p in query["where"]:
        require(p["field"] in PREDICATES[profile] and p["op"] in PREDICATES[profile][p["field"]], "unsupported_query")
        check_value(p["field"], p["op"], p["value"])
        currencies += p["field"] == "currency"
        price = price or p["field"] == "unit_price_minor"
    require(not price or currencies == 1, "unsupported_query", "a price predicate needs one currency")
    if "text" in query:
        require(query["text"]["mode"] == "lexical", "unsupported_query")
        require(bool(query["text"]["value"].split()), "unsupported_query")


def check_local(predicates, profile):
    """Hard constraints the runtime applies itself instead of sending them to an index.

    Any fact of the profile may be used, including ones indexes cannot filter on.
    """
    allowed = FIELDS[profile] | set(CORE)
    for p in predicates:
        require(set(p) == {"field", "op", "value"} and p["field"] in allowed, "unsupported_query")
        require(p["op"] in ("eq", "in", "gte", "lte"), "unsupported_query")
        if p["op"] in ("gte", "lte"):
            require(type(p["value"]) is int, "unsupported_query")
        else:
            check_value(p["field"], p["op"], p["value"])


def holds(resource, predicates):
    values = {**resource["facts"], "type": resource["type"], "publisher": resource["ref"]["publisher"]}
    for p in predicates:
        actual, expected, op = values.get(p["field"]), p["value"], p["op"]
        if actual is None:
            return False  # A missing fact never satisfies a constraint.
        if op in ("gte", "lte") and type(actual) is not int:
            return False
        if (op == "eq" and actual != expected) or (op == "in" and actual not in expected):
            return False
        if (op == "gte" and actual < expected) or (op == "lte" and actual > expected):
            return False
    return True


def matches(resource, query):
    if query["profile"] != "core/0.1" and resource["profile"] != query["profile"]:
        return False
    if not holds(resource, query["where"]):
        return False
    if "text" in query:
        name = resource["facts"].get("name")
        if not isinstance(name, str):
            return False
        name = fold(name)
        if not all(fold(term) in name for term in query["text"]["value"].split()):
            return False
    return True


class Publisher:
    def __init__(self, resources, validator):
        self.validator = validator
        self.records = {}
        for resource in resources:
            self.put(resource)

    def put(self, resource):
        self.validator.check("resource", resource)
        self.records[ref_key(resource["ref"])] = deepcopy(resource)

    def resolve(self, ref):
        try:
            return deepcopy(self.records[ref_key(ref)])
        except KeyError as exc:
            raise ProtocolError("not_found") from exc


class Index:
    def __init__(self, validator, clock=time.time, cursor_ttl=300, max_cursors=128, max_limit=100):
        self.validator = validator
        self.clock = clock
        self.cursor_ttl = cursor_ttl
        self.max_cursors = max_cursors  # Per client, so one client cannot expire another's cursors.
        self.max_limit = max_limit
        self.sources = {}
        self.cursors = {}
        self.lock = RLock()

    def install(self, publisher, head, parts, observed_at):
        self.validator.check("head", head)
        snapshot = head["snapshot"]
        require(timestamp(snapshot["expires_at"]) > self.clock(), "cursor_expired")
        require(set(parts) == set(snapshot["parts"]), detail="incomplete snapshot")
        require(all(origin(url) == publisher for url in snapshot["parts"]), "forbidden")
        if "changes" in head:
            require(origin(head["changes"]) == publisher, "forbidden")
        staged = {}
        for part in parts.values():
            self.validator.check("part", part)
            require((part["epoch"], part["snapshot_id"], part["through"]) ==
                    (head["epoch"], snapshot["id"], snapshot["through"]), detail="part of another snapshot")
            for resource in part["resources"]:
                self.validator.check("resource", resource)
                validate_ref(resource["ref"], publisher)
                key = ref_key(resource["ref"])
                require(key not in staged, detail="duplicate snapshot resource")
                staged[key] = self._entry(resource, observed_at)
        with self.lock:
            old = self.sources.get(publisher)
            require(not old or old["epoch"] != head["epoch"] or snapshot["through"] >= old["through"], "state_conflict")
            self.sources[publisher] = {"epoch": head["epoch"], "through": snapshot["through"], "records": staged}

    def apply(self, publisher, delta, observed_at):
        self.validator.check("delta", delta)
        start, end = delta["from_exclusive"], delta["through"]
        require(end >= start and end - start == len(delta["events"]), detail="delta coverage")
        for expected, event in enumerate(delta["events"], start + 1):
            require(event["seq"] == expected, detail="delta gap")
            ref = event["ref"] if event["op"] == "delete" else event["resource"]["ref"]
            validate_ref(ref, publisher)
            if event["op"] == "upsert":
                self.validator.check("resource", event["resource"])
        with self.lock:
            source = self.sources.get(publisher)
            require(source and source["epoch"] == delta["epoch"], "state_conflict", "rebuild snapshot")
            if end <= source["through"]:
                return  # Already applied; a replay changes nothing.
            require(start == source["through"], "state_conflict", "request changes from the watermark")
            staged = deepcopy(source["records"])
            for event in delta["events"]:
                if event["op"] == "delete":
                    staged.pop(ref_key(event["ref"]), None)
                else:
                    resource = event["resource"]
                    staged[ref_key(resource["ref"])] = self._entry(resource, observed_at)
            self.sources[publisher] = {"epoch": source["epoch"], "through": end, "records": staged}

    def _entry(self, resource, observed_at):
        return {"resource": deepcopy(resource), "retrieved_at": observed_at, "indexed_at": observed_at}

    def query(self, query, principal="public"):
        check_query(query, self.validator)
        with self.lock:
            now = self.clock()
            self.cursors = {k: v for k, v in self.cursors.items() if v["expires"] > now}
            if "cursor" in query:
                state = self.cursors.get(query["cursor"])
                require(state is not None, "cursor_expired")
                require(state["principal"] == principal, "forbidden")
                return deepcopy(state["response"])
            fields = set(query["select"]) | {p["field"] for p in query["where"] if p["field"] not in CORE}
            rows = []
            for source in self.sources.values():
                for entry in source["records"].values():
                    resource = entry["resource"]
                    if not matches(resource, query):
                        continue
                    rows.append({
                        "ref": deepcopy(resource["ref"]), "type": resource["type"], "profile": resource["profile"],
                        "source_revision": resource["revision"], "retrieved_at": entry["retrieved_at"],
                        "indexed_at": entry["indexed_at"], "valid_until": resource["valid_until"],
                        "facts": {k: v for k, v in resource["facts"].items() if k in fields},
                        "paid_inclusion": "unknown",
                    })
            rows.sort(key=lambda r: ref_key(r["ref"]))  # Fixed order; the index does not rank.
            limit = min(query["limit"], self.max_limit)
            pages = [rows[i:i + limit] for i in range(0, len(rows), limit)] or [[]]
            needed = len(pages) - 1
            require(needed <= self.max_cursors, "limit_exceeded", "narrow the query")
            mine = [k for k, v in self.cursors.items() if v["principal"] == principal]
            for token in mine[:max(0, len(mine) + needed - self.max_cursors)]:
                del self.cursors[token]  # Oldest cursors of this client only.
            tokens = [secrets.token_urlsafe(24) for _ in range(needed)]
            snapshot_id = secrets.token_urlsafe(12)
            responses = [{"version": "0.1", "snapshot": snapshot_id, "items": page,
                          "next_cursor": tokens[i] if i < needed else None} for i, page in enumerate(pages)]
            for token, response in zip(tokens, responses[1:]):
                self.cursors[token] = {"principal": principal, "expires": now + self.cursor_ttl,
                                       "response": deepcopy(response)}
            return responses[0]


def resolve_candidate(candidate, query, resolver, validator, local=()):
    """Fetch the resource from its publisher and re-check every hard constraint.

    `local` holds the constraints the runtime applied itself; they are checked
    against the resolved resource exactly like the query's predicates.
    """
    validator.check("candidate", candidate)
    check_query(query, validator)
    require("cursor" not in query, "unsupported_query", "use the initial query")
    check_local(local, candidate["profile"] if candidate["profile"] in FIELDS else "core/0.1")
    resource = resolver(candidate["ref"])
    validator.check("resource", resource)
    require(resource["ref"] == candidate["ref"], "forbidden", "resolved a different resource")
    require(matches(resource, query) and holds(resource, local), "constraint_failed",
            "live facts changed or are missing")
    return resource


class Handles:
    """Session-local names for objects the model may refer to. They grant nothing."""
    def __init__(self, clock=time.time, ttl=300):
        self.clock = clock
        self.ttl = ttl
        self.scope = secrets.token_hex(2)
        self.values = {}

    def add(self, value, kind="resource"):
        handle = f"{self.scope}:{kind[0]}{len(self.values) + 1}"
        self.values[handle] = (kind, self.clock() + self.ttl, deepcopy(value))
        return handle

    def get(self, handle, kind="resource"):
        require(handle in self.values, "not_found")
        actual, expires, value = self.values[handle]
        require(actual == kind, "forbidden")
        require(expires > self.clock(), "cursor_expired")
        return deepcopy(value)


def decision_view(candidates, handles, source_status, unresolved=()):
    """Smallest view for choosing among candidates.

    Facts appear once. Unknowns are stated, never defaulted. `unresolved` lists
    hard constraints these candidates cannot yet satisfy, such as a limit on the
    total, which an item price cannot establish.
    """
    rows = []
    for c in candidates:
        row = {"handle": handles.add(c), "publisher": c["ref"]["publisher"], "facts": deepcopy(c["facts"]),
               "retrieved_at": c["retrieved_at"], "valid_until": c["valid_until"],
               "paid_inclusion": c["paid_inclusion"]}
        if "unit_price_minor" in c["facts"]:
            row["price_basis"] = "item_only"
            row["delivered_total"] = "unknown"
        rows.append(row)
    coverage = "partial" if any(v != "ok" for v in source_status.values()) else "configured_indexes_only"
    return {"evidence": "index_claims", "coverage": coverage, "sources": dict(source_status),
            "unresolved": list(unresolved), "items": rows}
