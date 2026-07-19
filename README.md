# Agent-Ops 🤖🔎

> A repository-aware AI evaluation and reliability system for diagnosing test failures, analyzing execution artifacts, and proposing evidence-supported improvements.

[![Project Status](https://img.shields.io/badge/status-active%20development-blue)](#project-status)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## Overview

Agent-Ops is a repository-aware engineering agent designed to inspect a codebase, execute approved tests, analyze failures, and produce traceable recommendations.

The project explores how coding agents can be made more reliable through structured evaluation, constrained tool use, evidence tracking, sandboxed execution, and human approval.

Rather than applying changes autonomously, Agent-Ops begins with a read-only diagnostic workflow. Proposed corrections remain reviewable, measurable, and reversible.

## Project Status

**Status:** Active development  
**Current phase:** Deterministic diagnostic reporting and evaluation baseline

The initial release focuses on:

- Repository discovery
- Approved test execution
- Structured test-result parsing
- Evidence-supported failure classification
- Diagnostic report generation
- Complete tool-call tracing

Failure classification is deterministic and local-first. Explicit execution
signals first produce broad outcomes, then high-confidence markers refine
import, collection, fixture setup, assertion, browser/environment, test-data,
and application failures. Confidence values are assigned by rule strength,
and missing evidence is reported rather than guessed.

Patch generation, sandbox verification, multimodal analysis, and the web console are planned for later phases.

## Current Workflow

```text
Inspect repository
        ↓
Detect the test framework
        ↓
Optionally run an explicitly approved test command
        ↓
Parse and normalize captured pytest evidence
        ↓
Classify the failure
        ↓
Return a structured diagnostic report
```

## Structured Diagnostic Output

The CLI returns backward-compatible JSON containing the repository and detected test
framework. When an approved test command runs, the report also retains the raw
execution result and parsed summary, then adds normalized evidence and the supported
failure classification.

Report sections are emitted only when the workflow produced them. For example, an
unsupported framework can return a classification without claiming that a test
command ran. Inspection without `--run-tests` remains read-only and omits execution
and classification fields.

## Deterministic Evaluation

Generate one machine-readable report from each immutable system version. During
development, stage the intended candidate files and use the staged Git tree SHA. This
evaluates the exact proposed snapshot before creating a commit:

```bash
git add <intended-files>
git diff --quiet
git write-tree
```

`git diff --quiet` must succeed so the executing working tree matches the staged
snapshot. Use the returned tree SHA as `tree:<sha>`:

```bash
python -m evals.run_failure_classification \
  --system-version tree:<tree-sha> \
  --output evals/reports/candidate.json
```

Accepted baselines and post-commit CI reports use the full commit SHA instead. The
tree SHA and commit SHA are both immutable provenance identifiers; the tree form
exists specifically to gate uncommitted development safely.

Compare an accepted baseline with a candidate:

```bash
python -m evals.compare_failure_classification \
  evals/reports/<baseline>.json \
  evals/reports/<candidate>.json \
  --output evals/reports/<comparison>.json
```

The comparison validates the report schema and dataset identity, records aggregate
and case-level changes, and exits with status `1` when a previously passing case or
gated accuracy metric regresses. Duration changes are reported but do not block a
candidate because timing noise is expected.

Evaluate the exact command allowlist without launching any dataset command:

```bash
python -m evals.run_command_safety \
  --system-version tree:<tree-sha> \
  --output evals/reports/candidate-command-safety.json
```

The command-safety report records every expected and actual approval decision. The
runner exits with status `1` if the policy incorrectly approves an unsafe case or
rejects the trusted pytest command.

## Target Direction

Later phases may add evidence-supported recommendations, human-approved candidate
corrections, sandbox verification, persistent checkpoints, streaming, expanded
artifact analysis, and optional specialist agents. These capabilities will be added
only after their safety and evaluation contracts are established.

## Design Documentation

- [Architecture](docs/architecture.md)
- [Roadmap](docs/roadmap.md)
- [Failure taxonomy](docs/failure-taxonomy.md)
- [Evaluation strategy](docs/repository_aware_evaluation.md)
- [Architectural decisions](docs/decisions/)
