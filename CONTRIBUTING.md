# Contributing

ADDP is an experimental draft. The most useful contributions right now are:

- **Design problems.** A case the protocol gets wrong, a requirement that cannot be
  implemented, an attack the security section misses. Open an issue with a concrete
  example: the messages involved and what goes wrong.
- **Evidence.** A second implementation of any role, an adapter for an existing
  catalog or checkout protocol, or task-level measurements of the model views. The
  experiment in the draft (section "What the Experiment Should Show") cannot succeed
  without them. A decision-model adapter measured as described in
  [docs/model-integration.md](docs/model-integration.md) counts too.
- **Prior art we missed.** If something already does part of this, say where and how
  far the overlap goes. [docs/prior-art.md](docs/prior-art.md#not-yet-reviewed) lists
  works that have not been checked yet (ACP, AP2, MCP and WebMCP, Web Bot Auth,
  schema.org Actions, llms.txt), each with the question a review has to answer.

## Changing the specification

The specification is [`rfc/draft-kibin-addp-00.xml`](rfc/draft-kibin-addp-00.xml).
Every normative change needs a matching change in the schemas, the examples or the
reference implementation, and a test. If a rule cannot be tested, say why in the pull
request.

Style for the draft text: short sentences, one requirement per sentence, BCP 14 key
words (MUST, SHOULD, MAY) only where a requirement is meant. Say what an
implementation does, not why the design is good.

Examples in the draft are generated. Do not edit `rfc/examples/` by hand; change the
fixture generator and rebuild.

## Checks

```sh
python -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt      # .venv/Scripts on Windows

.venv/bin/python tools/generate_schemas.py
.venv/bin/python tools/generate_examples.py
.venv/bin/python tools/build_draft.py        # also refreshes rfc/examples/
.venv/bin/python -m pytest
```

CI runs the same steps, checks that generated files are committed, and runs idnits on
the rendered draft.

## License of contributions

Contributions are accepted under the Apache License 2.0, the license of this
repository (section 5 of the license).

The specification is intended for submission to the IETF as an Internet-Draft. By
contributing text or ideas to the specification, you agree that they may be included
in such submissions under the IETF rules on contributions, BCP 78 and BCP 79
(summarized in the [IETF Note Well](https://www.ietf.org/about/note-well/)). If you
cannot agree to that, say so in the pull request before it is merged.
