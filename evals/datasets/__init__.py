"""Trusted Agent-Ops evaluation datasets."""

from evals.datasets.command_safety_cases import COMMAND_SAFETY_DATASET
from evals.datasets.failure_cases import (
    FAILURE_CLASSIFICATION_DATASET,
)

__all__ = ["COMMAND_SAFETY_DATASET", "FAILURE_CLASSIFICATION_DATASET"]
