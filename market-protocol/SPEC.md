# Agent Market Protocol — 0.1 experimental draft

Date: 2026-10-03. Package version: `0.1.0-draft.1`. Wire version: `0.1`.
This is a design draft, not a deployed standard. Breaking draft revisions require
a package revision and synchronized fixtures; stable wire compatibility is not promised.

## 1. Scope and normative language

AMP specifies discoverable commerce data and operations for independent sellers,
marketplaces, indexes, buyer runtimes and evidence services. The network requires a
shared on-chain publication registry and a designated service token. Search and
product transactions are off-chain unless an explicit binding says otherwise.

MUST, MUST NOT, SHOULD, SHOULD NOT and MAY are used as in BCP 14
([RFC 2119](https://www.rfc-editor.org/rfc/rfc2119.html),
[RFC 8174](https://www.rfc-editor.org/rfc/rfc8174.html)). These words specify duties
of the named role, not obligations to implement every role.

Normative modules are [architecture](docs/architecture.md), [catalogs](docs/catalogs.md),
[search](docs/search.md), [transactions](docs/transactions.md),
[registry](docs/registry.md), [node profiles](docs/node-profiles.md),
[economics](docs/token-economics.md), [evidence](docs/evidence.md),
[reputation](docs/reputation.md), [community](docs/community.md),
[security](docs/security-privacy.md) and [conformance](docs/conformance.md).
The README, integration guide, walkthrough, roadmap and prior-art comparison are informative.

If schema and prose disagree, this is a specification defect. An implementation MUST
NOT silently select whichever permits a transaction. Schemas check structure;
normative prose also governs state, authorization, trust and external facts.

## 2. Common representation

- Messages use UTF-8 JSON objects. Duplicate keys, non-finite numbers and malformed
  UTF-8 MUST be rejected before schema validation.
- Top-level typed documents carry `version`, `kind`, `id`, and `issued_at`.
  `id` is an absolute URI. IDs are case-sensitive, opaque and stable within the
  issuing authority. Mutable records and buyer-review edits keep their identity and
  increment their revision. Immutable events and replacement moderation decisions
  get new IDs; replacements explicitly reference the preceding document.
- Timestamp fields are RFC 3339 UTC strings with `Z`. Receivers MUST compare parsed
  instants, not strings. Expiry is exclusive: `now >= expires_at` is expired.
- Integer wire values MUST lie within the JSON interoperable safe-integer range.
  Money uses non-negative integer `amount`, ISO currency `currency` and an explicit
  `exponent`; no floating-point prices. Token amounts use a separate decimal-string
  base-unit type and a network-qualified asset identifier.
- Currency and exponent are one unit of comparison. Implementations MUST reject
  unsupported currency/exponent pairs; matching the currency code alone is insufficient.
- References are identities, not permission to fetch. Transport endpoint URLs use
  HTTPS and the fetch rules in [security](docs/security-privacy.md).
- Unknown top-level fields MUST be rejected in 0.1. `extensions` is the only open
  map; keys use a reverse-domain namespace. A required extension MUST be advertised
  and negotiated. An unsupported required extension fails before side effects.
- A missing field MUST NOT imply a favorable fact. `unknown`, `unsupported` and
  `no_match` have different meanings in search; absence of evidence is not approval.

The generated [schema bundle](schemas/0.1/protocol.schema.json) is the structural
contract. Its `$defs` names identify object shapes, not globally registered standards.

## 3. HTTPS binding

An operator supplies an HTTPS discovery URL to the client. This draft does not
claim an IANA well-known URI registration. `Discovery` advertises role-specific
endpoint URLs, network, required extensions and authentication binding identifiers.
The agent MUST start with locally configured trust in a network descriptor and
bootstrap sources. Discovering an endpoint does not add it to a trust policy.

Read operations use GET on an advertised document URL. Search and operational
requests use POST on the advertised endpoint, with `Content-Type: application/json`.
Successful creation uses 201, reads/searches 200, accepted asynchronous requests 202.
An asynchronous response MUST provide an operation ID and an authenticated status
lookup endpoint; 202 MUST NOT be represented as confirmed purchase or payment.

| Endpoint key | Request | Successful response |
|---|---|---|
| `search` | `SearchQuery` | `SearchResult` |
| `quote` | `QuoteRequest` | `Quote` |
| `order_create` | `OrderRequest` | `Order` or `OperationStatus` |
| `operation_lookup` | `OperationLookup` | `OperationStatus` |
| `order_lookup` | `OrderLookup` | `Order` |
| `order_action` | `OrderAction` | `OperationStatus` |
| `registry_submit` | `RegistryOperation` | `OperationStatus` |

Registry submission is a managed-gateway interface, not a blockchain transaction
encoding. Its successful acceptance does not prove inclusion or finality.
Quote, authorization, order and operation messages carry `network_id`. The service
MUST compare it with the locally accepted network and authenticated operation scope.
An ID or signature from another network does not satisfy that binding.
Signed publications (catalogs, evidence, reviews and policies) are retrieved as
documents. Their distribution APIs are implementation-specific; signatures and
content identities survive transport changes.

Errors use `Error`: `code`, `message`, `retryable`, optional field and operation ID.
HTTP 400: invalid message; 401/403: authentication/authority; 409: state or idempotency
conflict; 410: expired cursor/quote; 422: unsupported requirement; 429: quota; 503:
unavailable. A network error or 5xx after sending a mutation is an unknown outcome,
not proof of rejection. Free-text error messages MUST NOT be executed as instructions.

Maximum accepted sizes and rate limits MUST be advertised and enforced. A service
MUST reject excess input explicitly rather than truncate constraints. Persistent
cursor state and operation records MUST be isolated by authenticated principal.

## 4. Authority and signatures

Public facts, signatures and discovered endpoints never authorize spending. The
buyer runtime MUST obtain a separate authorization binding understood by the
checkout operator. The `Authorization` document records bounded consent; it is
not itself a bearer credential or a replacement for OAuth/payment authorization.
Unattended order creation MUST fail if that binding is absent or insufficient.

Signed off-chain payloads follow [evidence](docs/evidence.md): JCS bytes, JWS compact
serialization and Ed25519. Documents and snapshots can be fetched independently
of their operator; signatures MUST be verified against an authorized key, not a key
chosen by untrusted content. Hash integrity alone is not an identity proof.

## 5. Conformance and deployment boundary

Claims MUST identify role, draft version, supported category profiles, extensions
and bindings. A JSON-valid document alone is not a conforming service. A managed
RPC client MUST NOT claim light-client verification. Two instances of one codebase
do not establish independent implementation compatibility.

This package specifies an abstract chain interface and documentary checkout
requirements. No production chain or payment binding is included. Network deployment
and real purchases therefore remain blocked on those bindings, while document and
signature interoperability can already be tested.
