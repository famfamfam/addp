# Catalog publication and index synchronization

Normative module. Each catalog has one `catalog_id`, an owner, an authorized
publisher and a stream identified by `epoch`. Registration is governed by
[the registry](registry.md); the availability of the source data is a separate duty.

## Publication objects

`CatalogManifest` names the catalog, publisher, epoch, head sequence, schema/profile,
full snapshot, delta endpoint, authorized mirrors and reuse terms. `Snapshot`
identifies one immutable snapshot through sequence `through`, with ordered part
URLs and SHA-256 digests. Each `SnapshotPart` carries the same catalog, epoch,
snapshot ID and boundary, and embeds offers and `tombstones`. Each tombstone retains
the offer ID and its highest deletion revision, without the removed offer contents.
`Delta` carries consecutive numbered
`Change` records: either an upsert with one complete offer or an explicit deletion.
A delta names its publisher; the registry must authorize that publisher for this catalog.

Only JCS bytes of the unsigned typed payload are hashed. Signed envelopes are
verified separately. Manifest and delta publications MUST be signed by an authorized
publisher. The authenticated snapshot descriptor authenticates each part digest; parts
need not each have a separate signature. Mirror URLs do not change IDs or digests.

`head` is the highest complete sequence known to the publisher. `through` is the
snapshot's included sequence. A part MUST NOT contain two records with the same
offer ID, including collisions between live offers and tombstones across parts.
All offers MUST belong to the advertised catalog, seller and category profile.
In 0.1 each catalog represents one seller; a marketplace publishes separate catalogs
for different sellers and needs a delegation binding for every represented seller.

## Installing a snapshot

1. Verify network registration, publisher authority, manifest signature and supported profile.
2. Fetch the descriptor and every required part within resource and URL limits.
3. Verify descriptor identity, expiry, part count, bytes/digests and structural rules.
4. Validate offer identities and reject duplicates across all parts.
5. Atomically replace the catalog's previous visible generation and set its cursor
   to `(epoch, through)`. Do not expose a half-built generation.

A failed install MUST leave the previous complete generation intact and mark its
freshness appropriately. A snapshot older than the visible sequence in the same
epoch MUST NOT roll back the index. Epoch changes require a new verified snapshot;
the client MUST NOT combine sequence numbers from different epochs.

## Applying changes

Starting at `(epoch, n)`, the next accepted sequence is `n + 1`. Apply a batch only
after verifying its catalog, epoch, signature, boundaries and full sequence continuity.
Applying the same batch again MUST be a no-op when its content matches. A conflicting
payload for an already seen sequence MUST be reported as a conflict, not overwritten.
If an older sequence's content is no longer retained, a receiver cannot assert that
a replay matches; it reports the verification limit and recovers from an accepted snapshot.
An older offer revision MUST NOT replace a newer revision. An upsert after deletion
requires a higher revision. Snapshots MUST preserve the highest revision of each
deleted identity in tombstones, so rebuilding does not permit old revisions to return.
Watermarks survive epoch changes for the lifetime of the catalog identity. Resource
quotas count live records and tombstones; retiring a catalog does not authorize
reusing its identities with reset revisions.
An upsert MUST NOT change the catalog's seller or category profile. The delta's
publisher MUST match the accepted manifest; publisher rotation requires a newly
authenticated manifest and registry authority before accepting its changes.

Missing history triggers recovery from retained changes or a fresh snapshot. A
publisher MUST advertise the oldest retained sequence. Notifications MAY accelerate
polling but MUST NOT be the only recovery mechanism. At each poll, compare the
manifest head with the locally applied sequence and record lag.

Snapshot `through` and the following changes MUST describe one continuous history.
The publisher MUST retain a valid handoff window or explicitly require a newer
snapshot. A downloaded snapshot is not current merely because its download just ended.
The snapshot boundary plus one MUST be at least `oldest_sequence`; otherwise the
advertised retained history cannot complete its handoff and a newer snapshot is needed.
Reinstalling snapshots MUST preserve known revision watermarks and reject changed
content at an unchanged revision. Sequence checks MUST be bounded by received record
count, never allocate memory proportional to an untrusted sequence-number range.

## Freshness, deletion and availability

Track separately the catalog revision, registry checkpoint, applied stream sequence,
last successful source check, offer observation and offer expiry. Renewal of the
registry lease updates none of the offer timestamps. Search policy MUST exclude
expired offers from current matches and report source lag/unavailability.

Deletion removes an offer from current search. It does not retroactively erase
legitimate private order records or minimal history. Privacy and retention rules
still apply to retained evidence. Media, reviews and arbitrary linked content MUST
NOT be fetched recursively just because a catalog mentions them.

Publishers MUST declare download limits and reuse rights. Indexers MUST enforce their
own object, byte, CPU and refresh quotas. Payment of a publication fee does not imply
unlimited ingestion or storage. An index SHOULD expose per-source diagnostics: accepted
revision, rejected document/reason, missing sequences, freshness and declared coverage.

## Rebuilding and changing operator

A fresh index MUST be able to reconstruct its declared subset from the accepted
registry checkpoint, available manifests, snapshots and deltas. It MUST NOT require
a proprietary export from the previous index. Loss of all authorized copies is a
data-availability failure; a ledger hash does not reconstruct their contents.

This contract governs observable state and queries, not the internal database.
Implementations MAY use SQL, inverted indexes or other engines. For the same verified
snapshot and exact typed filter, matching membership MUST agree; relevance ranking
may differ only under the declared ranking policy.
