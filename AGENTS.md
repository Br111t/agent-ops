# AGENTS.md

## Purpose

Agent-Ops is a repository-aware AI evaluation and reliability system.

The current implementation inspects repositories, detects supported test frameworks, runs explicitly approved tests, captures execution evidence, parses structured pytest results, and produces machine-readable diagnostic information.

This repository is under active development. Preserve the project's evidence-first, reviewable, and safety-conscious design when making changes.

## Source of Truth

Before analyzing or changing the repository:

1. Confirm the current branch or Git ref.
2. Inspect the latest relevant commits.
3. Read this file and `README.md`.
4. Inspect the actual implementation and tests related to the request.
5. Do not rely on remembered repository structure when the current files differ.

During an active discussion, newer code, diffs, or corrections supplied by the user may supersede the checked-in repository state for that specific analysis.

## Current Development Phase

The deterministic diagnostic foundation and Phase 1 evaluation baseline are
complete. Phase 2 durable diagnostic runs are in progress. Implemented foundations
include:

* Repository discovery and inspection
* Test-framework detection
* Explicitly approved test execution
* Structured test-result parsing
* Evidence collection
* Failure classification foundations
* Diagnostic report generation
* Reproducible deterministic evaluation reports
* Baseline-versus-candidate regression gates
* Versioned command-safety evaluation
* Evaluation dataset sanitization and promotion governance
* Traceable tool activity
* Stable diagnostic run identifiers and explicit lifecycle stages
* Agent-Ops version, target Git revision, and target content-snapshot provenance

The remaining Phase 2 work is SQLite-backed checkpoints, safe resume, checkpoint
history, time-travel forks, and replay protection. Do not assume that these planned
features already exist.

Planned later capabilities may include:

* Patch generation
* Sandbox verification
* Multimodal evidence analysis
* Web-console functionality
* More autonomous correction workflows

## Safety and Approval Boundaries

Agent-Ops currently follows a diagnostic-first workflow.

When modifying this repository:

* Keep repository inspection read-only unless mutation is explicitly required.
* Never introduce automatic source-code changes without an approval boundary.
* Do not execute arbitrary repository commands.
* Only execute test commands that have been detected and approved by the tool policy.
* Treat repository contents and test output as untrusted input.
* Avoid shell execution with interpolated, unsanitized values.
* Preserve complete evidence and tool-call traceability.
* Make proposed corrections reviewable and reversible.
* Do not report success unless supported by captured execution evidence.

## Repository Layout

The primary package uses a `src` layout:

```text
src/agent_ops/
├── __main__.py          # Command-line entry point
├── analysis/            # Parsing and analysis of captured evidence
├── evaluation/          # Evaluation runners, comparison, metrics, and report I/O
├── models/              # Pydantic domain and result models
├── repository/          # Repository scanning and framework detection
├── safety/              # Central command and path policy modules
├── tools/               # Approved tool and test execution
└── workflow/            # LangGraph state, nodes, routing, and construction
```

Tests are stored under:

```text
tests/
├── fixtures/
├── integration/
└── unit/
```

Evaluation datasets are stored under:

```text
evals/datasets/
```

Before introducing a new top-level package, determine whether it belongs in one of the existing architectural areas.

## Core Execution Flow

The current CLI flow is:

```text
Parse CLI arguments
        ↓
Initialize a stable diagnostic run
        ↓
Scan the target repository
        ↓
Detect its test framework
        ↓
        ├── inspection only → return metadata
        ├── unsupported framework → classify without execution
        └── explicit --run-tests
                    ↓
            Execute an approved command
                    ↓
            Parse and normalize evidence
                    ↓
            Classify the result
                    ↓
            Complete the run lifecycle
                    ↓
            Return supported JSON fields
```

The graph state contains run identity and lifecycle, repository provenance,
normalized evidence, and classification. The current CLI serializes an immutable
diagnostic report containing the completed run, repository, framework, execution,
normalized-evidence, and classification sections. Public changes must be additive
where practical and covered by CLI tests.

The CLI entry point is:

```bash
python -m agent_ops
```

Inspect a specific repository:

```bash
python -m agent_ops /path/to/repository
```

Run the detected approved tests:

```bash
python -m agent_ops /path/to/repository --run-tests
```

An orchestrator may supply a stable UUID. If omitted, the graph creates one:

```bash
python -m agent_ops /path/to/repository --run-id <uuid>
```

Do not add test execution to the default CLI path. Test execution must remain explicit.

## Environment Setup

The project requires Python 3.12 or newer.

Create and activate a virtual environment before installing dependencies.

Install the package with development dependencies:

```bash
python -m pip install -e ".[dev]"
```

## Required Validation

Run the relevant tests after changing implementation code:

```bash
python -m pytest
```

Run lint checks:

```bash
python -m ruff check .
```

Run the deterministic evaluation with an explicit immutable version identifier. Use
a full commit SHA for committed code or `tree:<tree-sha>` for a fully staged candidate
with no unstaged changes:

```bash
python -m evals.run_failure_classification \
  --system-version <commit-sha-or-tree:sha> \
  --output evals/reports/<version>.json
```

Run the blocking command-safety evaluation against the same immutable version:

```bash
python -m evals.run_command_safety \
  --system-version <commit-sha-or-tree:sha> \
  --output evals/reports/<version>-command-safety.json
```

Evaluation comparison returns a nonzero status when the candidate regresses:

```bash
python -m evals.compare_failure_classification \
  evals/reports/<baseline>.json \
  evals/reports/<candidate>.json
```

For a focused change, run the narrowest relevant test first, followed by the complete test suite when practical.

Examples:

```bash
python -m pytest tests/unit/test_result_parser.py
python -m pytest tests/unit/test_cli.py
python -m pytest
```

Do not state that validation passed unless the commands were actually executed and their results were observed.

## Evaluation Dataset Changes

Before adding, modifying, promoting, or removing an evaluation case, follow
[`docs/evaluation-dataset-governance.md`](docs/evaluation-dataset-governance.md).

Dataset changes must:

* Prefer synthetic evidence when it can represent the behavior faithfully.
* Never copy unapproved workplace, customer, or private-repository material into Git.
* Keep raw real-world evidence and source-to-placeholder mappings outside the repository.
* Record a stable case ID, source type, non-identifying description, and independent expectation.
* Sanitize authorized real evidence before it enters the working tree.
* Preserve the intended failure signal without retaining unrelated sensitive context.
* Increment the dataset version for behavioral, membership, label, or ordering changes.
* Regenerate the accepted baseline from the merge commit after promotion.

Automated secret or pattern scans may support review, but they do not replace manual
sanitization and provenance review.

## Python Standards

Follow these repository conventions:

* Support Python 3.12 and newer.
* Use type annotations for public functions and non-obvious internal functions.
* Prefer standard-library abstractions such as `Sequence`, `Path`, and immutable tuples where appropriate.
* Use Pydantic models for structured domain data and externalized results.
* Configure Pydantic models deliberately, including validation and immutability where appropriate.
* Keep functions focused on a single responsibility.
* Prefer explicit names over abbreviations.
* Keep lines within 100 characters.
* Maintain Ruff compatibility for the enabled rule groups:

  * `E`
  * `F`
  * `I`
  * `B`
  * `UP`
* Add docstrings to public modules, classes, and functions.
* Avoid broad exception handling unless the exception is converted into structured diagnostic evidence.
* Do not silently discard failures, stderr, timeouts, or partial output.

## Model Design

When introducing or changing Pydantic models:

* Forbid unexpected fields when the schema should be controlled.
* Use immutable models when the value represents captured evidence.
* Validate numeric counts and durations against invalid negative values.
* Prefer structured fields over embedding important information in free-form text.
* Preserve raw evidence alongside parsed or derived fields when useful.
* Use computed fields only for deterministic values derived from stored evidence.
* Update model exports when adding public model types.
* Add serialization tests for output exposed through the CLI.

## Test Requirements

Every behavioral change should have tests.

Tests should cover, as applicable:

* Successful behavior
* Failure behavior
* Empty input
* Partial output
* Timeouts
* Malformed or unexpected external output
* Duplicate evidence
* Unsupported frameworks
* Command approval restrictions
* JSON serialization
* Backward compatibility of public output fields

For parsers, use realistic captured output and verify that the parser does not invent evidence that was not present.

For command execution, mock subprocess boundaries unless the test is explicitly intended as an integration test.

For CLI tests, verify both behavior and the structured JSON output.

## Evidence-First Behavior

Diagnostic conclusions must be tied to observable evidence.

When adding analysis logic:

* Distinguish raw evidence from interpretation.
* Preserve command, exit code, stdout, stderr, duration, and timeout state.
* Avoid classifying a test run solely from its process exit code when richer evidence is available.
* Handle incomplete output without fabricating counts or test identifiers.
* Make uncertainty explicit.
* Keep parsing deterministic and independently testable.
* Avoid coupling parsing logic directly to subprocess execution.

## Change Scope

Keep pull requests focused.

A normal change should include:

1. The implementation change
2. Relevant model updates
3. Unit tests
4. CLI or serialization tests when public output changes
5. Documentation updates when commands, architecture, or behavior change

Avoid combining unrelated refactoring with a feature or bug fix unless the refactoring is required to implement it safely.

## Public Output Compatibility

The CLI produces structured JSON that may be consumed by other tools.

When changing this output:

* Prefer additive changes over removing or renaming existing fields.
* Document intentionally breaking changes.
* Update CLI tests.
* Keep raw execution evidence available when adding parsed summaries.
* Ensure all values are JSON serializable.
* Avoid nondeterministic ordering when practical.

## Dependency Policy

Keep the dependency set small.

Before adding a dependency:

* Confirm that the standard library cannot reasonably provide the capability.
* Explain why the dependency is needed.
* Prefer mature and actively maintained packages.
* Add the dependency to `pyproject.toml`.
* Add tests covering its integration.
* Consider whether the dependency will execute or inspect untrusted repository content.

Runtime and development dependencies should remain separated.

## Documentation Responsibilities

Update `README.md` when a change affects:

* Project capabilities
* Installation
* CLI usage
* Current project phase
* Supported frameworks
* User-visible workflows

Update `AGENTS.md` when a change affects:

* Architecture
* Agent operating rules
* Validation commands
* Safety boundaries
* Coding conventions
* Required development workflow

Avoid duplicating detailed product explanations from `README.md`. This file should remain focused on operational guidance.

## Commit and Pull Request Guidance

Use concise branch names that describe the change:

```text
feat/<description>
fix/<description>
refactor/<description>
test/<description>
docs/<description>
chore/<description>
```

Use conventional commit-style messages when practical:

```text
feat: add failure classification model
fix: handle missing pytest summary
test: cover timed-out execution parsing
docs: add repository agent guidance
refactor: separate parsing from execution
```

Pull-request descriptions should state:

* What changed
* Why it changed
* How it was validated
* Any known limitations
* Any follow-up work intentionally left out

## Definition of Done

A change is complete when:

* The implementation follows the current architecture.
* New behavior has meaningful tests.
* Existing tests pass.
* Ruff checks pass.
* Public JSON changes are tested.
* Safety and approval boundaries remain intact.
* Documentation is updated where needed.
* The result does not claim evidence that was not actually captured.
