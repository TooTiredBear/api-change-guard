"""Command-line entry point."""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from api_change_guard import __version__


def check(base: Path, revision: Path, executable: str) -> list[dict[str, object]]:
    base = base.resolve(strict=True)
    revision = revision.resolve(strict=True)
    if not base.is_file() or not revision.is_file():
        raise ValueError("Both specifications must be local files.")
    engine = shutil.which(executable)
    if engine is None:
        raise ValueError("oasdiff not found; install it and pass --oasdiff PATH.")
    engine = str(Path(engine).resolve())
    with tempfile.TemporaryDirectory(prefix="api-change-guard-") as directory:
        config = Path(directory) / "config.json"
        config.write_text("{}", encoding="utf-8")
        result = subprocess.run(
            [
                engine, "breaking", str(base), str(revision),
                "--format", "json", "--fail-on", "WARN",
                "--allow-external-refs=false", "--config", str(config),
            ],
            cwd=directory,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            check=False,
        )
    if result.returncode not in (0, 1):
        raise ValueError(f"oasdiff failed: {result.stderr.strip() or result.returncode}")
    try:
        findings = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"oasdiff returned invalid JSON: {result.stderr.strip() or 'no details'}"
        ) from error
    if not isinstance(findings, list) or not all(isinstance(item, dict) for item in findings):
        raise ValueError("oasdiff returned an unexpected result format.")
    if result.returncode == 1 and not findings:
        raise ValueError(f"oasdiff failed without findings: {result.stderr.strip()}")
    return findings


def render_report(findings: list[dict[str, object]]) -> str:
    status = "INCOMPATIBLE" if findings else "COMPATIBLE"
    lines = ["# API compatibility report", "", f"Status: {status}", ""]
    for finding in findings:
        lines.append(
            f"- {finding.get('id', 'change')}: {finding.get('text', 'Breaking change')}"
        )
        if finding.get("path"):
            lines.append(f"  {finding.get('operation', '')} {finding['path']}")
    if not findings:
        lines.append("No breaking changes detected by oasdiff.")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local-first OpenAPI compatibility checks.")
    parser.add_argument("--version", action="version", version=f"api-change-guard {__version__}")
    commands = parser.add_subparsers(dest="command")
    command = commands.add_parser("check", help="Compare two local OpenAPI specifications.")
    command.add_argument("base", type=Path)
    command.add_argument("revision", type=Path)
    command.add_argument("--oasdiff", default="oasdiff", help="oasdiff executable name or path.")
    command.add_argument("--report", type=Path, help="Write the Markdown summary to this file.")
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    try:
        if args.report and args.report.resolve() in (args.base.resolve(), args.revision.resolve()):
            raise ValueError("Report must not overwrite an input specification.")
        findings = check(args.base, args.revision, args.oasdiff)
        report = render_report(findings)
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(report, encoding="utf-8")
        print(report, end="")
        return 1 if findings else 0
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"Check failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())