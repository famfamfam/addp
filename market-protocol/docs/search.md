# Agent search

Normative module. An index is a replaceable view, not an authority to spend or a
promise that every offer in the world has been considered.

## Discovery and routing

`IndexDescriptor` declares endpoint, network, category profiles, regions, supported
filters, coverage description, response limits, ranking policy and service terms.
Clients MAY use their own index, several independently operated indexes, or manual
bootstrap addresses. A descriptor MUST NOT grant trust to itself.

Select sources whose capabilities cover the request. Bound fan-out, elapsed time,
bytes and paid queries before dispatch. An unavailable source contributes an explicit
failure to the aggregate. Different data coverage legitimately produces different
answers. No single inclusion proof proves query completeness.

## Query semantics

`SearchQuery` contains one category profile, currency with `currency_exponent`, coarse destination region,
hard filters, separate preferences, optional text, selected fields and a limit.
Filters are ANDed; `in` accepts any listed value. Empty hard filters are allowed
for browsing. `eq`, `in`, `gte`, `lte` operate only on fields advertised by the profile.
The index MUST reject unsupported fields, operators, types or units; it MUST NOT
silently omit a requirement. Currency conversion is not implicit in 0.1.
The currency/exponent pair and `destination_region` are mandatory eligibility
conditions even when `hard_filters` is empty. A mismatching unit cannot be compared
as if its integer amounts used the query's scale. An unsupported pair rejects the
query; an offer with incompatible or unknown units cannot pass its price constraints.

The first profile is `laptops/0.1`:

| Field | Type / unit | Operators |
|---|---|---|
| `price.amount` | integer minor units in query currency | eq, gte, lte |
| `attributes.ram_gb` | integer GB (decimal gigabytes as advertised) | eq, in, gte, lte |
| `attributes.mass_g` | integer grams | eq, gte, lte |
| `attributes.storage_gb` | integer GB | eq, in, gte, lte |
| `attributes.screen_mm` | integer millimetres, diagonal | eq, gte, lte |
| `condition` | new, refurbished, used | eq, in |
| `delivery_regions` | membership in advertised coarse regions | in |

Region codes are versioned profile identifiers; the fixtures use `DE-BE` as an
illustrative subdivision. Warehouse region, delivery coverage, pickup location and
warranty region MUST NOT be conflated. Coarse coverage is only a preliminary claim;
actual address eligibility and delivery charges are checked in a quote.
An offer MUST advertise the requested destination region to pass this coarse test.
The optional `delivery_regions` filter adds a constraint; it does not override the
query's destination.

Absent/null source values produce `unknown`. Unsupported semantics produce
`unsupported`; a known failing fact produces `no_match`. None is a successful hard
match. A request requiring final delivered cost can remain unresolved until quote;
the index MUST NOT substitute item price for that total.

Text and semantic retrieval MAY nominate candidates. A runtime MUST validate every
hard filter against current typed facts before treating a candidate as qualified.
It MUST keep a condition unresolved if the fact cannot be established. Relaxing a
hard constraint requires buyer agreement, not an LLM inference.
Approximate retrieval that does not exhaustively evaluate the declared typed-filter
set MUST disclose that restriction and mark the result partial. Equal membership
across indexes is required only for exhaustive typed-filter evaluation on identical
data, profile and evaluation time, not for arbitrary semantic retrieval algorithms.

## Results and explanations

`SearchResult` includes query reference, selected snapshot, registry checkpoint,
source coverage, candidates, source failures, partial flag and optional next cursor.
Each candidate carries the offer identity/revision, observed and indexed times,
fact checks, sponsorship disclosure and seller lookup URL.
In 0.1, `select` is an advisory request for fields of interest; it does not permit
omission of fields required by the Candidate/Offer schemas. More compact projections
need a separate negotiated response shape. Do not claim field-projection savings here.

Each `ConstraintCheck` identifies the requested field, result, source and observation
time. The agent's explanation MUST distinguish source claims, verified integrity
and independently corroborated facts. “Best” MUST identify the considered sources
and preference policy; it MUST NOT mean an unverified global optimum.

An index MUST set `partial` if a required source failed, ingestion is incomplete,
or a computation budget truncated evaluation. Normal pagination is reported by
`next_cursor`; it does not by itself mean failed evaluation. Coverage declarations
are operator claims unless separately audited.

## Ordering, federation and cursors

The default `id/0.1` ordering is ascending Unicode code-point order of offer URI,
over the complete eligible set for the declared snapshot. Relevance order requires
an advertised policy ID and disclosure of sponsored treatment. Default ordering
is testable across implementations; relevance scores from different engines are
not directly comparable.

Deduplicate identical offer identities and revisions across copies. Keep offers
from different sellers separate even when model IDs match. If copies conflict,
re-check the publisher; do not select the cheapest conflicting value arbitrarily.
The runtime may rerank validated candidates using buyer preferences. Top-k samples
from several indexes do not establish the global top-k.

A cursor binds query, snapshot, network, ordering, principal and expiry. Page requests
MUST use the same query except its cursor. Expired or unavailable snapshots return
`cursor_expired`; silently paging a new snapshot is prohibited. Resource quotas may
require narrowing the query. A cursor is not permission to reveal another buyer's data.

## Finishing the task

The runtime creates a compact decision view after deterministic validation. Include
only needed candidates, differences, uncertainty and next permitted actions.
Instructions embedded in descriptions or reviews are untrusted data. Before ordering,
obtain a current [quote](transactions.md) and validate it against the buyer's intent.
