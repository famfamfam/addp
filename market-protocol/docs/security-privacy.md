# Security and privacy

Normative module. Threat actors include malicious publishers, indexes, gateways,
buyer agents, colluding reviewers, compromised keys and unavailable infrastructure.

## Mandatory boundaries

- Treat descriptions, reviews, URLs and model output as untrusted data. They MUST NOT
  modify user intent, allowed endpoints, credentials, budgets or trust policy.
- Bind authorization to actor, operation, seller, amount, currency, terms and expiry.
  Separate registration spending, product purchasing and review publication.
- Authenticate each operational caller and scope status/cursor lookup to that caller.
  Signed public content does not replace service authorization.
- Enforce strict parsing, schema/profile versions, body limits, decompression limits,
  response deadlines, redirect limits and paid-query budgets before processing.
- Restrict remote retrieval to HTTPS with no userinfo, fragment or unexpected port.
  Reject loopback, private, link-local, multicast, reserved and cloud metadata targets
  for public-source fetches. Resolve and check every address, pin the checked address
  for the connection, and revalidate at each allowed hop to resist DNS rebinding.
  Automatic redirects are disabled in this profile; new endpoints require validation.
- Never follow arbitrary object references recursively. Keys, schemas and mirrors
  require bounded trusted resolution. A domain suffix match alone is insufficient.
- Store secrets outside catalogs, examples, logs and model context. Use separate
  keys/permissions for publication, transaction spending and administration.

Network-internal deployments need a separate explicit fetch policy; a seller URL
cannot opt the runtime into that policy. Schema `$id` values are identifiers, not
instructions to fetch schemas during validation.

## Threat handling

| Threat | Required behavior | Residual limit |
|---|---|---|
| Stale/false cheap offer | Mark freshness, recheck quote, enforce exact accepted total | A dishonest seller can still lie or fail fulfillment |
| Lost mutation response | Preserve unresolved operation, reconcile same ID | Needs a binding with durable atomic enforcement |
| Withheld search results | Disclose coverage/policy, permit alternate/self-hosted indexes | Signatures do not prove complete retrieval |
| Registry outage/reorg | Expose checkpoint, halt unsupported freshness/finality claims | Active registration depends on chain availability |
| Compromised key | Revoke/rotate with effective time and scoped policy | Historical truth may require investigation |
| Self-purchase/review ring | Disclosed weighting, evidence, investigation and appeal | No global proof of independent humans |
| Spam/huge catalog | Published quotas and bounded fees | Paid spam is still possible |
| Injected model instructions | Data-only handling and runtime-enforced permissions | Requires real host integration testing |
| Public personal evidence | Minimize/redact; authorized private access | Uncontrolled replicas may persist |

## Data access and retention

Public: catalog facts, registration metadata, index coverage, public policies and
minimized review/decision documents. Restricted: addresses, order details, payment
references, credential handles, buyer-subject linkage and reviewer-private evidence.

Share coarse region and needed filters early; disclose precise address only to the
selected authorized service. Do not broadcast the buyer's entire budget or private
preferences to every index by default. Log operation IDs and minimal diagnostics,
not secrets or complete private payloads.

Each deployed role MUST publish retention/deletion rules and permitted recipients.
An immutable chain commitment is not a justification for placing personal data
on-chain. Hashing predictable personal identifiers is not anonymization.

## What this repository verifies

Schema, signature and offline semantic checks are executable here. SSRF defenses,
authorization service enforcement, chain consensus, real payments, human independence
and production availability are not implemented. Their cases are acceptance
requirements for future bindings, not certified properties of this repository.
