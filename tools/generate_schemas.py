"""Generate the companion schemas from one definition. No network access."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://raw.githubusercontent.com/famfamfam/addp/main/schemas/0.1/"
MAX_INT = 9007199254740991
S = {"type": "string", "minLength": 1, "maxLength": 512}
URL = {**S, "format": "uri", "pattern": "^https://"}
TIME = {"type": "string", "format": "date-time", "pattern": "Z$"}
N = {"type": "integer", "minimum": 0, "maximum": MAX_INT}
POS = {**N, "minimum": 1}
VERSION = {"const": "0.1"}
DIGEST = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
CURRENCY = {"type": "string", "pattern": "^[A-Z]{3}$"}


def arr(item, maximum=100, minimum=0):
    return {"type": "array", "items": item, "minItems": minimum, "maxItems": maximum}


def obj(props, required=None):
    return {"type": "object", "properties": props,
            "required": list(props) if required is None else required,
            "additionalProperties": False}


def ref(name):
    return {"$ref": BASE + name + ".json"}


def nullable(value):
    return {"anyOf": [value, {"type": "null"}]}


def message(props, required=None):
    fields = {"version": VERSION, **props,
              "extensions": {"type": "object", "maxProperties": 32,
                             "propertyNames": {"format": "uri"}},
              "critical_extensions": {**arr({"type": "string", "format": "uri"}, 32), "uniqueItems": True}}
    return obj(fields, ["version"] + (list(props) if required is None else required))


schemas = {}
schemas["ref"] = obj({"publisher": URL, "namespace": {"enum": ["addp", "ucp.catalog"]}, "id": S})
schemas["money"] = obj({"amount_minor": N, "currency": CURRENCY})
schemas["offer-facts"] = obj({
    "name": S, "unit_price_minor": N, "currency": CURRENCY,
    "condition": {"enum": ["new", "used", "refurbished"]},
    "colour": S, "availability": {"enum": ["in_stock", "out_of_stock", "unknown"]},
    "gtin": {"type": "string", "pattern": "^[0-9]{8,14}$"},
}, [])
schemas["offer-facts"]["dependentRequired"] = {"unit_price_minor": ["currency"], "currency": ["unit_price_minor"]}
schemas["resource"] = message({
    "ref": ref("ref"), "type": URL, "profile": {"enum": ["core/0.1", "offer-search/0.1"]},
    "revision": nullable(S), "facts": {"type": "object", "maxProperties": 64},
    "capabilities": {**arr(URL, 32), "uniqueItems": True}, "valid_until": nullable(TIME),
})
schemas["resource"]["allOf"] = [{
    "if": {"properties": {"profile": {"const": "offer-search/0.1"}}},
    "then": {"properties": {"facts": ref("offer-facts"), "type": {"const": "https://schema.org/Offer"}}},
}]
schemas["manifest"] = message({
    "protocol": {"const": "addp"}, "origin": URL,
    "profiles": {**arr({"enum": ["core/0.1", "offer-search/0.1"]}, 8, 1), "uniqueItems": True},
    "feed": URL, "capability_documents": {**arr(URL, 32), "uniqueItems": True},
    "query": obj({"endpoint": URL, "profiles": arr(S, 8, 1),
                  "text_modes": {"const": ["lexical"]}, "max_limit": {"type": "integer", "minimum": 1, "maximum": 100}}),
}, ["protocol", "origin", "profiles", "capability_documents"])
schemas["head"] = message({
    "epoch": S,
    "snapshot": obj({"id": S, "through": N, "parts": {**arr(URL, 1024, 1), "uniqueItems": True}, "expires_at": TIME}),
    "changes": URL,
}, ["epoch", "snapshot"])
schemas["part"] = message({"epoch": S, "snapshot_id": S, "through": N, "resources": arr(ref("resource"), 10000)})
event = {"oneOf": [obj({"seq": POS, "op": {"const": "upsert"}, "resource": ref("resource")}),
                   obj({"seq": POS, "op": {"const": "delete"}, "ref": ref("ref")})]}
schemas["delta"] = message({"epoch": S, "from_exclusive": N, "through": N, "events": arr(event, 10000), "more": {"type": "boolean"}})
predicate = obj({"field": S, "op": {"enum": ["eq", "in", "gte", "lte"]},
                 "value": {"anyOf": [S, N, arr(S, 32, 1)]}})
initial_query = message({
    "profile": S, "text": obj({"mode": S, "value": S}), "where": arr(predicate, 32),
    "select": {**arr(S, 32), "uniqueItems": True},
    "limit": {"type": "integer", "minimum": 1, "maximum": 100},
}, ["profile", "where", "select", "limit"])
schemas["query"] = {"oneOf": [initial_query, message({"cursor": S})]}
schemas["candidate"] = obj({
    "ref": ref("ref"), "type": URL, "profile": S, "source_revision": nullable(S),
    "retrieved_at": nullable(TIME), "indexed_at": TIME, "valid_until": nullable(TIME),
    "facts": {"type": "object", "maxProperties": 64},
    "paid_inclusion": {"enum": ["yes", "no", "unknown"]},
})
schemas["result"] = message({"snapshot": S, "items": arr(ref("candidate")), "next_cursor": nullable(S)})
schemas["problem"] = obj({
    "type": {"const": "about:blank"}, "title": S,
    "status": {"type": "integer", "minimum": 400, "maximum": 599}, "code": S,
    "detail": {"type": "string", "maxLength": 512},
}, ["type", "title", "status", "code"])
schemas["capability"] = message({
    "id": URL, "profile": S, "revision": S,
    "input_schema": obj({"url": URL, "sha256": DIGEST}),
    "output_schema": obj({"url": URL, "sha256": DIGEST}),
    "effects": arr(S, 16),
    "binding": obj({"protocol": S, "protocol_version": S, "endpoint": URL, "operation": S}),
})
schemas["intent"] = message({
    "id": S, "revision": POS, "profile": {"const": "sandbox-purchase/0.1"},
    "target": obj({"ref": ref("ref"), "quantity": {"const": 1}}),
    "constraints": obj({"max_total": ref("money"), "max_count": {"const": 1}}),
    "permissions": obj({"purchase": {"type": "boolean"}, "substitution": {"const": False}, "recurring": {"const": False}}),
    "capability_digest": DIGEST, "expires_at": TIME,
})
schemas["quote"] = message({
    "id": S, "revision": S, "session": S, "ref": ref("ref"), "quantity": {"const": 1},
    "total": ref("money"), "total_scope": {"const": "merchant_total"},
    "capability_digest": DIGEST, "expires_at": TIME,
})
schemas["outcome"] = {"enum": ["succeeded", "pending", "failed", "cancelled", "unknown"]}
schemas["operation"] = obj({
    "intent_id": S, "intent_revision": POS, "quote_id": S, "quote_revision": S,
    "session": S, "ref": ref("ref"), "quantity": {"const": 1}, "total": ref("money"), "capability_digest": DIGEST,
})


def main():
    directory = ROOT / "schemas/0.1"
    directory.mkdir(parents=True, exist_ok=True)
    for name, schema in schemas.items():
        result = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": BASE + name + ".json", **schema}
        (directory / (name + ".json")).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Generated {len(schemas)} schemas")


if __name__ == "__main__":
    main()
