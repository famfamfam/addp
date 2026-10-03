# Infrastructure fees and service accounting

Normative module. The network design requires a service token for catalog registration
and renewal. This document defines accounting duties; it does not define a deployed
asset, its market value or an income promise.

## Separate payment flows

| Flow | Payer -> recipient | Purchased service |
|---|---|---|
| Publication fee | Seller or explicitly authorized sponsor -> registry fee recipient | Registration/renewal for a period and resource class |
| Native gas | Transaction sender/sponsor -> base-chain mechanism | Chain transaction execution |
| Search service | Consenting application/client -> index operator | Agreed queries, subscription or availability commitment |
| Content service | Consenting publisher/client -> content provider | Bounded storage and delivery of permitted versions |
| Referral | Seller/platform -> agreed referring application | Attributed eligible order under a commercial agreement |

No flow implicitly pays for the others. The public `FeeSchedule` specifies asset,
resource class, duration, fee, recipient and validity. A `ServiceQuote` specifies
provider, client, unit, quantity, token charge, ceiling and expiry. Product money
and token base units MUST use different representations. A token symbol alone is
not an asset identity; chain and contract/asset identity MUST be bound.

Every paid operation requires consent to its price and limit. Metered charges MUST
remain within the agreed budget. Failed, partial and disputed service treatment,
measurement and retention MUST be included in the referenced service terms.
An accepted quote is not proof that service was delivered. Receipts, delivery records
and dispute procedures belong to the service binding.

## Initial accounting profile

For documentary/devnet examples use a fixed published test-token fee per period and
resource class. Test tokens have no market-value implication. Fees are bounded by
catalog/byte/update quotas; one catalog cannot buy unlimited indexing with one fee.
Fee changes require a new schedule/version and MUST NOT retroactively change an
accepted quote. The chain profile defines effective checkpoints and settlement.

No oracle, automatic inflation per query or unlimited activity reward is part of
0.1. Operators may be paid directly for agreed service. A seller may use service
receipts to pay its own fees only under explicit settlement rules. Running more
processes or signing requests to oneself MUST NOT automatically create a reward
claim against someone else's budget.

`TokenPolicy` records the asset, permitted use, fee/governance authority, mint
authority and links to supply/allocation/upgrade disclosures. Undecided deployment
values MUST be labeled undecided rather than filled with arbitrary numbers. A real
network profile cannot become operational without those disclosures and defined
contract permissions. Balance does not grant fact-checking authority or review weight.

## Referral and marketplace participation

`Attribution` names the referring application, commercial agreement and referral ID.
An order records accepted attribution before completion. Agreements MUST define
eligibility, precedence for competing claims, fraud handling, attribution window,
refund/clawback treatment and disclosure. AMP does not impose one global last-click
or multi-touch policy. The same order/claim MUST NOT be paid twice through copies.

A marketplace can keep checkout and service responsibility while accepting agent
referrals. It can also act as an index or fulfillment provider under separate terms.
Publishing through a marketplace does not authorize circumventing its seller
agreements or exporting private customer data.

Sponsored results and referral incentives MUST be disclosed to the buyer runtime.
They MUST NOT change factual attributes or silently relax buyer requirements.
Actual incremental margin and attribution quality require a pilot; traffic alone
does not establish value.

## Abuse and sustainability

Publication fees can raise spam cost but do not prove identity independence. The
economic cost of self-purchase is unrecoverable external expense, not the nominal
order value moved between colluding accounts. Refunds, subsidies and fee rebates
must be included in abuse analysis.

Any subsidy must identify a payer, finite budget, eligibility, decision authority,
end date and collusion model. No reward is implied by review count, wallets, requests,
nodes or token holdings. A payment for one's own request is not proof of demand.

Evaluate low demand, resource-cost growth, token price changes, concentration of
index operators and colluding providers. Record provider revenue, actual infrastructure
expense, freshness, failures and independently requested service. Free test tokens
cannot demonstrate profitability or economic spam resistance.
