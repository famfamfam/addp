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

The common gap: none of these defines how an index keeps a consistent copy of many
publishers' items, what a query over them means, or that a client must re-check an
index's claim at the origin before relying on it. None states what an agent must check
before spending the user's money. That is the part ADDP is an experiment about.

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

MCP and WebMCP, the Agentic Commerce Protocol (ACP), AP2, Web Bot Auth, llms.txt and
schema.org Actions were discussed while the design was drafted but not checked against
their current specifications. Claims about them do not appear in the draft for that
reason.
