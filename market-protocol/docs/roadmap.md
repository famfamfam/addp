# Technical roadmap

This roadmap concerns protocol and implementation readiness. Stages are acceptance
gates, not dates or promises of a deployed network.

| Stage | Deliverable | Exit criterion |
|---|---|---|
| 1 — This draft | Role contracts, schemas, examples, threat model and checks | Documents agree; executable checks pass; unimplemented bindings are explicit |
| 2 — Binding design | Concrete chain profile and real checkout/authorization mapping | Exact encodings, proof/finality rules, keys, recovery and permissions reviewed |
| 3 — Local/devnet reference | Publishers, indexes, runtime and simulated external services | Complete journey, failure recovery, full/light measurements and bounded test-token accounting |
| 4 — Independent implementation | Second independently developed role implementation | Shared conformance vectors agree on identical data; no parent/private dependencies |
| 5 — Controlled pilot | Chosen category, region, sellers and payment/logistics partners | Measured task completion, data quality, support and seller economics; security review |

## Blocking dependencies for implementations

The chain profile must choose the base network, registry/token encoding, finality,
proofs, real light/full modes, administrative powers, tariffs and state availability.
The token policy must contain actual deployment supply/allocation and control
disclosures before an operational network can be described. A fixed fee in a free
test asset demonstrates accounting only.

The checkout binding must enforce consent and exact quote acceptance with durable
idempotency and unknown-outcome reconciliation. Payment and logistics evidence
need actual source integrations. Review eligibility needs a private holder binding
and a disclosed issuer policy. These dependencies are not solved by a schema.

## Reference scenario and measurements

Use three sellers, one category, two index instances and a marketplace role. Demonstrate
manual/agent handoff, price changes, absent delivery, feed gaps, expired leases,
registry reorg, source outage, order timeout, refund, copied review and appeal.

Measure setup effort, resource use, freshness, query latency, hard-filter correctness,
model context size, human interventions and confirmed orders. Add adversarial review
tests with explicit false-positive and collusion limits. Do not infer real-chain
resource cost from a tiny devnet or user quality from token-count reduction alone.

Later category profiles, cross-border pricing, multi-seller carts and advanced
community-ranking algorithms require separate proposals. Core publication and search
contracts should remain engine-independent and rebuildable.
