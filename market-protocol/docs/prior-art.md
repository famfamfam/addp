# Prior art and compatibility boundaries

Review date: 2026-10-03. This is a scoped comparison, not proof that no other project
solves these problems. Links to moving branches are observations on that date, not
immutable version pins. An operational adapter must pin the exact specification.

| Source inspected | Relevant overlap | AMP decision and current limit |
|---|---|---|
| [ADDP 0.1, revision ab62132](https://github.com/famfamfam/addp/tree/ab62132eeddc454db86e2ad434129bf717cdd990) | Snapshot/change consistency, typed discovery, origin re-check and bounded execution | Preserve the invariants in a separate protocol. ADDP only accepts its declared profiles; AMP is not a new name for a compatible ADDP message. No parent code imports. |
| [UCP overview](https://ucp.dev/specification/overview/), [catalog search](https://ucp.dev/specification/shopping/catalog/search/), [checkout](https://ucp.dev/specification/shopping/checkout/) | Catalog search/filtering and checkout-session operations; current overview uses version 2026-08-25 in examples | Adaptation is plausible but not implemented. Recheck exact version, hard-filter semantics and transactional authorization before claiming compatibility. |
| [Beckn protocol specifications](https://github.com/beckn/protocol-specifications) | Cross-platform discovery and commercial interactions; repository version table lists Core 1.0.0 | Reuse lessons on separate buyer/provider roles. A complete field-level mapping and independent-index consistency comparison are still required. |
| [ONDC network extension](https://github.com/ONDC-Official/protocol-network-extension) | Network-specific layer over Beckn | Separate network policy from common document contracts. No ONDC network membership or wire compatibility is claimed; only repository overview inspected. |
| [ACP](https://github.com/agentic-commerce-protocol/agentic-commerce-protocol), published tree 2026-04-17 listed in README | Agentic commerce; repository lists checkout, cart, feed, orders, authentication and MCP work | This overlap includes more than payment. No detailed 2026-04-17 adapter or conformance assessment has been performed. |
| [AP2](https://github.com/google-agentic-commerce/AP2) | Agent-driven payment interoperability | Candidate authorization/payment binding; repository-level review only. No claim that an AMP Authorization is an AP2 mandate. |

## A concrete semantic mismatch to preserve

UCP catalog search documents situations in which a currency-related price filter may
be ignored, with a message. AMP hard constraints cannot be treated as fulfilled in
that case. An adapter must reject an unsupported mandatory filter or re-evaluate
the condition from adequate facts; text similarity alone is insufficient.
[Source: UCP price filter](https://ucp.dev/specification/shopping/catalog/search/#search-filters).

The reviewed UCP checkout overview also distinguishes user completion through a
trusted interface from authorization using its AP2 extension. AMP must map those
boundaries rather than infer unattended purchase authority from a discovered endpoint.
[Source: UCP checkout overview](https://ucp.dev/specification/shopping/checkout/).

These observations motivate adapter requirements, not a competing claim that AMP
invented catalog search or checkout. AMP's proposed combination is independent
index synchronization, strict agent constraints, the mandatory registry and
portable commerce evidence under explicit trust policies. Its usefulness requires
implementation and ecosystem validation.

## Cryptographic building blocks

- [RFC 7515](https://www.rfc-editor.org/rfc/rfc7515.html): JWS representation.
- [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785.html): canonical JSON bytes.
- [RFC 9864](https://www.rfc-editor.org/rfc/rfc9864.html): fully specified Ed25519 identifier.

AMP defines a narrow signing profile of these standards. The fixture verifier is an
offline test utility, not a general-purpose JOSE library or an audit of a service.

## Required follow-up before adapter claims

For each mapping, record source release/commit, represented operations, unsupported
fields, authorization and quote-binding rules, timeout/retry behavior and positive
and adversarial integration tests. Pay particular attention to current catalog/feed
developments in other protocols. Similar JSON fields or project descriptions do not
demonstrate compatible semantics.
