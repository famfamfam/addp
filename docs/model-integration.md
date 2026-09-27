# Decision models in an ADDP runtime

Which part of an ADDP runtime a model can take over, how a typed decision model such as
Jev or Laya would be connected, and what to measure before claiming a benefit. This is a
design note, not part of the protocol. Nothing on this page is implemented yet.

## Where the model sits

```
index query -> runtime: hard constraints, ranking -> decision view -> model
                                                                        |
                            proposal: a handle, or "ask the user"  <----+
                                        |
runtime: Handles.get -> resolve_candidate (re-check at the publisher)
      -> user approval (Journal.approve) -> quote -> Runtime.run
```

The runtime does in code everything that has one right answer: currency, price limits,
required facts, the identity of the resource, the quote, the budget, the capability
digest and the state of the operation. The model is left with judgement: which of three
valid offers fits "quiet, for travel" best, or whether a listing really is the model the
user asked for.

If the user's criterion can be written as hard constraints plus a sort key ("the
cheapest new black one"), the runtime picks without a model.

[`tests/test_purchase_flow.py`](../tests/test_purchase_flow.py) runs this path with a
simulated model that always picks the first handle.

## Typed questions for a decision view

Jev and Laya answer three kinds of typed question against a shared state. The decision
view is already short, typed and free of credentials, so it can serve as that state,
rendered as text (Jev accepts text only).

| Need | Question | Options or levels | What the runtime does with the answer |
|---|---|---|---|
| Pick one offer for a subjective preference | Choice | The handles in the view, plus "none of these" | A handle: continue with the re-check. "None", or a top probability below the application's threshold: ask the user. |
| Order offers against a preference | Score, one question per handle | For example five levels from "does not fit" to "fits exactly" | Sort by score. The order is advisory. Score is a probability-weighted value and can be fractional; compare values, do not treat them as level indexes. |
| Check that a listing matches the request ("the XM6, not the XM5") | Noul | None | The probability that the statement is true. Below the threshold: drop the candidate or ask. Never a reason to skip a hard constraint. |
| Choose the next read-only step (search again, show details, ask the user) | Choice | Named steps the runtime offers | The runtime performs only steps it offered, and none that spend money. |

A Choice answer is one of the options it was given. With handles as the options, the
model cannot return an item that is not in the view, and there is no generated text to
parse.

## Rules

1. **The answer is a proposal.** The runtime resolves the handle with `Handles.get`
   (kind and expiry checked), re-checks the resource at the publisher, and executes
   only under a recorded intent and a matching quote. A model cannot create or change
   an intent.
2. **A probability is not permission.** Choice and Score return distributions and a
   confidence value; Noul returns a probability. Thresholds are the application's
   choice and have to be fitted on its own labelled data. Laya's README says it
   directly: confidence orders decisions, it does not show that a decision is correct.
3. **Always offer a way out.** Include a "none of these" option and send low-confidence
   answers to the user.
4. **Keep the option set small.** Laya's README notes that large option sets share one
   token budget and recommends shortlisting. The decision view already does this.
5. **Untrusted text stays untrusted.** Product names in the state can contain
   instructions aimed at the model. A typed answer limits what such text can achieve,
   but it can still steer the choice among valid options. The user's constraints bound
   the damage; they do not remove it.

## Hosted or local

| | Jev | Laya |
|---|---|---|
| Where it runs | Hosted API: `POST https://api.typesafe.ai/v1/systemone`, bearer token | Locally: Python SDK or a self-hosted HTTP service; its README also describes ONNX and browser paths |
| What leaves the machine | The decision view and the questions, including the user's stated preferences | Nothing, once the model files are downloaded |
| Credentials | An API key held by the runtime; never in the model's input or the journal | None for local use |
| API | Choice, Score, Noul; several questions per request | The same request format as Jev, with three differences its README lists (option budget, score levels, confidence semantics) |
| Limits stated in their documentation | Text input only. Latency and calibration figures are the vendor's and were not tested here. | Shipped checkpoints are over-confident; base checkpoints are near chance on typed decisions zero-shot; the English checkpoint "collapses outside English" and the multilingual one is weaker on English. |

## What to measure

[measurements.md](measurements.md) counts input size only. A useful comparison runs the
same labelled scenarios through several deciders:

- a rule in code (for example the cheapest offer that meets the constraints), as the
  baseline;
- a general language model given the decision view;
- Jev;
- Laya, run locally.

Scenarios: a subjective preference among valid offers; near-identical models (XM5 and
XM6); product names with injected instructions; no suitable offer, where the right
answer is to ask the user; and stale index data, which the re-check should catch before
any model sees it.

Metrics:

- rate of correct choices against the labels;
- how often the decider abstains, and how often the abstention was right;
- invalid proposals that reached execution (expected zero; this tests the runtime, not
  the model);
- latency, median and 95th percentile, including the re-check at the publisher;
- cost per completed task, including fallbacks to the user.

## Status

Not implemented. This project has made no calls to either API, and neither project has
reviewed or endorsed ADDP. A first step would be an adapter that turns a decision view
into a request and an answer into a handle or "ask the user", tested against recorded
responses, with no network access in the default test run.

## Sources

Checked on 2026-09-27.

- Jev: <https://docs.typesafe.ai/>, <https://docs.typesafe.ai/llms-full.txt>,
  <https://typesafe.ai/blog/introducing-system-one-models-and-jev>
- Laya: <https://github.com/NandhaKishorM/laya> (README of version 0.3.21; the code is
  licensed Apache 2.0, the licences of the model checkpoints were not checked)
