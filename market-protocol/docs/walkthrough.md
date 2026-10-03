# Documentary purchase journey

All actors, orders, money movements, chain states and addresses below are fictional.
The example domains use `.example`; no network requests are needed. Test signatures
are valid cryptographic fixtures. The registry checkpoint is explicitly simulated.

## 1. Publish and register

Three sellers publish the same laptop configuration through separate offers.
Seller C's offer identifies a marketplace checkout and fulfillment provider.
See [seller A](../examples/valid/seller-a.json), [offer A](../examples/valid/offer-a.json),
[offer C](../examples/valid/offer-c.json), [manifest](../examples/valid/manifest-a.json),
[snapshot](../examples/valid/snapshot-a.json) and [part](../examples/valid/part-a.json).

The [registration intention](../examples/valid/registry-operation.json) accepts a
maximum charge under the [fee schedule](../examples/valid/fee.json).
[Registration](../examples/valid/registration-a.json) points to the manifest commitment
and [checkpoint](../examples/valid/checkpoint.json). The
[publication payment](../examples/valid/publication-payment.json) is simulated,
not a purchase of a laptop. No block hash in this example is a chain inclusion proof.

## 2. Build and update indexes

[Index A](../examples/valid/index-a.json) and [index B](../examples/valid/index-b.json)
declare the same documentary coverage. An offline checker verifies all snapshot
part digests before installing a generation. The
[upsert](../examples/valid/delta-upsert.json) and [deletion](../examples/valid/delta-delete.json)
are a separate update branch after the initial search snapshot. They demonstrate
revision advancement, replay and removal; they are not concurrently applied to the
initial quote branch below.

The [post-deletion manifest](../examples/valid/manifest-after-delete.json),
[snapshot](../examples/valid/snapshot-after-delete.json) and
[part](../examples/valid/part-after-delete.json) show a fresh rebuild with no live
offers. The deleted offer's revision remains in a tombstone, preventing an older
revision from reappearing after rebuild or epoch change.

If the second sequence is missed, the third cannot be accepted as if the stream
were complete. Rebuilding from the snapshot and applying the same changes produces
the same final records. The tests exercise this in memory; no search server runs.

## 3. Find and compare

The [query](../examples/valid/query.json) asks for EUR-priced laptops with at least
16 GB RAM and advertised Berlin delivery coverage. The item-price ceiling is
EUR 1,000. The runtime separately preserves the buyer's delivered-total ceiling.

The [result](../examples/valid/search-result.json) contains three offers, individual
constraint checks and coverage. Its simulated checkpoint makes it a documentary
result, not a valid live-network assertion. The runtime must explain that distinction.
Actual address delivery and total price are still unresolved at this stage.

## 4. Quote, authorize and confirm

[Quote request](../examples/valid/quote-request.json) obtains
[a quote](../examples/valid/quote.json): EUR 899 item subtotal plus EUR 10 delivery,
with no additional tax or discount line and no unknown external costs in this example.
The exact accepted total is EUR 909, under the EUR 1,000
[authorization limit](../examples/valid/authorization.json).

The quote and permission bind the same network and private destination reference.
The permission also limits delivery time. Its amount and quantity limits cover all
accepted and unresolved uses; a new operation ID does not reset the allowance.

The [order request](../examples/valid/order-request.json) binds the quote's digest,
quantity, permission and exact amount. [Attribution](../examples/valid/attribution.json)
identifies a disclosed referral agreement; it does not itself calculate a fee.

If the response is lost, the same operation is looked up using
[the lookup request](../examples/valid/operation-lookup.json). Only a resolved
[success](../examples/valid/operation-status.json) referencing
[the order](../examples/valid/order.json) permits “order confirmed”.
The authorization reference is deliberately non-operational. This is not a payment API.

## 5. Evidence, refund and review

The [payment](../examples/valid/payment.json), [delivery](../examples/valid/delivery.json)
and later [refund](../examples/valid/refund.json) each name their issuer and explicitly
carry `evidence_level: simulated`. An authenticated binding would establish those
facts in a real deployment. A [refund request](../examples/valid/refund-request.json)
uses a new [after-sales permission](../examples/valid/after-sales-authorization.json)
bound to this order; the purchase permission has expired. The request does not alone
establish the refund event.

[Evidence](../examples/valid/evidence.json) is presented to a named audience with a
challenge. [Eligibility](../examples/valid/eligibility.json) binds the order line and
buyer pseudonym. The [review](../examples/valid/review.json) remains one review if
copied to two services, and a refund does not grant the seller a deletion right.
Its claimed experience belongs to the fictional buyer, not to an agent.

## 6. Community and appeal

The [community policy](../examples/valid/community-policy.json) describes reviewer
selection and recusal. A [claim check](../examples/valid/claim-check.json) finds that
one documentary report cannot support a claim about all units.
[A decision](../examples/valid/decision.json), [an appeal](../examples/valid/appeal.json)
and [a replacement decision](../examples/valid/decision-after-appeal.json) preserve
the link between conclusions. No vote debits funds or globally blocks a seller.

The [assessment](../examples/valid/assessment.json) states its lack of real-world
evidence. A signed fictional statement is still fictional.

## Evaluating the fixtures

The base quote/authorization checks use `2026-10-03T12:00:00Z`. After-sales examples
describe later documentary events; they are not assertions that the initial order
already has those later states. Each service needs an event binding to construct a
current order projection. No such service is part of these fixtures.
Signed fixture cases specify their own evaluation times in `examples/cases.json`;
a later review cannot be accepted as already issued at the base purchase time.
