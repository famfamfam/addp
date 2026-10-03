# Moving and publishing the package

The planned public repository is `famfamfam/agent-market-protocol`. No repository
creation, push or release is performed by the generators or checks.

## Standalone use

Move this directory to any chosen location and run the README commands from its root.
All local links, generators, schemas and tests resolve relative to this package.
Recreate its virtual environment at the new path; virtual environments are not
portable artifacts. No parent ADDP code or private material is needed.

The nested `.github/workflows/checks.yml` becomes active when this package is the
repository root. While nested under ADDP, run its checks directly; the parent
workflow does not automatically execute this workflow.

## Before publishing

1. Run generators, `python tools/check.py` and `python -m pytest` in the package.
2. Inspect the exact files to be committed and verify the private-directory ignore
   rules. Git ignores do not prevent a filesystem archive from including local notes.
   Publish a tracked-file export, not an indiscriminate archive of the working copy.
3. Initialize/use the separate repository only after relocation or explicit preparation
   of an isolated checkout. Never overwrite an existing remote history.
4. Check the target name, license, author attribution, draft status and schema namespace.
   The bundle uses a URN identifier and does not need network access to resolve schemas.
5. Push the reviewed files and check CI before creating an optional prerelease tag
   `v0.1.0-draft.1`. Record actual check results, not assumed success.

Do not claim an IETF submission, production deployment, independent implementation,
audited contracts or real payment integration. Issues should request concrete
counterexamples and independent implementations. Public evidence levels remain
honest: test signatures are real, external demonstration events are simulated.
