# Quotes, orders and recovery

Normative module. A conforming flow keeps the same order when a buyer switches
between an agent and a human UI. Product payment is independent of registry fees.

## Current conditions and consent

`QuoteRequest` identifies seller, offer, revision, quantity, currency and destination
reference. The precise address is disclosed only to the selected authorized service.
`Quote` returns the offered revision, quantity, price breakdown, merchant total,
whether the delivered total is known, delivery window, terms digest and expiry.
Quote request, quote, permission and order request MUST agree on `network_id`.
The quote also carries `destination_ref`: a private, immutable reference bound by
the checkout to the resolved destination. A changed address requires a new reference
and quote; the old reference cannot silently resolve to a different address.

The operator MUST either honor the quote on acceptance or require a new quote. A
quote does not reserve inventory unless `inventory_reserved` is true and its binding
provides a reservation. Currency, exponent and all amounts MUST agree. The sum of
item subtotal, delivery, tax and negative discount MUST equal `merchant_total`.
External duties or charges MUST be listed as unknown when not included. If the
buyer requires a delivered-total ceiling, an unknown delivered total cannot satisfy it.

`Authorization` binds buyer principal, seller, checkout operator, permitted actions,
quantity ceiling, money limit, currency, terms digest, expiry and an opaque credential
reference. Purchase permission MUST name `offer_id`; cancellation and refund permission
MUST name `order_id`. A new offer or another order requires an appropriate new scope.
Purchase permission MUST bind `destination_ref`; if a delivery deadline is mandatory,
it MUST carry `delivery_deadline`. A quote for another destination or a later date
cannot use that permission. Additional private product constraints remain the
runtime's responsibility and MUST be rechecked before dispatch.
Review publication uses a separate role-specific authorization binding, not this
commerce permission. It MUST be recorded through a trusted buyer interaction. A model cannot
create or expand it. The operator MUST independently enforce an accepted authorization
binding; this document alone is not that binding.

An `OrderRequest` binds operation ID, quote ID and digest, authorization reference,
seller, quantity, currency and exact expected total. The operator MUST atomically
validate those conditions with order acceptance. A price change, new terms or expired
quote cannot be accepted by merely retaining the earlier authorization reference.
If changes exceed permission, get new consent. Payment credentials MUST NOT enter
model prompts or public order documents.

## Operation identity

Mutations require a client-generated URI `operation_id`. Its scope is the authenticated
principal, operator, operation kind and network. The operator stores a canonical
request digest with the outcome. Same key/same request returns the recorded outcome;
same key/different request returns `idempotency_conflict` and performs no new mutation.
Record the intent before dispatch and reserve its worst-case permitted budget.
The permission's money and quantity limits are cumulative across accepted and
unresolved purchases, not renewed for each operation ID. A shared enforcing ledger
MUST atomically account for existing reservations and completed spending before
accepting a new intention. A fresh operation ID does not reset consent. Successful
refunds do not automatically replenish permission; that requires explicit policy
and, when necessary, new consent.

An accepted operation returns `OperationStatus` with `pending`, `succeeded`, `rejected`
or `unknown`, plus a result reference when succeeded. Its status lookup MUST use the
same principal. Unknown or missing history MUST NOT be interpreted as rejected.
Retry the original operation ID; never create a replacement purchase merely on timeout.
Release reserved budget only after a trustworthy terminal result or binding-defined
reconciliation. Cross-device limits require a shared enforcing authority.

Each operator MUST advertise its deduplication retention window. Clients MUST stop
automatic retries beyond that window and reconcile manually. A binding MUST prevent
late original requests from creating an untracked second purchase; accepted request
expiry and durable outcome retention are part of its requirements. A short cache of
idempotency keys alone is insufficient.
Lookup/replay of a recorded outcome is distinct from validating a new purchase:
expiration of the original quote MUST NOT erase an already accepted outcome. For
a new dispatch, future-issued permissions/quotes MUST NOT be accepted as current.

## Independent state machines

| Object | States and transitions |
|---|---|
| Order | pending -> confirmed, rejected or cancelled; confirmed -> cancelled or completed |
| Payment | pending -> authorized, captured, failed; authorized -> captured or voided; captured -> partially_refunded or refunded; partially_refunded -> refunded |
| Fulfillment | pending -> shipped or cancelled; shipped -> delivered or failed; delivered -> returned |
| Refund | requested -> approved or rejected; approved -> paid or failed; failed -> approved for an explicitly recorded retry |

An accepted cancellation/refund **request** is not proof that the order was cancelled
or money refunded. Each `OrderAction` names the action, reason and operation ID.
The response is an operation status; authoritative events establish the eventual
outcome. Refunds must reference an order/payment and cannot exceed captured funds
net of earlier refunds. Partial refunds and quantities require line-level accounting.

`PaymentEvent`, `FulfillmentEvent` and `RefundEvent` each have an issuer, order/line
references, prior event reference where applicable, observed time, state and evidence
level (`simulated`, `seller_asserted`, `provider_attested`). A provider-attested label
is not credible without a verified authorized issuer and integration.

The first profile handles one seller and one offer line per order. It does not
promise atomic multi-seller checkout. Events MUST be deduplicated by their scoped
identity and external transaction binding, not by counting signatures or copies.

## Handoff and after-sales

`Order` exposes stable identity, current component states, revision and permitted
next actions. A trusted handoff link MUST resolve to the same order/checkout session
under authentication. The URL itself is not consent. Human and agent actions remain
separately authorized and conflict by expected revision instead of overwriting changes.

An agent may report “ordered” only after confirmed order state, and “paid” only with
the corresponding payment state. It MUST communicate pending/unknown outcomes and
the next recovery action. A buyer's purchase permission does not authorize publishing
a review, subscribing to marketing or disclosing additional personal information.

## Binding requirements

A production checkout binding must define authentication, authorization enforcement,
quote integrity, seller/payment-recipient binding, funds reservation, idempotency,
status reconciliation, webhook authenticity, event ordering, handoff and retention.
No such production binding is shipped here. UCP/ACP/AP2 mappings require a separate
versioned review and integration tests; similar field names do not prove compatibility.
