# Architecture and roles

Normative module of [AMP 0.1](../SPEC.md).

## Identities and responsibilities

| Role | Authority | Required modules |
|---|---|---|
| Seller/publisher | Own catalog and offers; authorized catalog keys | Common, catalogs, registry, evidence, security |
| Index | Declared copies and search responses | Common, catalogs, search, registry read, security |
| Buyer runtime | Enforces recorded user permissions | Common, search, transactions, security |
| Checkout operator | Accepts orders for named sellers under a binding | Common, transactions, evidence, security |
| Registry gateway | Submits bounded delegated registration requests | Common, registry, economics, security |
| Evidence issuer | Attests facts within its declared competence | Common, evidence, security |
| Reputation service | Computes assessments under a disclosed policy | Evidence, reputation, security |
| Community | Reviews claims and moderates its own publications | Evidence, community, security |
| Content provider | Stores and serves authorized document versions | Catalogs, economics, security |

A participant MAY implement several roles. None inherits another role's authority
by doing so. A full blockchain node is not necessarily an index, archive or validator.

`Seller`, `Product`, `Variant` and `Offer` are different objects. A product identifies
a model under its issuer; a variant identifies a configuration; an offer identifies
a seller's commercial proposition. A product match across sources MUST NOT merge
sellers or treat their prices and policies as one offer.

`Offer.seller_id` names the seller. Optional `platform_id` names the marketplace.
`checkout_operator` names the actor accepting the order and `fulfillment_provider`
names an advertised provider when known. A binding MUST resolve responsibility,
payment recipient and accepted seller before charging. A platform cannot override
seller data or submit orders without the relevant delegation.

## Network selection and delegation

The locally accepted `NetworkDescriptor` identifies one network, its registry,
token, chain profile and bootstrap index descriptors. A different descriptor or
registry is not silently the same network. Multiple gateway URLs MAY access the
same registry. Bootstrap lists MUST be replaceable and manual configuration MUST
be possible. The descriptor's authenticity requires an out-of-band trust decision;
fetching its signature does not bootstrap that trust by itself.

Catalog owner and publisher keys are distinct from treasury/spending and admin
keys. The registry records authorized publishing key IDs. Catalog registration
and key changes MUST use owner authority as defined by the chain binding.
Managed delegation is bounded by catalog, operation, expiry and maximum charge;
revocation MUST stop new operations without erasing prior orders or history.

References to remote actors, mirror origins or checkout operators require explicit
delegation in the relevant binding. AMP does not disable ADDP same-origin rules by
claiming backward compatibility. Moving an endpoint does not silently transfer identity.

## Data paths and failure isolation

Registry -> catalog manifest -> snapshot and changes -> index -> agent candidates
-> seller quote -> authorized checkout -> events -> evidence/review.

The registry is the authority for registration state; a seller is the source for
its current commercial terms; payment/delivery issuers have authority only within
their external integrations. The index is a cached view with declared limitations.

An index MUST state source failures and coverage; it MUST NOT fabricate empty results
for unavailable sources. A failed background indexing or content task MUST NOT
silently spend more funds or expand a seller's delegation.

Public catalogs can be mirrored under explicit rights. Private orders and buyer
identifiers MUST NOT be included in public feeds. Reputation portability means
documents remain verifiable, not that every service must accept their conclusions.

## Versioning and extensions

Wire `0.1` supports only explicitly advertised capabilities. Negotiation selects
an exact supported wire version and a category profile version before queries.
Unknown required capabilities fail closed; optional unsupported extensions can
be ignored but MUST NOT be treated as fulfilled constraints.

The repository's draft version is not an operational network version. A network
descriptor binds its registry and chain profile versions separately. Registry
migrations require an explicit migration record and client acceptance; cached
trust MUST NOT automatically follow an arbitrary redirect or replacement contract.
