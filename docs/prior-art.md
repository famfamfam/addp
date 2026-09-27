# Prior art

What already exists, what it covers, and what ADDP adds. Checked against primary sources
on 2026-09-27 unless stated otherwise. Anything not listed under "checked" was not
reviewed and may overlap more than this page says.

## Summary

| Work | Finds | Where | Overlap with ADDP | What ADDP adds |
|---|---|---|---|---|
| UCP | Business capabilities; catalog of one business | `/.well-known/ucp` | Manifest; catalog search | Feeds with consistency rules; queries across indexes; re-evaluation at origin; runtime profile |
| ARD | Tools, APIs, agents, skills | `/.well-known/ard.json` | Origin catalogs; registries that search them | Items with typed facts; change feeds; fixed-order typed queries; re-evaluation; runtime profile |
| agent.json ("Agent Web Protocol") | Actions of one site | `/agent.json` or `/.well-known/agent.json` | Manifest and capability documents | Feeds; index queries; re-evaluation; spending limits |
| A2A agent cards | Agents | `/.well-known/agent-card.json` | None beyond "a JSON file at a well-known URI" | Everything item-related |
| OAuth (RFC 9728, 9396, 8693) | Authorization servers; delegated authority | Protected resource metadata | ADDP uses it as is | Nothing; ADDP defines no authorization |
| ACP | Checkout at one merchant; product feeds pushed to an agent | `/.well-known/acp.json` | Idempotent checkout; feeds; "checkout is authoritative" | Queries across indexes; feed deletions and sequence numbers; an expected total at completion (missing in ACP) |
| AP2 | Nothing; secures purchases inside a commerce protocol | None | User approval with limits (open mandates); exact binding of payment to checkout | Discovery; runtime handling of lost responses and reservations; AP2 could carry the ADDP intent |

The common gap: none of these defines how an index keeps a consistent copy of many
publishers' items, what a query over them means, or that a client must re-check an
index's claim at the origin before relying on it. AP2 states what merchants and
credential providers verify, and ACP how a merchant handles repeated requests, but
neither says what the agent's own runtime must record and check before it sends a
payment, or what it does when the response is lost. That is the part ADDP is an
experiment about.

## Checked

### Universal Commerce Protocol (UCP)

- Business profile at `/.well-known/ucp` with `ucp.version`, `ucp.services`,
  `ucp.capabilities`, `ucp.payment_handlers`. Capability names are reverse-domain, such
  as `dev.ucp.shopping.checkout`. Transports: REST, MCP, A2A, embedded. Version string
  on the pages read: `2026-08-25`.
- Catalog search `POST /catalog/search` (`query`, `filters.categories`,
  `filters.price.min/max` in minor units, `pagination.cursor/limit`) and lookup
  `POST /catalog/lookup` (`ids`). Product: `id`, `title`, `variants[]`; variant: `id`,
  `title`, `price{amount, currency}`, `availability{available}`.
- The pages read define no feeds, freshness or consistency guarantees. That is a
  statement about those pages, not proof that UCP has none.
- ADDP reads UCP catalogs through an adapter (draft appendix "UCP Catalog Adapter")
  instead of asking UCP businesses to publish anything new.
- Sources: <https://ucp.dev/specification/overview/>,
  <https://ucp.dev/specification/shopping/catalog/>,
  <https://ucp.dev/specification/shopping/catalog/search/>,
  <https://ucp.dev/specification/shopping/catalog/lookup/>

### Agentic Resource Discovery (ARD)

- Version v0.91, status "Proposal", dated 2026-08-26 (v0.9 of 2026-05-28 used
  `/.well-known/ai-catalog.json`). Apache 2.0. Authors from Google and Hugging Face;
  oversight board with members from Google, Hugging Face, Microsoft, Amazon and Cisco.
- Discovers "any external capability an AI client can call on": agents, MCP servers,
  skills, plugins, APIs, workflows. Products and offers are not in scope.
- Catalog at `/.well-known/ard.json`; required entry fields `identifier`
  (`urn:air:...`), `displayName`, `type` (media type), and `url` or `data`.
- Registries ingest by crawling. `POST /search` takes natural-language `text` and
  equality filters; ranking is up to each registry. No change feeds, no range
  predicates, no snapshot-consistent cursors.
- "Verification" means identity and provenance of catalog entries (`trustManifest`).
  No rule that a client re-checks a registry result at the origin.
- ARD "sits entirely before invocation": nothing on execution, approval or limits.
- Sources: <https://github.com/ards-project/ard-spec>,
  <https://developers.googleblog.com/announcing-the-agentic-resource-discovery-specification/>

### agent.json ("Agent Web Protocol", AWP)

- SPEC.md v0.2, "Draft RFC", 2026-04-16. MIT. Small project (3 stars at the time of
  checking). This project is why ADDP is no longer called "Agent Web Protocol".
- One JSON file per domain; the spec says `/agent.json`, the website says
  `/.well-known/agent.json`.
- Actions with `id`, `description`, `inputs`, `outputs`, `auth_required`, and optional
  `sensitivity`, `requires_human_confirmation`, `idempotency`, `reversible`. Types use a
  custom notation, not JSON Schema. Free-text `description` and `agent_hints` are aimed
  at the model.
- No feeds, no index queries, no re-validation at the origin, no spending limits.
- Source: <https://github.com/agentwebprotocol/spec>

### Agentic Web Protocol (also "AWP")

- Draft v0.1, CC-BY-4.0, one committer. JSON pages under `/awp`; decentralized,
  plural registries. Most specification pages returned 404 when checked, so field-level
  comparison was not possible. States that site content is "untrusted input, never
  instructions".
- Source: <https://github.com/awp-spec/awp>

### A2A agent cards

- `agent-card.json` is registered in the IANA Well-Known URIs registry (permanent,
  change controller Linux Foundation, registered 2025-08-01).
- Source: <https://www.iana.org/assignments/well-known-uris/well-known-uris.xhtml>

### IETF drafts on agent protocols

- `draft-cui-ai-agent-discovery-invocation-02` (2026-07-06): metadata format,
  discovery and a REST invocation interface for AI agents, with intent-based selection
  of agents. It finds agents; ADDP finds items.
- `draft-rosenberg-ai-protocols-00` (2025-05-05): framework, use cases and requirements
  for AI agent protocols.

### OAuth

- RFC 9728 (protected resource metadata): how a client learns a resource's
  authorization servers. Section 7.6: choosing which authorization server to trust is
  out of scope. ADDP inherits that gap and says so.
- RFC 9396 (Rich Authorization Requests) can carry operation details if the
  authorization server defines a type for them. ADDP does not define one.

### Agentic Commerce Protocol (ACP)

Checked on 2026-09-27 against the repository at commit `7fdd78d` (2026-07-18); latest
released version `2026-04-17`.

- Maintained by OpenAI and Stripe, status "beta", Apache 2.0. A technical steering
  committee has up to seven organizations; the founding maintainers appoint the seats.
  Versions are dates.
- Checkout API that the agent calls at the merchant: create, update and retrieve
  (`GET /checkout_sessions/{id}`) a session, then `complete` or `cancel` it. Amounts are
  integers in minor units. Requests carry a bearer token that the merchant must accept;
  a request signature is recommended. How the token is issued is not specified in the
  documents read, so an ADDP runtime would need credentials from each merchant or seller
  platform it uses.
- Idempotency. The `2026-04-17` OpenAPI requires `Idempotency-Key` on every POST,
  scoped to the authenticated identity and endpoint, with errors
  `idempotency_conflict` (same key, different body, 422) and `idempotency_in_flight`
  (409). The RFC text at the checked commit (section 6, marked as an unreleased rewrite)
  adds: an identical request returns the original response and status without repeating
  side effects; responses with status 5xx are not stored, and a retry after one is
  processed as a new request; keys are kept for at least 24 hours; storing the key and
  the operation in one transaction is recommended, not required.
- The request that completes a checkout (`CheckoutSessionCompleteRequest`, `2026-04-17`)
  has `buyer`, `payment_data`, `authentication_result`, `affiliate_attribution`,
  `risk_signals` and `marketing_consents`. It carries no expected total and no session
  version, so the merchant cannot tell that the session changed after the agent last
  read it.
- Delegated payment: a vault token usable only within an allowance with `reason`
  `one_time`, `max_amount`, `currency`, `checkout_session_id`, `merchant_id` and
  `expires_at`. This ties the token to one checkout and caps the amount. Like the Stripe
  token below, it does not fix the amount.
- Discovery document at `/.well-known/acp.json` (added in `2026-04-17`): protocol
  versions, API base URL, transports and services.
- Product feeds (RFC status "Proposal"; the `2026-04-17` release notes add the Feed API
  as an "unreleased" surface): the merchant pushes a full snapshot or upserts products
  to a feed service hosted by the agent. Partial updates cannot delete products; cursor
  deltas are deferred; no query is defined. "Agents MUST treat checkout responses as
  authoritative even when they differ from feed data", which is the same principle as
  ADDP's re-check at the origin.
- Intent traces (proposal): an agent may send a structured reason when it cancels a
  checkout, for example price. That can reveal the user's limit to the merchant.
- Sources: <https://github.com/agentic-commerce-protocol/agentic-commerce-protocol>
  (`rfcs/rfc.agentic_checkout.md`, `rfcs/rfc.delegate_payment.md`,
  `rfcs/rfc.product_feeds.md`, `rfcs/rfc.discovery.md`, `rfcs/rfc.intent_traces.md`,
  `spec/2026-04-17/openapi/openapi.agentic_checkout.yaml`, `changelog/2026-04-17.md`,
  `docs/governance.md`)

**ACP against the binding requirements of the draft:**

| Requirement | ACP `2026-04-17` |
|---|---|
| 1. Reject an operation that does not match the quote | Not met. `complete` carries no expected total or session version; the payment allowance only caps the amount. Needs an ACP extension, for example an expected total or session revision that the merchant must check on `complete`. |
| 2. One recorded outcome per identifier, rejections included | Met through `Idempotency-Key`, with two limits: a 5xx response is not recorded, and keys may expire after 24 hours. The runtime has to treat a 5xx as unknown and must not resend after the key may have expired. |
| 3. Status request per identifier | No such request. Retrieving the session and repeating the identical request with the same key cover the need while the key is kept. |
| 4. Own authorization | Met: bearer token, and a payment token limited to one checkout, an amount and an expiry. |

Until requirement 1 is met, an ADDP runtime using ACP has to ask the user to confirm
each completion.

### Agent Payments Protocol (AP2)

Checked on 2026-09-27 against the repository at commit `e1ea56d` (2026-04-29); version
0.2, released 2026-04-28.

- Repository `google-agentic-commerce/AP2`, Apache 2.0. The specification works "as a
  security feature within a Commerce Protocol"; catalogs, checkout updates and transport
  are out of scope. It is "designed explicitly to be compatible with" UCP.
- Checkout mandate: the merchant signs the checkout as a JWT; the closed mandate
  carries that JWT and its hash. The merchant must verify the hash and, if open mandates
  are included, every constraint, and must return a signed checkout receipt on
  acceptance or rejection.
- Payment mandate: bound to the same checkout by the hash of the checkout JWT, with
  payee, amount (integer minor units) and instrument. The credential provider, and the
  network if any, verify it before issuing a payment credential, and a payment receipt
  follows. This is an exact binding of the payment to the checkout, which a credential
  with a maximum amount does not give.
- Human present: the user sees the closed checkout on a "Trusted Surface" and signs.
  Human not present: the user signs open mandates with constraints and the agent's key
  (`cnf`); the agent signs the closed mandates; verifiers check them against the
  constraints. An agent must not present another open mandate before it has a rejection
  receipt for the previous one.
- Constraints: `checkout.allowed_merchants`, `checkout.line_items` (acceptable items and
  quantities), `payment.allowed_payees`, `payment.amount_range` (integer minor units),
  `payment.budget`, `payment.agent_recurrence` (frequency, maximum occurrences),
  `payment.allowed_payment_instruments`, `payment.allowed_pisps`,
  `payment.execution_date`, `payment.reference`. In the SDK, budget and occurrences are
  evaluated against a mandate context with past spending and uses, which the verifier
  has to keep. A credential provider that keeps it can enforce one limit across all of
  a user's devices.
- No retry, idempotency or status rules; these are left to the commerce protocol.
  Mandates and receipts are meant as dispute evidence, but "how this is used for dispute
  resolution" is out of scope.
- Inconsistency found: `payment.budget.max` is a JSON number with no stated unit, while
  `payment.amount_range` uses integer minor units. The Python SDK evaluates the budget as
  `int(max * 100)` for every currency (`code/sdk/python/ap2/sdk/constraints.py`). A
  budget of EUR 19.99 becomes 1998 minor units, so a payment of 19.99 is rejected; a
  budget of JPY 5000 becomes 500000, a hundred times the intended limit. This has not
  been reported upstream yet.
- Sources: <https://github.com/google-agentic-commerce/AP2> (`docs/ap2/specification.md`,
  `docs/ap2/checkout_mandate.md`, `docs/ap2/payment_mandate.md`,
  `code/sdk/schemas/ap2/*.json`, `code/sdk/python/ap2/sdk/constraints.py`,
  `CHANGELOG.md`)

**How an ADDP intent maps to AP2 open mandates:**

| ADDP intent | AP2 |
|---|---|
| `target.ref`, `target.quantity` | `checkout.allowed_merchants` and `checkout.line_items` with one acceptable item. The ADDP reference (origin, namespace, id) has to be mapped to the merchant object and item id. |
| `constraints.max_total` | `payment.amount_range` `max` for one payment; `payment.budget` for several. |
| `constraints.max_count` | `payment.agent_recurrence` `max_occurrences`. |
| `permissions.substitution: false` | One acceptable item per line. |
| `expires_at` | `exp`. |
| `capability_digest` | No equivalent. The closed checkout mandate binds the checkout itself, which is stronger for the transaction. |

AP2 checkout and payment mandates meet requirement 1 by construction. Requirements 2
and 3 have to come from the commerce protocol that carries the mandates.

### What this means for ADDP

- ADDP should not define its own payment authorization. The intent stays as the
  runtime's local record; where AP2 is available, a binding can express it as open
  mandates, and then parties other than the runtime can check the limits (draft section
  "Limits Across Runtimes").
- An ACP binding needs an ACP extension for requirement 1. ACP has a proposal process
  for such changes.
- The runtime rules (reserve before sending, "unknown" after a lost response, resend
  only under the same identifier and only while the service keeps it) are not covered by
  either protocol and remain ADDP's contribution, together with discovery across
  merchants.
- ACP product feeds and ADDP feeds serve different directions: ACP feeds are pushed to
  one agent platform; ADDP feeds are pulled by any index and come with query semantics.
  If the ACP proposal gains deletions and deltas, the two could share a record format.

### Payment allowance: Stripe Shared Payment Tokens

- Issued with `usage_limits[currency]`, `usage_limits[max_amount]`,
  `usage_limits[expires_at]` and a seller profile; states `active`, `requires_action`,
  `deactivated`; revocable. Example API version `2026-04-22.preview`.
- `max_amount` is a ceiling. It does not tie a charge to a quoted total. The draft's
  binding requirement 1 (reject an operation that does not match the current quote)
  therefore has to be met somewhere else, and a binding must say where.
- Source: <https://docs.stripe.com/agentic-commerce/concepts/shared-payment-tokens.md?agent-seller=agent>

### Names

- `/.well-known/addp` was not in the IANA registry on 2026-09-27.
- The acronym ADDP is also used by Digi International's Advanced Device Discovery
  Protocol, a UDP protocol for finding devices on a local network. Different field, no
  technical overlap.

## Not yet reviewed

The works below were discussed while the design was drafted but have not been checked
against their current specifications, so the draft makes no claims about them. They are
listed in the order they should be reviewed, with the question each review has to
answer.

| Work | Area | Question for ADDP |
|---|---|---|
| MCP and WebMCP | Tools that models call, on servers and in web pages | Can a query endpoint or an execution binding be offered as a tool without losing the guarantees? How much do tool definitions add to the model's input? Is "not a tool-calling interface" the right boundary? |
| Web Bot Auth | Identifying automated clients to websites | Should indexes and runtimes use it when fetching feeds and resources? Can publishers use it for rate limits and indexes for binding cursors to clients? |
| schema.org Actions | Actions described in page markup | Do capability documents duplicate it? Can `offer-search/0.1` facts map to schema.org Offer properties without changing their meaning? |
| llms.txt | Site content prepared for language models | Does it overlap with the manifest or feeds at all, or only with documentation? |

ACP and AP2 were reviewed first (see above). Each further review adds a section under
"Checked" with the version, date and sources, a row in the summary table, and, where
the answer changes the design, an issue against the draft. Checkout in UCP was not part
of the UCP review; whether it meets the binding requirements, alone or with AP2, is the
next question for the execution side.
