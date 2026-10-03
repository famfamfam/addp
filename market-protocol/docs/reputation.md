# Purchase reviews and reputation

Normative module. A verified signature is not proof of an independent buyer.

## Eligibility

`ReviewEligibility` binds issuer, order, line, seller, buyer pseudonym, policy,
evidence references, expiry and a stable eligibility ID. It MUST NOT expose raw
payment IDs or delivery addresses. Verification of the issuer and private holder
binding is required before accepting a buyer review as eligible.

`BuyerReview` references eligibility, seller, product/variant, subject pseudonym,
rating, text, experience basis, revision, prior revision and conflicts of interest.
The buyer subject owns the right; the purchasing software agent does not. Publication
requires a separate review permission. An agent MUST NOT claim personal experience
from a delivery log. `experience_basis` distinguishes buyer-reported experience,
order events and automated checks of specified facts.

## Counting and portability

Deduplicate by issuer-qualified eligibility ID and review identity. Edits and copies
in several stores are versions/copies, not votes. Multiple purchased units do not
automatically confer additional influence. Repeated purchases by the same subject
must be handled by a disclosed weighting policy, not unlimited vote creation.

If two issuers assert eligibility for the same transaction, a service may merge only
with authorized reliable linkage. Otherwise report overlap unknown rather than
counting them as demonstrably independent. Global identity correlation is not required.
Holder binding cannot completely prevent consensual resale of review rights or collusion.

A refund updates evidence and status; it MUST NOT give the seller unilateral power
to delete an unfavorable review. Corrections, privacy removal and moderation use
their own documented process. Public replication must respect the same content rights
and data minimization requirements as the original publication.

## Assessments and self-purchase

`ReputationAssessment` identifies subject, policy version, input references,
counts, overlap status, conclusion and limitations. There is no mandatory global
rating formula. Clients choose accepted services and policies. Token balances and
registration fees MUST NOT count as evidence of honest reviews or fact-check authority.

Policies can limit influence, consider transaction history and assess suspicious
relationships within a declared data scope. They MUST distinguish suspicion from
proof, explain adverse decisions and provide an appeal path. Wallet/account count
is not independent-human count. Self-purchase detection is probabilistic and cannot
be guaranteed by successful payment alone.

Claims of anti-abuse effectiveness require a defined threat model, labeled dataset,
false-positive measurements and residual limitations. Fixtures illustrate handling;
they are not a measured fraud-prevention system.
