# API Change Guard

[English](README.md) | [繁體中文](README.zh-TW.md)

Check locally whether an OpenAPI change breaks existing clients.

Early POC: a small Python CLI around [oasdiff](https://github.com/oasdiff/oasdiff).
The upstream engine performs all compatibility analysis. This wrapper provides
fixed check options, a Markdown summary, and predictable exit codes; it does not
claim a new comparison algorithm or replace upstream tooling.

## Quick start

Requires Python 3.11+ and oasdiff. From this checkout, on Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe scripts/install_oasdiff.py
.venv\Scripts\api-change-guard.exe check examples/base.json examples/compatible.json --oasdiff .tools/oasdiff.exe
.venv\Scripts\api-change-guard.exe check examples/base.json examples/breaking.json --oasdiff .tools/oasdiff.exe --report reports/breaking.md
```

On Linux/macOS, use `.venv/bin/python`, `.venv/bin/api-change-guard`, and
`.tools/oasdiff` instead. The installer pins oasdiff to **v1.34.1** and checks
the archive against its upstream SHA-256 checksum. It refuses to overwrite an
existing executable. Alternatively, install oasdiff yourself and pass its path
with `--oasdiff`, or put it on `PATH`.

The compatible example adds an optional response field. The breaking example
removes the required `customer_id` response field. The second command is
expected to return **1**, not 0.

## Usage

```text
api-change-guard check BASE REVISION [--oasdiff PATH] [--report FILE]
```

BASE is the old specification; REVISION is the proposed specification. Both
must be local, self-contained OpenAPI files (JSON or YAML). Internal `$ref`
references are supported; external file and URL references are disabled.
For FastAPI, export each version's `app.openapi()` to JSON before comparing.

The summary is printed to stdout; `--report` also writes it to a UTF-8 Markdown
file. The engine runs with a 60-second timeout, an explicit empty config, and
`--fail-on WARN`, so warnings and errors both block the change.

| Exit code | Meaning |
| --- | --- |
| 0 | No breaking changes detected |
| 1 | Breaking changes detected |
| 2 | Check could not complete, including invalid input or missing engine |

Only consume the report after exit 0 or 1. A failed check does not update an
existing report file; an old report must not be interpreted as a fresh result.

## Scope and limitations

- Tested cases include removed endpoints, newly required request parameters,
	removed required response properties, and incompatible response types.
- This compares specifications, not running servers. It cannot prove API
	behavior, authorization, performance, or correctness of an AI-generated patch.
- External references are disabled, but this is not a sandbox. Run untrusted
	specifications in an isolated CI environment with no secrets.
- No AI service, API key, hosted service, telemetry, or report uploads are used
	by this wrapper. The installer downloads releases from GitHub.

## Development

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check src tests scripts
.venv\Scripts\python.exe -m build --no-isolation
```

Integration tests run automatically when `.tools/oasdiff[.exe]` or an engine on
`PATH` is available. Otherwise they skip. Set `OASDIFF_BINARY` to an executable
path to require a specific engine. Unit tests can run without it.
No GitHub Actions workflow is included; run these checks locally.

Bug reports should include minimal redacted base/revision specs, the CLI and
engine versions, and the expected result. Never submit credentials or private
API specifications. For compatibility-rule issues, check upstream oasdiff too.

## License

Apache-2.0; see [LICENSE](LICENSE). oasdiff is an independent project with its
own license. This project is not affiliated with OpenAI or oasdiff.