"""Build and verify the installed distribution outside the source checkout."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path


def run(*arguments: str, cwd: Path | None = None) -> str:
    """Run a build or smoke check, preserving useful failure output."""
    result = subprocess.run(
        arguments,
        cwd=cwd,
        check=False,
        text=True,
        capture_output=True,
        timeout=180,
    )
    if result.returncode:
        sys.stderr.write(result.stdout + result.stderr)
        raise SystemExit(result.returncode)
    return result.stdout


def main() -> None:
    """Check wheel contents, sdist rebuilding, discovery and optional fallback."""
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="foundata-distribution-") as temporary:
        work = Path(temporary)
        artifacts = work / "artifacts"
        run("uv", "build", "--out-dir", str(artifacts), cwd=root)
        sdist = next(artifacts.glob("*.tar.gz"))
        with tarfile.open(sdist) as archive:
            members = {
                Path(*Path(member.name).parts[1:]).as_posix()
                for member in archive.getmembers()
                if member.isfile()
            }
            required = {
                "DEVELOPMENT.md",
                "docs/rules.md",
                "uv.lock",
                "REUSE.toml",
                "scripts/check_distribution.py",
                "tests/integration/test_consumer_config.py",
                "examples/consumer/.ansible-lint",
                "examples/consumer/.yamllint",
            }
            assert required <= members, sorted(required - members)
        wheel = next(artifacts.glob("*.whl"))
        with zipfile.ZipFile(wheel) as archive:
            names = archive.namelist()
            assert "ansiblelint/__init__.py" not in names
            assert "ansiblelint/rules/__init__.py" not in names
            assert "ansiblelint/rules/custom/__init__.py" not in names
            assert "ansible_lint_foundata/py.typed" in names
            assert "ansiblelint/rules/custom/foundata/__init__.py" in names
        run(
            "uv",
            "build",
            str(sdist),
            "--wheel",
            "--out-dir",
            str(work / "rebuilt"),
        )
        rebuilt = next((work / "rebuilt").glob("*.whl"))
        with zipfile.ZipFile(wheel) as original, zipfile.ZipFile(rebuilt) as other:
            assert sorted(original.namelist()) == sorted(other.namelist())
            for name in original.namelist():
                # uv may use its bundled backend for one build and a newer
                # compatible uv_build for the other. Generator/hash records vary.
                if name.endswith((".dist-info/WHEEL", ".dist-info/RECORD")):
                    continue
                assert original.read(name) == other.read(name), name

        environment = work / "venv"
        run("uv", "venv", "--python", sys.executable, str(environment))
        python = environment / "bin" / "python"
        run("uv", "pip", "install", "--python", str(python), str(wheel))
        # Imports and CLI calls run outside the checkout and without PYTHONPATH.
        os.environ.pop("PYTHONPATH", None)
        os.environ["ANSIBLE_CONFIG"] = str(work / "ansible.cfg")
        os.environ["ANSIBLE_COLLECTIONS_PATH"] = str(work / "collections")
        os.environ["ANSIBLE_COLLECTIONS_SCAN_SYS_PATH"] = "true"
        os.environ["ANSIBLE_LINT_NODEPS"] = "1"
        (work / "ansible.cfg").write_text("[defaults]\n", encoding="utf-8")
        ids = json.loads(
            run(
                str(python),
                "-c",
                "import json; from ansible_lint_foundata import RULE_IDS; print(json.dumps(RULE_IDS))",
                cwd=work,
            )
        )
        listing = run(
            str(python),
            "-m",
            "ansiblelint",
            "--offline",
            "--list-rules",
            "--format",
            "brief",
            cwd=work,
        )
        for rule_id in ids:
            assert f"- {rule_id} " in listing, rule_id
        assert "- yaml " in listing and "- fqcn " in listing
        (work / ".ansible-lint").write_text(
            json.dumps(
                {
                    "profile": "production",
                    "enable_list": ids,
                }
            ),
            encoding="utf-8",
        )
        (work / "tasks").mkdir()
        (work / "tasks" / "main.yml").write_text(
            """---
- name: "Example"
  ansible.builtin.debug:
    msg: "Example"
    verbosity: 1
  when:
    - true
""",
            encoding="utf-8",
        )
        run(str(python), "-m", "ansiblelint", "--offline", "tasks/main.yml", cwd=work)
        run("uv", "pip", "uninstall", "--python", str(python), "ansible-lint-foundata")
        run(str(python), "-m", "ansiblelint", "--offline", "tasks/main.yml", cwd=work)
        listing = run(
            str(python),
            "-m",
            "ansiblelint",
            "--offline",
            "--list-rules",
            "--format",
            "brief",
            cwd=work,
        )
        assert "- yaml " in listing and "- foundata-" not in listing
    print("Wheel, rebuilt sdist, installed discovery and package-free fallback passed.")


if __name__ == "__main__":
    main()
