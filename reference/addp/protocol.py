"""Message rules shared by every role: JSON, identifiers, time, errors, fetching."""
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
import math
from pathlib import Path
import re
from urllib.parse import urljoin, urlsplit
import zlib

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

# ISO 4217 minor-unit exponents known to this implementation. The specification
# requires rejecting amounts in currencies whose exponent the receiver does not know.
CURRENCIES = {"EUR": 2, "USD": 2, "GBP": 2, "JPY": 0}
MAX_BYTES = 1_048_576
MAX_DEPTH = 32
ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "schemas/0.1"
STATUS = {
    "invalid_message": 400, "forbidden": 403, "not_found": 404, "method_not_allowed": 405,
    "state_conflict": 409, "cursor_expired": 410, "limit_exceeded": 413,
    "unsupported_media_type": 415, "unsupported_query": 422, "unsupported_profile": 422,
    "unsupported_extension": 422, "constraint_failed": 422, "rate_limited": 429, "unavailable": 503,
}
# Reason phrases from RFC 9110 (429 from RFC 6585). Not taken from the Python
# runtime, whose phrases differ between versions.
TITLES = {400: "Bad Request", 403: "Forbidden", 404: "Not Found", 405: "Method Not Allowed",
          409: "Conflict", 410: "Gone", 413: "Content Too Large", 415: "Unsupported Media Type",
          422: "Unprocessable Content", 429: "Too Many Requests", 503: "Service Unavailable"}
TIME_FIELDS = {"expires_at", "valid_until", "retrieved_at", "indexed_at"}
INTEGER_FIELDS = {"amount_minor", "unit_price_minor", "quantity", "max_count", "limit", "max_limit",
                  "seq", "through", "from_exclusive", "intent_revision"}
# RFC 3339 date-time restricted to UTC with a literal "Z".
TIME_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,9})?Z")
SCHEME_RE = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*")


class ProtocolError(Exception):
    def __init__(self, code, detail=""):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")

    def problem(self):
        status = STATUS[self.code]
        return {"type": "about:blank", "title": TITLES[status], "status": status, "code": self.code}


def require(condition, code="invalid_message", detail=""):
    if not condition:
        raise ProtocolError(code, detail)


def canonical(value):
    # Local equality/journal representation, NOT a signature format.
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def timestamp(value):
    require(isinstance(value, str) and TIME_RE.fullmatch(value) is not None, detail="timestamp format")
    try:
        # Python accepts at most microseconds; extra fraction digits do not change validity.
        head, _, fraction = value[:-1].partition(".")
        parsed = datetime.fromisoformat(head + ("." + fraction[:6] if fraction else "")).replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ProtocolError("invalid_message", "timestamp value") from exc
    return parsed.timestamp()


def absolute_uri(value):
    require(isinstance(value, str) and 0 < len(value) <= 512, detail="URI length")
    require(not any(ord(c) <= 32 or ord(c) == 127 for c in value), detail="URI characters")
    scheme, sep, _ = value.partition(":")
    require(sep == ":" and SCHEME_RE.fullmatch(scheme) is not None and "#" not in value, detail="absolute URI")


def origin(url):
    require(isinstance(url, str) and len(url) <= 512)
    require(not any(ord(c) <= 32 or ord(c) == 127 for c in url))
    try:
        p = urlsplit(url)
        host = p.hostname
        port = p.port
        require(p.scheme == "https" and host and not p.username and not p.password and not p.fragment)
        require(host.isascii() and "%" not in host and not host.endswith("."))
        host = host.lower()
        authority = f"[{host}]" if ":" in host else host
        return "https://" + authority + (f":{port}" if port not in (None, 443) else "")
    except ValueError as exc:
        raise ProtocolError("invalid_message", "invalid URL") from exc


def validate_origin(value):
    require(value == origin(value), detail="publisher must be a serialized origin")


def validate_ref(value, publisher=None):
    validate_origin(value["publisher"])
    if publisher is not None:
        require(value["publisher"] == publisher, "forbidden", "publisher mismatch")
    if value["namespace"] == "addp":
        require(origin(value["id"]) == value["publisher"], "forbidden", "cross-origin resource")
    else:
        require(value["namespace"] == "ucp.catalog", "unsupported_profile")


def ref_key(value):
    return (value["publisher"], value["namespace"], value["id"])


def strict_json(data):
    require(len(data) <= MAX_BYTES, "limit_exceeded")

    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, detail="duplicate JSON key")
            result[key] = value
        return result

    def no_constant(value):
        raise ProtocolError("invalid_message", "non-JSON numeric constant")

    try:
        result = json.loads(data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=no_constant)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ProtocolError("invalid_message", "invalid UTF-8 JSON") from exc
    stack = [(result, 0)]
    while stack:
        item, depth = stack.pop()
        require(depth <= MAX_DEPTH, "limit_exceeded", "JSON nesting")
        if isinstance(item, float):
            require(math.isfinite(item), detail="nonfinite number")
        if isinstance(item, str):
            require(not any(0xD800 <= ord(c) <= 0xDFFF for c in item), detail="unpaired surrogate")
        if isinstance(item, dict):
            for key in item:
                require(not any(0xD800 <= ord(c) <= 0xDFFF for c in key), detail="unpaired surrogate key")
        children = item.values() if isinstance(item, dict) else item if isinstance(item, list) else ()
        stack.extend((child, depth + 1) for child in children)
    return result


class Validator:
    """Schema checks plus the rules JSON Schema cannot express.

    Format keywords in the schemas are documentation only: jsonschema ignores
    them unless optional packages are installed, so formats are checked here.
    """
    def __init__(self):
        self.schemas = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in SCHEMA_DIR.glob("*.json")}
        require(bool(self.schemas), detail="generate schemas first")
        self.registry = Registry().with_resources(
            (s["$id"], Resource.from_contents(s)) for s in self.schemas.values())
        for schema in self.schemas.values():
            Draft202012Validator.check_schema(schema)

    def check(self, name, value):
        validator = Draft202012Validator(self.schemas[name], registry=self.registry)
        errors = list(validator.iter_errors(value))
        require(not errors, detail=f"schema {name}")
        self._walk(value)
        if name in ("ref", "candidate"):
            validate_ref(value if name == "ref" else value["ref"])
        if name in ("intent", "quote", "operation"):
            validate_ref(value["target"]["ref"] if name == "intent" else value["ref"])
        if name in ("resource", "candidate"):
            absolute_uri(value["type"])
        if name == "resource":
            validate_ref(value["ref"])
            if value["ref"]["namespace"] == "addp":
                require(value["revision"] is not None, detail="revision required for namespace addp")
            for url in value["capabilities"]:
                require(origin(url) == value["ref"]["publisher"], "forbidden")
        if name == "manifest":
            validate_origin(value["origin"])
            urls = value["capability_documents"] + ([value["feed"]] if "feed" in value else [])
            if "query" in value:
                urls.append(value["query"]["endpoint"])
            require(all(origin(u) == value["origin"] for u in urls), "forbidden")
        if name == "head":
            urls = value["snapshot"]["parts"] + ([value["changes"]] if "changes" in value else [])
            require(len({origin(u) for u in urls}) == 1, "forbidden")
        if name == "capability":
            publisher = origin(value["id"])
            require(origin(value["binding"]["endpoint"]) == publisher, "forbidden")
            for field in ("input_schema", "output_schema"):
                require(origin(value[field]["url"]) == publisher, "forbidden")
        return value

    def _walk(self, value):
        if isinstance(value, dict):
            # No critical extensions are implemented by the reference implementation.
            require(not value.get("critical_extensions"), "unsupported_extension")
            for key, child in value.items():
                if key == "extensions":
                    for name in child:
                        absolute_uri(name)
                    continue  # Extension content is not constrained.
                if key in INTEGER_FIELDS or (key == "revision" and isinstance(child, (int, float))):
                    require(type(child) is int, detail="integer required")
                if key == "currency":
                    require(child in CURRENCIES, detail="currency exponent unknown")
                if key in TIME_FIELDS and child is not None:
                    timestamp(child)
                self._walk(child)
        elif isinstance(value, list):
            for child in value:
                self._walk(child)


def public_address(text):
    try:
        address = ipaddress.ip_address(text)
    except ValueError as exc:
        raise ProtocolError("forbidden", "invalid DNS answer") from exc
    if address.version == 6 and address.ipv4_mapped is not None:
        address = address.ipv4_mapped  # Judge ::ffff:a.b.c.d by the IPv4 address it carries.
    return address.is_global


class Fetcher:
    """Discovery requests (specification section "Fetching").

    The transport must connect to the address it is given and still validate
    TLS against the URL's host name. There is no production HTTP backend here;
    tests supply a controlled peer. No credentials are ever sent.
    """
    def __init__(self, resolver, transport):
        self.resolver = resolver
        self.transport = transport

    def fetch(self, url):
        """Return the decoded body bytes. Needed where exact bytes are hashed."""
        publisher = origin(url)
        for _ in range(4):  # The request plus at most three redirects.
            require(origin(url) == publisher, "forbidden", "cross-origin redirect")
            addresses = self.resolver(urlsplit(url).hostname)
            require(bool(addresses), "unavailable")
            require(all(public_address(a) for a in addresses), "forbidden", "nonpublic address")
            status, headers, body = self.transport(url, addresses[0], {"Accept": "application/json"})
            headers = {k.lower(): v for k, v in headers.items()}
            require(len(body) <= MAX_BYTES, "limit_exceeded")
            if status in (301, 302, 303, 307, 308):
                require("location" in headers)
                url = urljoin(url, headers["location"])
                continue
            if status != 200:
                code = {404: "not_found", 410: "not_found", 429: "rate_limited"}.get(status, "unavailable")
                raise ProtocolError(code)
            media_type = headers.get("content-type", "").split(";")[0].strip().lower()
            require(media_type == "application/json", "unsupported_media_type")
            coding = headers.get("content-encoding", "identity").strip().lower()
            require(coding in ("identity", "gzip"), "unsupported_media_type", "content coding")
            if coding == "gzip":
                try:
                    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
                    body = decoder.decompress(body, MAX_BYTES + 1)
                    require(len(body) <= MAX_BYTES and not decoder.unconsumed_tail, "limit_exceeded")
                    require(decoder.eof and not decoder.unused_data, detail="invalid gzip stream")
                except zlib.error as exc:
                    raise ProtocolError("invalid_message", "invalid gzip") from exc
            return body
        raise ProtocolError("limit_exceeded", "redirect limit")

    def get(self, url):
        return strict_json(self.fetch(url))
