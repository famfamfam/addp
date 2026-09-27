# Publishing

State on 2026-09-27: ready to publish on GitHub as an experimental draft. Not yet
submitted to the IETF.

## What is checked

| Check | Result | Command |
|---|---|---|
| Schemas and examples | Valid examples pass; each invalid example fails with the expected error | `pytest tests/test_protocol.py` |
| Reference implementation | All tests pass: feeds, queries, resolution, fetch restrictions, sandbox execution and recovery | `pytest` |
| Draft matches the code | Every example in the draft is generated from a tested file; the measurement table matches `docs/measurements.json` | `pytest tests/test_draft.py` |
| Example digests | SHA-256 values in the examples match the files byte for byte, with LF line endings | `pytest tests/test_execution.py -k digests` |
| Rendering | xml2rfc renders TXT and HTML without warnings; ASCII only; no line over 72 characters | `python tools/build_draft.py` |
| idnits 2.17.1 | 0 errors, 0 flaws, 1 warning | see below |

The idnits warning says it cannot tell when the document was first submitted. That is
expected before the first submission.

## Publishing on GitHub

1. Create the repository `famfamfam/addp`. The schema `$id` values and the draft's
   Conformance section point to `https://github.com/famfamfam/addp` and to raw files on
   its `main` branch. If the repository gets another name, change `BASE` in
   `tools/generate_schemas.py` and the URL in the draft, then regenerate.
2. Commit everything that is not ignored. `notes/` is ignored on purpose: it holds the
   working notes and review reports from the design phase.
3. Push. The `checks` workflow runs the tests, verifies that generated files are
   committed, renders the draft, runs idnits and attaches the rendered draft as an
   artifact. It has not run yet; the first push is its first run.

## Submitting to the IETF

An Internet-Draft needs no approval to be posted. Becoming an RFC needs a stream (an
IETF working group, or the Independent Submission Editor), reviews and consensus.

Before the first submission:

1. **Contact.** The author block has only a GitHub URL. The IETF expects an e-mail
   address that stays reachable. Add it to `rfc/draft-kibin-addp-00.xml`.
2. **Where to discuss.** The first open question in the draft is whether ADDP should
   exist separately or become profiles of UCP, ARD and OAuth. Ask the UCP and ARD
   maintainers early. For new work in the IETF's Applications and Real-Time area, the
   usual first stop is the DISPATCH mailing list.
3. **Upload** `build/draft-kibin-addp-00.xml` (a single file with all includes
   resolved) at <https://datatracker.ietf.org/submit/>. The upload runs xml2rfc and
   idnits again. A draft expires after 185 days unless a new revision replaces it.

To run idnits locally:

```sh
curl -sSfL -o idnits https://raw.githubusercontent.com/ietf-tools/idnits/main/idnits
bash idnits build/draft-kibin-addp-00.txt
```

## Gaps reviewers will raise

They are listed in the draft's "Open Issues" appendix. They do not block a -00, whose
purpose is to start the discussion.

- Only a sandbox execution binding exists. It keeps quote and charge in one database,
  which is the easy case. No binding to a real checkout or payment protocol has been
  written.
- No task-level evidence that the model views keep decisions correct. The measurement
  shows fewer tokens on synthetic data only.
- One implementation. The first experimental question needs two independent indexes.
- Profiles cannot be added without a new protocol version; there are no registries.
- No hosting of manifests or feeds on another origin, and no signed feeds.
- Several related specifications have not been reviewed yet; see
  [prior-art.md](prior-art.md).

## Sources for the process

- [IETF: required content of an Internet-Draft](https://github.com/ietf/authors.ietf.org/blob/main/required-content.md)
- [IETF: naming an Internet-Draft](https://github.com/ietf/authors.ietf.org/blob/main/naming-your-internet-draft.md)
- [IETF: submitting an Internet-Draft](https://github.com/ietf/authors.ietf.org/blob/main/submitting-your-internet-draft.md)
- [IANA Well-Known URIs registry](https://www.iana.org/assignments/well-known-uris/well-known-uris.xhtml)
