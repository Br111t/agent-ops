"""Command-line entry point for Agent-Ops."""

import argparse
import json
from collections.abc import Sequence

from agent_ops.repository import scan_repository


def build_parser() -> argparse.ArgumentParser:
    """Create the Agent-Ops command-line parser."""
    parser = argparse.ArgumentParser(
        prog="agent-ops",
        description="Inspect a repository and return structured metadata.",
    )
    parser.add_argument(
        "repository_path",
        nargs="?",
        default=".",
        help="Repository directory to inspect. Defaults to the current directory.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """Run the Agent-Ops repository inspection command."""
    args = build_parser().parse_args(argv)
    profile = scan_repository(args.repository_path)

    print(
        json.dumps(
            profile.model_dump(mode="json"),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()