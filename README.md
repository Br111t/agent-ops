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
**Current phase:** Repository inspection and failure-analysis foundation

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
```

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