# Community review and moderation

Normative module. A community's conclusion applies under that community's policy;
it is not a global verdict or authority to seize funds.

## Objects

| Object | Purpose | What it does not establish |
|---|---|---|
| BuyerReview | Buyer-subject feedback with eligibility | Independence of that buyer |
| CommunityReview | Test or analysis without required purchase | An additional verified sale |
| ClaimCheck | Evidence-based examination of a specific assertion | Universal truth or subjective satisfaction |
| AbuseReport | Report of suspected violation | Proof of the allegation |
| ModerationDecision | Versioned decision under a named policy | Global blacklist or financial arbitration |
| Appeal | Request to reconsider a named decision | Automatic reversal |

`CommunityPolicy` declares reviewer selection, eligibility, conflicts/recusal,
required evidence, response/appeal periods, moderator authority and insufficient
reviewer handling. Authors MUST disclose known sponsorship, free samples, affiliate
payments and relevant relationships. The policy defines how such conflicts affect
review eligibility and display.

## Claim and decision lifecycle

A `ClaimCheck` moves from submitted to reviewing, then a conclusion of `supported`,
`contradicted` or `inconclusive`. Evidence references and reasoning accompany the
conclusion. “I find it uncomfortable” cannot be adjudicated as the same kind of
claim as “this unit weighs 1,200 grams.” Popularity votes are not measurement evidence.

A `ModerationDecision` names the subject, policy, reviewer identities scoped to the
community, evidence, action, reasons, revision and previous decision. Actions are
service-local: annotate, limit display, remove content or restore. The community
MUST NOT interpret a vote as authorization to debit tokens or cancel an external order.

An `Appeal` identifies the decision, appellant, grounds and evidence. Where possible,
different qualified reviewers consider it. If independent reviewers are unavailable,
the service MUST disclose that limitation. A successful appeal creates a linked
new decision; it does not rewrite the previous signed document. Assessments and
local display MUST be recomputed under the recorded policy version.

Conflicting communities can publish different supported conclusions. Clients retain
their source and policy choice; no fictitious consensus is inferred. The initial
procedure uses disclosed reviewers and evidence, not token-weighted fact voting or
payments contingent on favorable/unfavorable verdicts.

## Content lifecycle

Evidence may be private to authorized reviewers. Public summaries MUST omit sensitive
data. Removal of unlawful or personal content is compatible with retaining minimal
non-sensitive decision metadata where permitted. Replicas need a content-removal
notification policy; the protocol cannot guarantee erasure of uncontrolled copies.
