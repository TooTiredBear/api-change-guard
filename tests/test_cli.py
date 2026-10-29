import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from api_change_guard.cli import main


def test_version(capsys):
    with pytest.raises(SystemExit) as result:
        main(["--version"])
    assert result.value.code == 0
    assert "api-change-guard 0.1.0" in capsys.readouterr().out


def test_unknown_option():
    with pytest.raises(SystemExit) as result:
        main(["--unknown"])
    assert result.value.code == 2


@pytest.fixture
def specs(tmp_path):
    base = tmp_path / "base.json"
    revision = tmp_path / "revision.json"
    base.write_text("{}", encoding="utf-8")
    revision.write_text("{}", encoding="utf-8")
    return base, revision


def mock_engine(monkeypatch, result):
    monkeypatch.setattr("api_change_guard.cli.shutil.which", lambda name: "oasdiff")

    def run(command, **kwargs):
        assert "--allow-external-refs=false" in command
        assert "--config" in command
        assert kwargs["timeout"] == 60
        return result

    monkeypatch.setattr("api_change_guard.cli.subprocess.run", run)


@pytest.mark.parametrize("breaking", [False, True])
def test_check_and_report(specs, tmp_path, monkeypatch, capsys, breaking):
    findings = [{"id": "api-removed", "text": "endpoint removed", "path": "/users"}]
    mock_engine(
        monkeypatch,
        subprocess.CompletedProcess(
            [], int(breaking), json.dumps(findings if breaking else []), ""
        ),
    )
    report = tmp_path / "reports" / "report.md"
    assert main(["check", *map(str, specs), "--report", str(report)]) == int(breaking)
    output = capsys.readouterr().out
    assert report.read_text(encoding="utf-8") == output
    assert f"Status: {'INCOMPATIBLE' if breaking else 'COMPATIBLE'}" in output
    if breaking:
        assert "endpoint removed" in output


@pytest.mark.parametrize(
    ("code", "output"), [(2, ""), (1, "[]"), (0, "not json"), (0, "{}")]
)
def test_engine_failure_is_not_compatible(specs, monkeypatch, capsys, code, output):
    mock_engine(monkeypatch, subprocess.CompletedProcess([], code, output, "engine error"))
    assert main(["check", *map(str, specs)]) == 2
    captured = capsys.readouterr()
    assert "Check failed:" in captured.err
    assert not captured.out


def test_missing_engine(specs, monkeypatch, capsys):
    monkeypatch.setattr("api_change_guard.cli.shutil.which", lambda name: None)
    assert main(["check", *map(str, specs)]) == 2
    assert "oasdiff not found" in capsys.readouterr().err


def test_missing_spec(tmp_path, capsys):
    assert main(["check", str(tmp_path / "missing.json"), "missing.json"]) == 2
    assert "Check failed:" in capsys.readouterr().err


def test_report_cannot_overwrite_input(specs, capsys):
    assert main(["check", *map(str, specs), "--report", str(specs[0])]) == 2
    assert specs[0].read_text(encoding="utf-8") == "{}"
    assert "must not overwrite" in capsys.readouterr().err


def test_engine_timeout(specs, monkeypatch, capsys):
    monkeypatch.setattr("api_change_guard.cli.shutil.which", lambda name: "oasdiff")

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("oasdiff", 60)

    monkeypatch.setattr("api_change_guard.cli.subprocess.run", timeout)
    assert main(["check", *map(str, specs)]) == 2
    assert "Check failed:" in capsys.readouterr().err


@pytest.fixture
def real_engine():
    name = "oasdiff.exe" if os.name == "nt" else "oasdiff"
    local = Path(__file__).resolve().parents[1] / ".tools" / name
    configured = os.environ.get("OASDIFF_BINARY")
    if configured:
        assert Path(configured).is_file(), "OASDIFF_BINARY must point to an executable"
        return str(Path(configured).resolve())
    if local.is_file():
        return str(local)
    engine = shutil.which("oasdiff")
    if engine is None:
        pytest.skip("Install oasdiff to run integration tests")
    return engine


@pytest.mark.integration
@pytest.mark.parametrize(("revision", "code"), [("compatible", 0), ("breaking", 1)])
def test_real_examples(real_engine, revision, code, capsys, tmp_path):
    examples = Path(__file__).resolve().parents[1] / "examples"
    report = tmp_path / "report.md"
    assert main([
        "check", str(examples / "base.json"), str(examples / f"{revision}.json"),
        "--oasdiff", real_engine, "--report", str(report),
    ]) == code
    output = capsys.readouterr().out
    assert report.read_text(encoding="utf-8") == output
    assert f"Status: {'INCOMPATIBLE' if code else 'COMPATIBLE'}" in output
    if code:
        assert "customer_id" in output


@pytest.mark.integration
@pytest.mark.parametrize("change", ["endpoint", "request", "response"])
def test_real_breaking_changes(real_engine, tmp_path, change, capsys):
    base = Path(__file__).resolve().parents[1] / "examples" / "base.json"
    spec = json.loads(base.read_text(encoding="utf-8"))
    operation = spec["paths"]["/customers"]["get"]
    if change == "endpoint":
        spec["paths"] = {}
    elif change == "request":
        operation["parameters"] = [{
            "name": "token", "in": "query", "required": True, "schema": {"type": "string"},
        }]
    else:
        schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
        schema["properties"]["customer_id"]["type"] = "integer"
    revision = tmp_path / "changed.json"
    revision.write_text(json.dumps(spec), encoding="utf-8")
    assert main(["check", str(base), str(revision), "--oasdiff", real_engine]) == 1
    assert "INCOMPATIBLE" in capsys.readouterr().out


@pytest.mark.integration
def test_real_invalid_spec(real_engine, tmp_path, capsys):
    base = Path(__file__).resolve().parents[1] / "examples" / "base.json"
    revision = tmp_path / "invalid.json"
    revision.write_text("{invalid", encoding="utf-8")
    assert main(["check", str(base), str(revision), "--oasdiff", real_engine]) == 2
    captured = capsys.readouterr()
    assert "Check failed:" in captured.err
    assert not captured.out


@pytest.mark.integration
def test_real_external_ref_rejected(real_engine, tmp_path, capsys):
    base = Path(__file__).resolve().parents[1] / "examples" / "base.json"
    spec = json.loads(base.read_text(encoding="utf-8"))
    response = spec["paths"]["/customers"]["get"]["responses"]["200"]
    response["content"]["application/json"]["schema"] = {"$ref": "./external.json"}
    (tmp_path / "external.json").write_text('{"type": "string"}', encoding="utf-8")
    revision = tmp_path / "external-ref.json"
    revision.write_text(json.dumps(spec), encoding="utf-8")
    assert main(["check", str(base), str(revision), "--oasdiff", real_engine]) == 2
    assert "Check failed:" in capsys.readouterr().err


@pytest.mark.integration
def test_real_ignores_ambient_config(real_engine, monkeypatch, capsys):
    base = Path(__file__).resolve().parents[1] / "examples" / "base.json"
    monkeypatch.setenv("OASDIFF_CONFIG", "does-not-exist.yaml")
    assert main(["check", str(base), str(base), "--oasdiff", real_engine]) == 0
    assert "Status: COMPATIBLE" in capsys.readouterr().out