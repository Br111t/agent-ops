# Evaluation Dataset Promotion

## Change summary

- Dataset:
- Previous version:
- Candidate version:
- Added, changed, or removed case IDs:
- Evaluation behavior this change represents:

## Provenance

- Source types included:
- Source class for any authorized real evidence:
- Reuse authorization confirmed by:
- Regression or adjudication reference, if applicable:

Do not paste raw evidence, confidential approval text, private URLs, internal ticket
identifiers, or source-to-placeholder mappings into this pull request.

## Sanitization and labeling

- Sensitive fields removed or substituted:
- Residual-data checks performed:
- How sanitization was verified not to change the intended signal:
- Contract used to establish expected results:
- Reviewer or adjudication outcome:

## Dataset governance

- [ ] Every case has a stable ID, source type, description, and independently assigned expectation.
- [ ] Reuse of any real evidence is explicitly authorized.
- [ ] Raw evidence and source-to-placeholder mappings remain outside Git.
- [ ] The committed fixture is minimized and contains no prohibited content.
- [ ] Sanitization substitutions preserve the intended diagnostic signal.
- [ ] Serialized and rendered forms were reviewed for residual sensitive data.
- [ ] Ambiguous labels were adjudicated against a documented contract.
- [ ] Dataset membership or behavior changes use a new version.
- [ ] Relevant tests, Ruff checks, and deterministic evaluations pass.
- [ ] Candidate-versus-baseline changes were reviewed case by case.

## Validation

- [ ] `python -m pytest`
- [ ] `python -m ruff check .`
- [ ] `python -m ruff format --check .`
- [ ] `git diff --check`
- [ ] Failure-classification evaluation, when applicable
- [ ] Command-safety evaluation, when applicable
- [ ] Accepted baseline regenerated from the merge commit after promotion
