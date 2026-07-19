"""Tests for deterministic command-policy evaluation."""

import json
from pathlib import Path

import pytest
from evals.datasets import COMMAND_SAFETY_DATASET
from evals.run_command_safety import main as run_command_safety_main
from pydantic import ValidationError

from agent_ops.evaluation import evaluate_command_safety
from agent_ops.models import CommandSafetyEvaluationDataset
from agent_ops.safety import is_test_command_approved


def test_command_safety_dataset_contains_approved_and_rejected_cases() -> None:
    """The trusted corpus should exercise both policy outcomes."""
    expected_decisions = {case.expected_approved for case in COMMAND_SAFETY_DATASET.cases}

    assert expected_decisions == {False, True}
    assert len(COMMAND_SAFETY_DATASET.cases) >= 10


def test_current_command_policy_passes_safety_dataset() -> None:
    """The current allowlist should match every trusted decision."""
    report = evaluate_command_safety(
        COMMAND_SAFETY_DATASET,
        system_version="test-version",
    )

    assert report.total_cases == len(COMMAND_SAFETY_DATASET.cases)
    assert report.passed_cases == report.total_cases
    assert report.approval_accuracy == 1.0
    assert report.unsafe_approval_count == 0
    assert report.safe_rejection_count == 0
    assert report.gate_passed is True


def test_unsafe_policy_decisions_fail_the_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Approving trusted-unsafe cases must produce a blocking report."""
    monkeypatch.setattr(
        "agent_ops.evaluation.evaluator.is_test_command_approved",
        lambda framework, command: True,
    )

    report = evaluate_command_safety(
        COMMAND_SAFETY_DATASET,
        system_version="unsafe-candidate",
    )

    assert report.gate_passed is False
    assert report.unsafe_approval_count == report.total_cases - 1
    assert report.safe_rejection_count == 0


def test_command_safety_dataset_rejects_duplicate_case_ids() -> None:
    """A command-safety dataset must identify every case uniquely."""
    duplicate_case = COMMAND_SAFETY_DATASET.cases[0]

    with pytest.raises(ValidationError, match="must be unique"):
        CommandSafetyEvaluationDataset(
            name="duplicates",
            version="1.0.0",
            cases=(duplicate_case, duplicate_case),
        )


def test_command_policy_requires_exact_framework_and_tuple() -> None:
    """Approval must not normalize or broaden repository-provided commands."""
    approved_case = COMMAND_SAFETY_DATASET.cases[0]

    assert is_test_command_approved(approved_case.framework, approved_case.command) is True

    for case in COMMAND_SAFETY_DATASET.cases[1:]:
        assert is_test_command_approved(case.framework, case.command) is False


def test_command_safety_entry_point_writes_passing_report(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The executable evaluation should persist output and expose its gate result."""
    report_path = tmp_path / "command-safety.json"

    exit_code = run_command_safety_main(
        [
            "--system-version",
            "tree:test-sha",
            "--output",
            str(report_path),
        ]
    )
    stdout_report = json.loads(capsys.readouterr().out)
    saved_report = json.loads(report_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert stdout_report["gate_passed"] is True
    assert saved_report == stdout_report
    assert saved_report["system_version"] == "tree:test-sha"
