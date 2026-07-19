# Failure Taxonomy

## Purpose

The failure taxonomy defines the meanings of Agent-Ops classifications and the
minimum evidence required to produce them. It is shared by the deterministic
classifier, evaluation datasets, diagnostic reports, and future model-assisted
analysis.

The taxonomy is conservative. It describes what the captured evidence supports,
not every possible root cause. A specific label must not be selected from intuition
when only a broad outcome is observable.

## Classification Levels

Agent-Ops currently produces four kinds of result:

1. **Successful or terminal outcomes** describe an observed execution result.
2. **Specific diagnostic categories** identify a cause supported by explicit local
   markers.
3. **Broad fallback categories** preserve a known pytest outcome when the cause is
   not supported.
4. **Uncertainty categories** identify missing, unsupported, or unparsed evidence.

## Current Categories

### Successful and terminal outcomes

| Category | Meaning | Minimum evidence |
| --- | --- | --- |
| `passed` | The approved command completed without reported failures or errors. | Exit code `0`; a recognized summary raises confidence. |
| `timeout` | The approved command exceeded its configured time limit. | Captured timeout state and duration. |
| `no_tests` | Pytest explicitly reported that no tests ran. | Recognized `no tests ran` summary. |

`passed` means that the observed approved command succeeded. It does not prove that
the repository is defect-free or that unexecuted tests would pass.

### Specific diagnostic categories

| Category | Meaning | Minimum evidence |
| --- | --- | --- |
| `import_error` | Test execution or collection failed because a module could not be imported. | A recognized `ImportError` or `ModuleNotFoundError`. |
| `collection_error` | Pytest failed while collecting tests. | Parsed collection error node or equivalent explicit marker. |
| `fixture_setup_error` | Test setup failed in fixture resolution or configuration. | `FixtureLookupError` or a fixture configuration path such as `conftest.py`. |
| `assertion_failure` | An assertion or expected/actual comparison failed. | `AssertionError` or an extracted assertion message. |
| `browser_or_environment_failure` | Browser startup, availability, session, connection, or runtime environment prevented execution. | A specific browser exception, or a generic environment exception paired with a browser-library traceback path. |
| `test_data_failure` | A data-related exception originated from explicit test-data or fixture input. | A recognized data exception paired with a test-data or fixture path. |
| `application_failure` | A non-assertion exception originated from application source. | An application exception paired with a non-vendored `src` traceback path. |

An `assertion_failure` does not determine whether the application or the test
expectation is wrong. That distinction requires additional repository and behavioral
evidence.

### Broad fallback categories

| Category | Meaning | Minimum evidence |
| --- | --- | --- |
| `test_error` | Pytest reported one or more errors, but no supported specific error marker was found. | Parsed error count greater than zero. |
| `test_failure` | Pytest reported one or more failed tests, but no supported specific failure marker was found. | Parsed failed count greater than zero. |

Broad fallbacks are valid conclusions. They preserve observed information without
inventing a more specific cause.

### Uncertainty and support boundaries

| Category | Meaning | Minimum evidence |
| --- | --- | --- |
| `unsupported_framework` | Agent-Ops cannot safely select an approved test command for the detected repository. | Framework detection returns `unknown`. |
| `unparsed_failure` | The command failed, but its output did not contain a recognized test summary. | Nonzero exit code and no recognized summary. |
| `unknown` | Available evidence is missing or does not match a supported rule. | Missing normalized evidence or no decisive status and summary. |

`unknown` and `unparsed_failure` are intentional abstentions. They should trigger
additional evidence collection or parser improvements rather than speculative
classification.

## Deterministic Precedence

Rules are ordered because one execution can contain overlapping markers. The current
precedence is:

1. Unsupported framework
2. Missing normalized evidence
3. Timeout
4. No tests
5. Parsed errors
   1. Import
   2. Collection
   3. Browser or environment
   4. Fixture setup
   5. Broad test error
6. Parsed failures
   1. Browser or environment
   2. Test data
   3. Assertion
   4. Application
   5. Broad test failure
7. Successful exit
8. Nonzero unparsed exit
9. Unknown

Changing precedence is a behavioral change. It requires focused classifier tests and
evaluation against the full versioned dataset.

## Confidence Semantics

Current confidence values represent the strength of a deterministic rule, not an
empirically calibrated probability that the classification is correct. For example,
a category selected from an exact exception marker receives higher confidence than
one inferred from an exception and a general source path.

Evaluation may later calibrate these values against a sufficiently large labeled
dataset. Until then, reports must not describe `0.95` as a measured 95 percent chance
of correctness.

## Labeling Evaluation Cases

Reference labels should follow these rules:

- Label the most specific category directly supported by the complete fixture.
- Include the evidence markers that justify the reference label.
- Use a broad fallback when the fixture establishes an outcome but not a cause.
- Use `unknown` or `unparsed_failure` when evidence is intentionally incomplete.
- Record whether a case is synthetic, sanitized real-world evidence, or a regression
  fixture derived from a reported defect.
- Do not derive the reference label by running the classifier being evaluated.
- Require human adjudication for ambiguous cases used as trusted references.

## Evolving the Taxonomy

Adding or changing a public category requires:

1. Updating `FailureCategory` and the deterministic classifier.
2. Adding positive, negative, ambiguous, and precedence tests.
3. Adding or updating evaluation cases.
4. Reviewing confusion with existing categories.
5. Updating this document and any public JSON examples.
6. Preserving compatibility or documenting an intentional breaking change.