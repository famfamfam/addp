# Conformance and verification scope

Normative claims identify exact draft version, role, profiles, bindings and optional
extensions. An example passing JSON Schema is structurally valid, not a deployed
conforming role. [Architecture](architecture.md) lists role/module requirements.

## Check layers

| Layer | This repository | Does not establish |
|---|---|---|
| Structure | All message kinds have valid fixtures; negative fixtures check expected rejection | External facts, permissions or state evolution |
| Signatures | JCS/Ed25519 reproducible signing and verification; tampering/key-policy cases | Real issuer identity, holder independence or secure key custody |
| Offline semantics | Quote arithmetic, intent bounds, feed assembly/replay/gaps, typed filters, registration predicates | Running database concurrency, HTTP security or chain proofs |
| Documentation | Generated-file agreement, fixture inventory and local-link checks | Correctness of remote services or compatibility with other protocols |
| Deployment/integration | Documentary acceptance vectors below | A passed integration test |

Run `python tools/check.py` and `python -m pytest` from the package root. Evaluation
times are fixed explicitly so future expiry does not make fixture checks nondeterministic.
The `tools/validation.py` functions are offline assertions, not a production validator,
payment runtime, HTTP fetcher or blockchain client. Trust inputs are supplied by tests.

Pre-publication regression cases cover price units and destination filtering,
future-issued documents, network/address/deadline bindings, cumulative permission
usage, seller/publisher continuity, deleted revision retention, snapshot rollback
and bounded delta-range validation. Usage totals are trusted test inputs; atomic
reservation and durable deduplication still require an operator implementation.

## Requirement traceability

| Requirement group | Normative source | Example family | Verification |
|---|---|---|---|
| Independent, rebuildable catalog | catalogs | manifest, snapshot, part, delta | Executable digest/stream tests; independent implementation deferred |
| Same hard-filter meaning | search | query, search-result | Executable known/unknown/failing predicates; retrieval quality deferred |
| Current bounded purchase | transactions | quote, authorization, order-request | Executable offline condition checks; operator enforcement deferred |
| Unknown outcome and retries | transactions | operation-lookup/status | Executable request identity checks; durable service recovery deferred |
| Mandatory registry/token | registry, economics | network, registry-operation, registration, publication-payment | Structural/action/context checks; chain verification deferred |
| Light/full/managed distinction | node-profiles | network | Documentary chain-binding requirements; resource measurements deferred |
| Marketplace and referral roles | architecture, economics | offer-c, attribution | Structural checks; delegation and commercial settlement deferred |
| Evidence provenance/privacy | evidence, security | key, evidence, signed documents | Executable signing/presentation checks; external identity/privacy operations deferred |
| Portable reviews and refunds | reputation | eligibility, review, refund | Structure/version checks; holder linkage and aggregation deferred |
| Community and appeal | community | claim-check, decision, appeal | State/link shape checks; actual review process deferred |
| Service fees and abuse budgets | economics | fee, service-quote, token-policy | Arithmetic/asset checks; metering and profitability deferred |

## Documentary deployment vectors

Each future integration report must record input state, actor/authority, messages,
observed result and expected result. The following are **not executed** by this package.

| ID | Scenario | Expected result |
|---|---|---|
| D01 | Catalog is available but unregistered | Not presented as an active network offer |
| D02 | Lease expires; old catalog still reachable | Removed from active network matches; history remains subject to retention |
| D03 | Reorg removes a registration | Derived registry state is rolled back; checkpoint limitation is visible |
| D04 | RPC claims invalid inclusion | Real light client rejects the proof; managed client does not claim verification |
| D05 | Registry/gateway unavailable | No fabricated renewal/finality; existing orders remain separately accessible |
| D06 | Registration response lost and retried | Same protocol intention, no duplicate protocol charge; gas costs separately reported |
| D07 | Different network/contract replays a signed request | Domain-bound authorization rejects it |
| D08 | A provider exceeds paid query/storage quota | Work stops or a new agreement is requested; no unauthorized charge |
| D09 | Provider fabricates activity or multiple nodes | No automatic reward from an external budget |
| D10 | Index/source is down or withholds offers | Failure/coverage shown; alternate source possible; no completeness claim |
| D11 | Cursor snapshot evicted or query changed | Explicit expiry/conflict, no silently mixed pages |
| D12 | Buyer changes between human UI and agent | Same checkout/order identity; permissions and expected revision checked |
| D13 | Checkout commits, response is lost | Durable same-ID lookup returns the one accepted order |
| D14 | Quote expires while stock is being sold | Atomic rejection/requote; no substitute conditions silently charged |
| D15 | Cancellation or refund is requested | Request acknowledgement kept distinct from completed reversal |
| D16 | One review copied/edited or 100 units purchased | No new independent votes from copies, edits or quantity |
| D17 | Refund follows unfavorable review | Seller cannot erase it by refunding |
| D18 | Multiple issuers describe one transaction | Deduplicate only with reliable permitted linkage; otherwise report unknown overlap |
| D19 | Colluding wallets self-purchase | No claim of independent buyers from payment alone; evidence and limitations recorded |
| D20 | Sponsored reviewer or mass voting | Conflicts disclosed; votes do not substitute evidence or debit funds |
| D21 | Communities disagree; appeal succeeds | Separate sourced decisions; linked revision and local reassessment |
| D22 | Review contains private payment/address evidence | Minimized public content; restricted evidence handling |
| D23 | Injected instructions or endpoint/key substitution | No expanded authority, arbitrary fetch or secret disclosure |
| D24 | DNS rebinding, redirects or oversized response | Fetch/resource policy prevents unauthorized access/exhaustion |
| D25 | Key revoked or seller changes mode/provider | Scoped revocation and history preserved; no silent identity transfer |
| D26 | Original data and every replica are lost | Explicit unavailability; hash is not treated as recoverable content |
| D27 | Pruned full node runs out of resources | Explicit unavailability/service shedding; verification is not bypassed |
| D28 | Concrete payment/logistics adapter absent | Events remain simulated/unverified; no provider-attested claim |

## Independence and acceptance

Two processes using these same test helpers are not two independent implementations.
Before an interoperability claim, a separately developed implementation must pass
shared input/output vectors and report the data/checkpoint/profile used. Before a
real network claim, implement the chain profile and its proof/finality tests. Before
real purchasing, implement the authorization/checkout and external-event bindings.

No numeric fraud-prevention, uptime, revenue or setup-time guarantee follows from
passing these offline checks.
