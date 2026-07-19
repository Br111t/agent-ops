"""Tests for evaluation report persistence and candidate comparison."""

import json
from pathlib import Path

import pytest
from evals.compare_failure_classification import main as compare_reports_main
from evals.datasets import FAILURE_CLASSIFICATION_DATASET
from evals.run_failure_classification import main as run_evaluation_main
from pydantic import ValidationError

from agent_ops.evaluation import (
    compare_classification_reports,
    evaluate_failure_classification,
    load_classification_report,
    write_evaluation_artifact,
)
from agent_ops.models import (
    ClassificationEvaluationReport,
    EvaluationCaseChange,
    FailureCategory,
)


def _report(system_version: str) -> ClassificationEvaluationReport:
    """Return a passing report for the checked-in dataset."""
    return evaluate_failure_classification(
        FAILURE_CLASSIFICATION_DATASET,
        system_version=system_version,
    )


def _report_with_one_regression(
    system_version: str,
) -> ClassificationEvaluationReport:
    """Return a structurally valid report with one regressed case."""
    report = _report(system_version)
    first_case = report.cases[0]
    regressed_case = first_case.model_copy(
        update={
            "actual_category": FailureCategory.UNKNOWN,
            "category_correct": False,
            "actual_abstention": True,
            "abstention_correct": False,
            "confidence": 0.5,
            "passed": False,
        }
    )

    return report.model_copy(
        update={
            "passed_cases": report.passed_cases - 1,
            "category_accuracy": (report.total_cases - 1) / report.total_cases,
            "abstention_accuracy": (report.total_cases - 1) / report.total_cases,
            "macro_f1": 0.95,
            "cases": (regressed_case, *report.cases[1:]),
        }
    )


def test_identical_candidate_passes_comparison_gate() -> None:
    """Equivalent results should pass regardless of their system identifiers."""
    comparison = compare_classification_reports(
        _report("baseline-sha"),
        _report("candidate-sha"),
    )

    assert comparison.gate_passed is True
    assert comparison.gate_failures == ()
    assert comparison.regression_case_ids == ()
    assert comparison.improvement_case_ids == ()
    assert comparison.passed_cases_delta == 0
    assert all(case.change is EvaluationCaseChange.UNCHANGED for case in comparison.cases)


def test_regressed_case_fails_comparison_gate() -> None:
    """A previously passing case should block the candidate."""
    baseline = _report("baseline-sha")
    candidate = _report_with_one_regression("candidate-sha")

    comparison = compare_classification_reports(baseline, candidate)

    assert comparison.gate_passed is False
    assert comparison.regression_case_ids == (baseline.cases[0].case_id,)
    assert comparison.passed_cases_delta == -1
    assert comparison.category_accuracy_delta < 0.0
    assert comparison.abstention_accuracy_delta < 0.0
    assert comparison.macro_f1_delta < 0.0
    assert any("case regression" in failure for failure in comparison.gate_failures)


def test_improved_case_does_not_fail_comparison_gate() -> None:
    """A candidate may improve a failing baseline without being blocked."""
    baseline = _report_with_one_regression("baseline-sha")
    candidate = _report("candidate-sha")

    comparison = compare_classification_reports(baseline, candidate)

    assert comparison.gate_passed is True
    assert comparison.improvement_case_ids == (candidate.cases[0].case_id,)
    assert comparison.passed_cases_delta == 1


def test_comparison_rejects_different_dataset_versions() -> None:
    """Reports from different corpus versions are not comparable."""
    baseline = _report("baseline-sha")
    candidate = _report("candidate-sha").model_copy(update={"dataset_version": "2.0.0"})

    with pytest.raises(ValueError, match="same dataset version"):
        compare_classification_reports(baseline, candidate)


def test_report_round_trip_validates_schema(tmp_path: Path) -> None:
    """Written reports should reload through the strict Pydantic contract."""
    report_path = tmp_path / "reports" / "candidate.json"
    report = _report("candidate-sha")

    write_evaluation_artifact(report, report_path)

    assert load_classification_report(report_path) == report

    invalid_report = report.model_dump(mode="json")
    invalid_report["passed_cases"] = 0
    report_path.write_text(json.dumps(invalid_report), encoding="utf-8")

    with pytest.raises(ValidationError, match="must match passed_cases"):
        load_classification_report(report_path)


def test_evaluation_and_comparison_entry_points_write_artifacts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Executable entry points should persist reports and enforce the gate."""
    baseline_path = tmp_path / "baseline.json"
    candidate_path = tmp_path / "candidate.json"
    comparison_path = tmp_path / "comparison.json"

    assert (
        run_evaluation_main(
            [
                "--system-version",
                "baseline-sha",
                "--output",
                str(baseline_path),
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert (
        run_evaluation_main(
            [
                "--system-version",
                "candidate-sha",
                "--output",
                str(candidate_path),
            ]
        )
        == 0
    )
    capsys.readouterr()

    exit_code = compare_reports_main(
        [
            str(baseline_path),
            str(candidate_path),
            "--output",
            str(comparison_path),
        ]
    )
    comparison_output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert comparison_output["gate_passed"] is True
    assert json.loads(comparison_path.read_text(encoding="utf-8"))["gate_passed"] is True


def test_comparison_entry_point_returns_one_for_regression(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The executable comparison should return a CI-friendly failure code."""
    baseline_path = tmp_path / "baseline.json"
    candidate_path = tmp_path / "candidate.json"
    write_evaluation_artifact(_report("baseline-sha"), baseline_path)
    write_evaluation_artifact(
        _report_with_one_regression("candidate-sha"),
        candidate_path,
    )

    exit_code = compare_reports_main([str(baseline_path), str(candidate_path)])
    comparison_output = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert comparison_output["gate_passed"] is False
