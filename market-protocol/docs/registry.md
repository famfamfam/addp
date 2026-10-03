# Mandatory catalog registry

Normative module. One accepted network descriptor identifies the shared registry
for that network. Another deployment is a different network unless an explicit,
accepted migration joins their histories.

## On-chain and off-chain boundaries

The registry records `catalog_id`, owner, authorized publishers, manifest URL,
catalog revision, commitment, bounded routing hints, lease expiry and fee schedule.
It MUST NOT include buyer identities, private orders, full catalogs, media or reviews.
`commitment` is SHA-256 of JCS bytes of the unsigned `CatalogManifest` payload.
The manifest authenticates a snapshot descriptor digest; the descriptor authenticates
its parts. A commitment proves matching bytes, not that the statements are true.

The current off-chain head MAY advance beyond the last anchored revision. An index
MUST disclose both revisions and MUST NOT label unanchored data as included in the
checkpoint. Owner-authorized signatures authenticate those newer revisions; network
policy decides the permitted lag. Absence of a chosen chain policy is not permission
to call arbitrary unanchored updates finalized.

## Operations and authorization

| Action | Required authority | Effect |
|---|---|---|
| register | owner or bounded registration delegate | Create new identity and initial lease |
| publish | authorized publisher | Advance revision and commitment monotonically |
| renew | authorized payer/delegate | Extend lease under the referenced tariff |
| revoke | owner or explicit revocation delegate | End active publication, retain minimal history |

`RegistryOperation` identifies network, registry, operation ID, catalog, action,
expected revision, requested revision/lease, commitment, manifest URL, fee schedule,
payer and maximum token fee. Irrelevant optional fields MUST be absent; action-specific
requirements are semantic constraints. A managed gateway must not submit a request
outside its delegated action, expiry or spending bound.

One logical intention MUST NOT charge a second protocol fee on retry. Native gas
for failed transactions is separately possible and MUST be disclosed. Contracts
need chain-bound replay protection, expected-state checks and durable operation
identity; an HTTP gateway's deduplication alone cannot provide that property.

## Three separate clocks

- `lease_expires_at`: registered presence in the active network.
- Offer observation and `valid_until`: freshness of a published commercial claim.
- Quote `expires_at`: validity of personalized purchase terms.

Renewing a lease does not refresh cards or extend a quote. Expired/revoked registration
MUST be excluded from active network matches. Its historical documents and existing
orders remain governed by their own retention and service rules.

## Checkpoints and outages

`RegistryCheckpoint` identifies network, registry, chain profile, height, block hash,
observed time and finality. `CatalogRegistration` ties state to that checkpoint.
An index MUST disclose its checkpoint. It MUST NOT invent finality or renew leases
locally while the chain is unavailable. Stored views may be shown as historical or
degraded; an expired or unverifiable active registration cannot silently pass checks.

On a reorganization, an implementation invalidates affected derived registration
state, reapplies the accepted canonical history and marks impacted results. Existing
private orders do not disappear merely because publication state changed. Under a
binding with finality, conflicting finalized checkpoints trigger a halt in new
registration-dependent assertions and explicit incident recovery.

## Required concrete chain profile

This draft defines an abstract interface, not a transaction ABI. Before deployment,
a profile MUST specify chain identity, registry and token contract identities,
transaction/event encodings, proof verification, finality, checkpoint bootstrap,
reorg recovery, fee accounting, key/delegation binding and upgrade/migration authority.

It MUST provide actual light and pruned-full verification modes, state availability
and sync/resource measurements. A trusted RPC response is a managed mode, not a
light proof. The profile also specifies publication freshness policy, maximum
unanchored lag, finalized-state query and historical replay/snapshot requirements.

Fixtures use `urn:amp:chain:documentary:1`. This identifier names a documentary
scenario only: its block hashes and states are not blockchain proofs.

## Administration and availability

Document who can change fees, upgrade contracts, mint tokens, revoke delegates and
move treasury funds. Delays and recovery authorities MUST be explicit. Token ownership
or DAO terminology does not demonstrate decentralization.

Registration MUST use published technical rules and tariffs, not discretionary
approval by a sole catalog operator. Indexes may still apply their own disclosed
coverage and abuse policies. Fee payment neither compels unlimited storage nor
guarantees inclusion in every index. A missing catalog remains a data-availability
failure even with a valid registration proof.
