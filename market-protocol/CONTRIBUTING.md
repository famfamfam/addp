# Contributing

Start with a concrete scenario: the actors, input documents, expected outcome and
the rule that is missing or contradictory. This is an experimental draft.

Normative changes must update the relevant prose, schema, examples and conformance
case together. Use MUST, MUST NOT, SHOULD and MAY only for requirements (BCP 14).
Keep requirements per role: a seller need not implement a reputation service.

Schema source is `tools/generate_schemas.py`; example source is
`tools/generate_examples.py`. Regenerate with the commands in [README](README.md).
Do not edit generated JSON directly. Never use real buyer data or operational keys.

Run the package's own checks from this directory. It has no parent-repository imports.
Unimplemented integration cases must remain labeled documentary, not passed tests.
Do not add claims of compatibility, measured performance or fraud prevention without
reproducible evidence. Changes to network economics must identify payer, recipient,
budget and abuse cases.

Contributions are accepted under Apache-2.0. This package is not an IETF submission;
no IETF contribution process is established here.
