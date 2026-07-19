# Evaluation Dataset Governance

## Purpose

Agent-Ops evaluation datasets are trusted reference material. A case can influence
regression gates, architectural decisions, and future model selection, so promotion
requires more than adding a fixture that makes the current implementation pass.

This policy defines how evaluation evidence is sourced, sanitized, labeled,
reviewed, versioned, promoted, corrected, and retired. It applies to every artifact
under `evals/datasets/` and to raw evidence considered for future inclusion.

## Governing Principles

1. Prefer synthetic evidence when it can represent the behavior faithfully.
2. Treat repository contents, logs, test output, screenshots, and metadata as
   untrusted and potentially sensitive.
3. Do not transfer workplace, customer, or private-repository material into this
   repository without explicit authorization. Recreate the behavior synthetically
   when permission is uncertain.
4. Keep the trusted label independent of the implementation being evaluated.
5. Preserve the failure signal while removing information that is not necessary to
   evaluate it.
6. Commit only reviewed, minimized evidence. Raw source material stays outside Git.
7. Never change dataset membership or trusted labels without creating a new dataset
   version and regenerating the accepted baseline.
8. Automated scanners assist review but do not establish that evidence is safe.

## Source Types

Every case records one of the `EvaluationSourceType` values already enforced by the
Pydantic case models.

| Source type | Meaning | Promotion requirement |
| --- | --- | --- |
| `synthetic` | Hand-authored evidence that does not reproduce private source material | Review semantic realism and confirm that no real identifiers were copied |
| `sanitized_real` | Evidence derived from an authorized real execution and transformed into a safe fixture | Record authorization, sanitization actions, residual-risk review, and trusted labeling |
| `regression` | A minimized case preserving a previously observed Agent-Ops failure | Record the behavior being protected and whether its evidence is synthetic or sanitized |

`regression` describes why a case is retained; it does not exempt the case from
sanitization. A regression derived from private evidence must satisfy every
`sanitized_real` control before promotion.

## Required Provenance

### Dataset-level provenance

Each dataset must retain:

- a stable dataset name;
- an immutable version identifier;
- its intended evaluation target;
- the ordered case identifiers included in that version;
- the change rationale in the promoting pull request; and
- the full commit or staged-tree SHA used to generate each report.

The executable dataset object owns the name, version, and ordered cases. The pull
request records why a version changed and which review gates were completed.
Generated reports record the dataset identity and system version but remain local
artifacts unless a later policy explicitly promotes them.

### Case-level provenance

Every promoted case must have:

- a stable, non-identifying `case_id`;
- a `source_type`;
- a description of the behavior represented;
- a trusted expected result created independently of the evaluated implementation;
- only the minimum input and evidence needed to preserve that behavior; and
- notes for ambiguity, sanitization, adjudication, or regression rationale when
  applicable.

For `sanitized_real` and privately derived `regression` cases, the pull request must
also state:

- the source class, such as local pytest output or an authorized application log;
- who or what authorized reuse, without copying confidential approval text;
- which sensitive fields were removed or substituted;
- how the sanitized case was checked for residual identifiers and secrets; and
- how the trusted label was established.

Do not commit a source-to-placeholder mapping, private repository URL, internal
ticket URL, employee name, customer name, or other breadcrumb that can reconstruct
the original source.

## Raw Evidence Handling

Raw real-world evidence is candidate material, not part of the trusted dataset.

- Keep it outside the repository and Git working tree.
- Store it only in an authorized, access-controlled location for as long as review
  requires.
- Do not paste it into issues, pull requests, chat transcripts, test failure output,
  or generated evaluation reports.
- Do not use a public or personal repository as a transfer mechanism for workplace
  evidence.
- Delete the working sanitization copy after promotion or rejection according to
  the source environment's retention requirements.

When raw evidence cannot be handled safely in the project environment, create a
synthetic case from a behavior description instead of moving the evidence.

## Sanitization Procedure

### 1. Confirm authority and necessity

Before copying any real evidence, confirm that reuse is permitted and that a
synthetic case would not be sufficient. Lack of a clear answer means the evidence is
not eligible for promotion.

### 2. Minimize first

Extract only the lines, fields, and structure needed to reproduce the diagnostic
behavior. Remove unrelated stack frames, environment dumps, request bodies,
headers, source code, timestamps, and surrounding log traffic before applying
substitutions.

### 3. Remove prohibited content

Committed evaluation data must not contain:

- passwords, API keys, access tokens, session cookies, private keys, certificates,
  connection strings, or authorization headers;
- customer, patient, employee, account, or other personal information;
- private source code or proprietary business data;
- internal repository names, ticket identifiers, hostnames, domains, IP addresses,
  database names, bucket names, or filesystem locations;
- private URLs, query strings, request or response bodies, or trace identifiers;
- machine names, usernames, email addresses, home directories, or device metadata;
  or
- embedded metadata in images, archives, reports, and other binary artifacts.

### 4. Substitute consistently

Use obvious stable placeholders such as `<USER>`, `<REPOSITORY>`, `<HOST>`,
`<TOKEN>`, and `<RESOURCE_ID>`. Preserve only structural details that affect the
behavior being evaluated.

Do not use realistic replacement credentials or personally identifying fake data.
Do not replace a sensitive value with a placeholder that accidentally introduces a
classifier marker or changes the trusted category.

Normalize paths when their structure matters. For example:

```text
/home/responsible_party/private-product/tests/test_checkout.py
```

can become:

```text
/workspace/project/tests/test_feature.py
```

### 5. Inspect all representations

Review the sanitized text, serialized model, diff, and rendered artifact where
applicable. Search for credential patterns and residual source identifiers. For
images or binary reports, remove metadata and verify that redaction is flattened and
cannot be reversed. Prefer recreating a minimal synthetic artifact over editing a
sensitive original.

### 6. Revalidate semantics

Run the relevant parser, normalizer, classifier, or command-policy evaluator against
the sanitized candidate. Confirm that sanitization preserved the intended signal and
did not add unsupported evidence.

### 7. Perform a separate review pass

The sanitizer must complete the promotion checklist after stepping away from the raw
source. Sanitized real evidence should receive a second human review when available.
If independent review is unavailable, record that limitation and keep the case out
of high-trust release gates until it is reviewed.

## Trusted Labeling and Adjudication

Expected results must be assigned from the failure taxonomy, command policy, or
another documented contract—not copied from the current Agent-Ops output.

- Label the minimized evidence before running the candidate implementation when
  practical.
- Prefer a broad category or explicit abstention when the evidence does not support
  a specific cause.
- Record competing signals and the precedence rule used to resolve them.
- When reviewers disagree, keep the case in candidate status until the disagreement
  is resolved against the documented contract.
- Do not change an expected label merely to make an evaluation pass.

A corrected trusted label creates a new dataset version and requires a new baseline.
Historical reports keep their original dataset identity.

## Promotion Lifecycle

Cases move through the following states outside or through Git:

| State | Required outcome |
| --- | --- |
| Candidate | Behavior and proposed evaluation purpose are documented; raw evidence remains outside Git |
| Sanitized | Only minimized, permitted content remains and residual-risk checks are recorded |
| Labeled | Expected results and evidence requirements are established independently |
| Reviewed | Provenance, safety, realism, and label correctness pass the checklist |
| Promoted | The case is merged in a new immutable dataset version with a regenerated baseline |

A case is promoted only through a focused pull request. Promotion requires:

1. completed provenance and sanitization statements;
2. a stable case identifier and explicit source type;
3. successful Pydantic validation;
4. independent trusted labeling or recorded adjudication;
5. focused tests for any new parsing or metric behavior;
6. the full test, lint, formatting, and whitespace checks;
7. classification and command-safety evaluations as applicable;
8. review of candidate-versus-baseline changes; and
9. a dataset version increment and regenerated accepted baseline.

## Dataset Versioning

Dataset versions use semantic versioning and are immutable after merge.

- **Patch:** Clarifies non-behavioral metadata without changing inputs, case order,
  expected results, or metric requirements.
- **Minor:** Adds cases or additive evidence requirements while preserving existing
  case identifiers and trusted meanings.
- **Major:** Removes or renames cases, changes trusted labels, changes case meaning,
  or introduces an incompatible schema or policy interpretation.

Any change to executable case inputs, expected outcomes, required markers,
forbidden markers, membership, or order requires a version increment. Never reuse a
version string for different dataset contents.

Baseline and candidate reports are comparable only when their dataset name, version,
case identifiers, and expected categories match. After promotion, generate a new
accepted baseline from the merge commit SHA; do not relabel an older report.

## Promotion Pull-Request Checklist

Copy this checklist into a dataset promotion pull request:

The repository also provides
[`dataset-promotion.md`](../.github/PULL_REQUEST_TEMPLATE/dataset-promotion.md) as a
complete promotion template.

```markdown
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
```

## Correction, Quarantine, and Removal

If a promoted case is mislabeled, ambiguous, unsafe, or no longer representative:

1. stop using the affected dataset version as a release gate;
2. document the affected case IDs without repeating sensitive content;
3. correct, replace, or remove the cases in a new dataset version;
4. regenerate the accepted baseline; and
5. retain the old version only when it is safe and useful for historical report
   interpretation.

If committed data may contain a real credential or other sensitive value, treat it
as an incident. Revoke or rotate the credential first, restrict further exposure,
notify the appropriate repository or security owner, and follow an explicitly
approved history-remediation process. Deleting the value in a later commit is not
sufficient because it remains in Git history.

## Current Dataset Status

The Phase 1 failure-classification and command-safety datasets are version `1.0.0`
synthetic corpora. They do not contain promoted real-world evidence. Future dataset
changes must follow this policy before they become part of regression gates.

## Definition of Done

A dataset promotion is complete when its provenance is reviewable, its committed
evidence is minimized and safe, its labels are independent, its version is unique,
all deterministic checks pass, and a new accepted baseline can be reproduced from
the merge commit.
