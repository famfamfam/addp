# Integration guide

Informative. This is a design-time guide, not an installer for an existing service.

## A seller's shortest path

1. Map the existing product export to Product, Variant and Offer. Keep IDs stable.
   Start with one supported category. Missing facts remain unknown.
2. Publish a manifest, complete snapshot and recoverable changes. Run document checks
   and inspect invalid fields, currency, units, deletions and freshness.
3. Choose a network profile once a concrete chain binding exists. Register the
   catalog directly or delegate bounded registration to a provider. Accept the
   explicit fee schedule and retain owner control and an exit path.
4. Submit/discover the catalog with suitable indexes. Check their declared coverage
   and per-source ingestion diagnostics; registration does not force every index to
   cover the catalog.
5. Connect current quotes and a supported checkout binding. Test changes of price,
   inventory, address and lost responses before enabling purchases.
6. Enable order-status and after-sales operations, then optional review/evidence roles.

| Integration level | Capability | Buyer-facing limit |
|---|---|---|
| Catalog | Search, compare, link to an offer | No guaranteed prepared checkout or confirmed order |
| Quote/handoff | Current conditions and prepared seller checkout | Human may need to finish; completion must be reconciled |
| Order lifecycle | Authorized order/status/after-sales binding | Only advertised actions are available |

Registration is required for all active network publication levels. Catalog-only
integration does not remove that requirement. It reduces commerce operations needed.

## Index operator

Select category/region coverage, accept a network descriptor and verified checkpoint,
load catalogs, validate snapshots, apply numbered changes and publish a descriptor.
Expose lag, rejected records, gaps, quotas and completeness limitations. Test rebuilding
without the former operator and switching clients to a second independently controlled
endpoint. A second instance of the same code checks availability, not independent
implementation interoperability.

The specification does not prescribe a database. A small pilot can use a conventional
database and full-text search; performance and resource claims need measurements.
Semantic retrieval is optional. Exact filters and current purchase checks remain required.

## Marketplace and agent application

A marketplace chooses roles and permitted catalog scope, keeping seller, checkout
and fulfillment responsibility explicit. Referral terms and customer-data access
are separate agreements. A buyer application configures accepted network/index
sources, records user permissions outside model control, validates facts, handles
unknown outcomes and presents concise explanations.

Measure first valid indexed offer, setup time, invalid-record rate, stale-offer rate,
hard-constraint violations, confirmed-order rate, recovery rate and incremental
seller margin. There is no claimed thirty-minute installation or guaranteed sales lift.
