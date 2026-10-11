# SPDX-FileCopyrightText: foundata GmbH <https://foundata.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Optional verification command; normal linting uses ansible-lint."""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from ruamel.yaml.error import YAMLError

from ansible_lint_foundata.verification import verify


def main(argv: Sequence[str] | None = None) -> int:
    """Verify configured rules without changing project files."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("verify", help="Verify enabled foundata rules")
    command.add_argument("--project-dir", type=Path, default=Path.cwd())
    command.add_argument(
        "-c", "--config-file", type=Path, help="Config path relative to the project"
    )
    args = parser.parse_args(argv)
    try:
        verified = verify(args.project_dir, args.config_file)
    except (OSError, ValueError, YAMLError, subprocess.TimeoutExpired) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Verified discovery and execution of {len(verified)} foundata rules.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
