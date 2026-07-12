"""Repository inspection capabilities."""

from agent_ops.repository.scanner import scan_repository
from agent_ops.repository.test_framework import detect_test_framework

__all__ = [
    "detect_test_framework",
    "scan_repository",
]
