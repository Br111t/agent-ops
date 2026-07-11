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

Patch generation, sandbox verification, multimodal analysis, and the web console are planned for later phases.

## Core Workflow

```text
Inspect repository
        ↓
Load relevant engineering skills
        ↓
Select and run approved tests
        ↓
Collect code, logs, screenshots, and traces
        ↓
Classify the failure
        ↓
Produce evidence-supported recommendations
        ↓
Propose candidate corrections
        ↓
Request human approval
        ↓
Test approved changes in a sandbox
        ↓
Measure and report the outcome
