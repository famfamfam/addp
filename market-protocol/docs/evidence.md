# Evidence, signatures and history

Normative module. Separate the claim, its integrity, the issuer's authority, the
independence of that issuer and the verifier's acceptance policy.

## Signed envelope

`SignedDocument` contains `payload` (a typed AMP document) and `jws` (JWS Compact
Serialization). Signing uses RFC 7515, JSON canonicalization RFC 8785 and the
fully specified `Ed25519` algorithm identifier from RFC 9864.

1. Reject duplicate JSON keys and values outside the common data model.
2. Canonicalize the payload with JCS. No home-grown JSON sorting substitute is allowed.
3. The protected header is exactly `alg`, `kid`, `typ`, with `alg: Ed25519` and
   `typ: amp+jws`. `kid` is an absolute key URI authorized for the payload role.
4. Serialize the header with JCS. Base64url encode header and payload without padding.
5. Sign ASCII `header64.payload64` using Ed25519. Append the base64url signature.

Verification MUST reject unexpected header members, unsupported algorithms, padding
or noncanonical base64url, a payload different from the embedded JWS bytes, a wrong
key, an unauthorized role or expired/revoked authority under the applicable policy.
Verify the original bytes and require them to equal JCS of the typed payload.
Never download a key just because untrusted `kid` points to it. Use trusted,
bounded key resolution and the [fetch policy](security-privacy.md).
For current-use verification, payload `issued_at` MUST NOT be in the future, and
the signing key MUST be valid at issuance as well as acceptable under the current
key-status policy. Backdating `issued_at` alone does not prove a historical signature
preceded revocation; historical acceptance requires the issuer policy and independent
time evidence where needed. Fixture signing cases specify their evaluation instant.

`KeyDescriptor` describes a public OKP Ed25519 JWK, owner, validity, status and
authorized roles. The signed key descriptor itself needs an established owner/key
binding; a self-signed descriptor does not establish legal identity or network ownership.
Registry owner authorization governs catalog publishing keys. Other issuers are
accepted through a configured `IssuerPolicy`. `kid` values MUST NOT be reused for
different key material. Rotation and revocation preserve historical provenance and
record the effective time; a new key cannot silently inherit a new identity's history.

SHA-256 digests are lowercase hexadecimal over JCS payload bytes. Catalog commitments
use the manifest payload. Quote digests use the quote payload. Hashes alone are
neither signatures nor proof that the external event occurred.

## Claims and presentations

`EvidenceStatement` binds issuer, subject/order/line, claim type, observation time,
evidence level, audience, nonce, expiry, source reference and optional superseded
statement. Verifiers MUST validate scope, event linkage, issuer role and policy.
Private presentations bind a verifier-provided audience and fresh challenge;
replays MUST NOT create a second event or disclosure permission. Repeated viewing
of a public signed document is not itself a duplicate purchase.

`simulated` is reserved for fixtures. `seller_asserted` means the seller says it
happened. `provider_attested` requires an authorized provider's own source. None by
itself establishes independent human ownership or honest product quality.

Corrections create a new statement referencing the old one; they MUST NOT silently
rewrite an immutable event. An issuer policy defines accepted claims, required
sources, key-status checks, historical acceptance and dispute handling.

## Observations

`PriceObservation` records offer, source, observed time, scope (public, personalized,
transaction), money, included charges and unknown external costs. Compare like scope,
currency and terms; do not call personalized quotes public price history.

`SalesObservation` records source, period, counting unit, observed count, returns
and overlap status. Multiple issuers for one payment do not create multiple sales.
If safe cross-source matching is unavailable, show separate counts and unknown
overlap instead of summing them as independent demand.

## Privacy and retention

Use buyer pseudonyms scoped to the issuer/review context; public cross-store tracking
is not required. Hashing a phone number or address is not anonymization. Public
evidence MUST omit addresses, credentials and raw payment identifiers. Authorized
verifiers may retain minimized private linkage subject to declared retention terms.

Each data type needs a retention basis, access policy, correction/deletion procedure
and backup policy. A public commitment does not justify keeping personal contents
forever. External copies may outlive deletion requests; do not promise universal erasure.

## Fixture boundary

The example key seed is public and deterministically derived from a test label.
Signatures are genuine Ed25519 test signatures. Seller/payment/delivery assertions
remain simulated; signature verification cannot turn a fabricated demonstration
event into a real transaction.
