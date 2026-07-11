Goals

Agent-Ops is intended to demonstrate practical patterns for:

Repository-aware coding agents
AI-assisted failure analysis
Agent and tool-use evaluation
Context engineering and reusable skills
Secure and constrained execution
Traceability and observability
Multimodal artifact analysis
Human-in-the-loop decision-making
Evaluator-driven experimentation
Core Capabilities
Repository Intelligence
Map repository structure and important configuration files
Identify languages, frameworks, test runners, and build tools
Search source code by file, symbol, dependency, and error message
Connect failed tests to relevant application and test code
Inspect recent Git changes when diagnosing regressions
Controlled Test Execution
Detect supported test frameworks
Run only explicitly approved commands
Capture standard output, errors, exit codes, and timing
Enforce execution timeouts and retry limits
Prevent unrestricted shell access

Initial support will focus on Python and pytest, followed by Java and JUnit.

Artifact Analysis
Parse structured test results
Review logs and stack traces
Associate failures with screenshots and browser artifacts
Inspect Playwright traces and test metadata
Preserve the evidence used to produce each conclusion
Failure Classification

Initial failure categories include:

Application defect
Test automation defect
Test-data defect
Environment or configuration issue
Dependency or build failure
Timing or synchronization issue
Unsupported scenario
Indeterminate failure requiring human review
Diagnostic Reporting

Each analysis produces a structured report containing:

Failure summary
Failure classification
Supporting evidence
Relevant files and symbols
Probable root cause
Recommended next steps
Confidence and uncertainty
Suggested verification steps

Example:

{
  "failure_type": "test_automation_defect",
  "summary": "The workflow continued after assignment extraction returned no results.",
  "evidence": [
    {
      "source": "test output",
      "detail": "Assignment list was empty before selection was attempted."
    }
  ],
  "affected_files": [
    "src/flows/assignment_flow.py"
  ],
  "recommendation": "Add an explicit assignment guard before selection and record a structured failure result.",
  "confidence": 0.88
}
Human-Reviewed Corrections

Planned correction workflow:

Generate one or more candidate changes.
Explain the evidence supporting each candidate.
Present a unified diff for review.
Require explicit human approval.
Apply the approved change in an isolated environment.
Run focused tests and regression checks.
Compare the result with the original baseline.
Preserve the full decision and execution history.

Agent-Ops will not merge changes automatically.

Evaluation Strategy

Evaluation is part of the system rather than an afterthought.

The project will measure:

Correct test-command selection
Failure-classification accuracy
Relevant-file identification
Evidence and citation quality
Unsupported-claim frequency
Recommendation usefulness
Tool-selection accuracy
Guardrail compliance
Test recovery after an approved correction
Latency, token usage, and execution cost
Consistency across repeated runs

Evaluation datasets will contain known repository failures with expected classifications, relevant files