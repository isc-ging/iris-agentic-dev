# iris-dev Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-05-01

## Active Technologies
- Rust 2021, tokio async, rmcp 1.2 (020-scm-elicitation-auto-open)
- Rust 2021 edition + rmcp 1.2, reqwest 0.12, tokio 1, bollard 0.17, serde/serde_json, tracing 0.1, uuid 1, regex 1, semver 1 (001-fix-audit-bugs)
- IRIS globals (`^SKILLS`, `^KBCHUNKS`) via docker exec; Atelier REST API (001-fix-audit-bugs)
- Rust 2021 + reqwest 0.12, tokio 1, anyhow 1, urlencoding 2 (all already in workspace) (002-fix-exec-bugs)
- IRIS temp class/routine via Atelier REST; temp file in IRIS `/tmp/` (002-fix-exec-bugs)
- Rust 2021 + `toml` 0.8 (already in workspace), `serde` (already in workspace), `dirs` 5 (already in iris-dev-core) (003-workspace-config)
- Rust 2021 + All existing (no new deps) (004-fix-realworld-issues)
- Rust 2021 edition, tokio async runtime + `reqwest 0.12` (HTTP), `serde_json` (response building), `anyhow` (error handling) — all already in workspace. No new crates. (024-interop-depth)
- No persistent storage. IRIS globals and classes are the backing store; accessed via Atelier REST. (024-interop-depth)
- No persistent storage — reads files from disk at call time (025-symbols-local-ts)
- Rust 2021, tokio async + `reqwest`, `serde_json`, `anyhow` — all already in workspace. No new crates. (026-admin-tools)
- No persistent storage — queries IRIS Security.* and Config.* classes (026-admin-tools)
- Rust 1.92 (workspace — `crates/iris-dev-core`) + `uuid = { version = "1", features = ["v4"] }` (already in workspace); `std::collections::VecDeque`, `std::time::Instant` (stdlib only). No new crate deps. (027-progressive-disclosure)
- In-process memory only — `VecDeque<LogEntry>` with max 50 entries. Not persisted to disk. Cleared on server restart. (027-progressive-disclosure)
- Rust 1.92 (`crates/iris-dev-core`, `crates/iris-dev-bin`) + `bollard` (already workspace); `reqwest` (already workspace). No new deps. (028-better-docker-discovery)
- N/A — discovery is stateless (028-better-docker-discovery)
- Rust 1.92 (`crates/iris-dev-core`) + No new crates. Uses existing: `serde_json`, `reqwest`, `uuid`, `log_store` module (027) (032-iris-test-http)
- In-process log store (027) for full test detail (032-iris-test-http)
- Rust 1.92 (`crates/iris-dev-core`) + None new — uses only `std` (regex-free string scanning). All (033-sql-safety-gate)
- N/A — pure in-memory validation, no persistence (033-sql-safety-gate)
- Rust 1.92 (`crates/iris-dev-core` + `crates/iris-dev-bin`) + No new crates. Uses `std::sync::Mutex`, `std::fs::metadata`, `std::time::SystemTime` (all std). (034-live-connection-reload)
- In-memory `Arc<Mutex<ConnectionState>>` on `IrisTools` (034-live-connection-reload)
- Rust 1.92 (`crates/iris-dev-core/src/tools/mod.rs`) + No new crates. Pure `std` string processing. (035-sql-macro-translate)
- N/A — pure in-memory transformation (035-sql-macro-translate)
- Python 3.11+ (consistent with existing benchmark harness) + `requests` (curl URL validation + fixture loading), `subprocess` (opencode invocation), `sqlite3` (stdlib, OPENCODE_DB inspection), `pyyaml` (task fixture files), `pytest` (test runner) (039-skills-e2e)
- Temp files per run (`/tmp/opencode-harness-{run_id}/`); results JSON to `tests/e2e/results/` (039-skills-e2e)
- Python 3.11+ + existing `benchmark/021/runner/` (judge, fixtures, client), `tests/e2e/` (039 harness — isolated_env, opencode_runner, readme_validator), `pyyaml`, `anthropic` (Bedrock) (040-skill-regression)
- `tests/e2e/tasks/skills/*/eval.yaml` (configs), `tests/e2e/results/skill-eval-*.json` (run results), `tests/e2e/results/skill-baseline.json` (comparison baseline) (040-skill-regression)
- Rust 1.92 (workspace version) + existing workspace — no new crates (043-windows-native-iris)
- N/A (no persistent state changes) (043-windows-native-iris)
- Rust 1.92 (stable, aarch64-apple-darwin + x86_64-linux) + existing workspace crates + `keyring = { version = "4", features = ["linux-keyutils"] }` (new — justified in research.md) (044-servermanager-discovery)
- `~/.iris-agentic-dev/audit.jsonl` (append-only JSONL); VS Code `settings.json` (read-only) (044-servermanager-discovery)
- Rust 1.92 (workspace minimum — matches existing `iris-agentic-dev-core`) + `serde_json` (already workspace), `regex` (already workspace via `iris_search`), no new crates required (051-phi-policy-env-gates)
- `.iris-agentic-dev.toml` (per-connection policy section, extends existing `[policy.<server>]` block from 044); no new storage (051-phi-policy-env-gates)
- Rust 2021 (workspace `edition = "2021"`, matches + `reqwest` 0.12 (already a dependency, used for Anthropic/OpenAI (059-tool-telemetry-benchmark)
- Dual-sink durable telemetry — IRIS global (name TBD in research.md, mirroring (059-tool-telemetry-benchmark)
- Rust 2021 edition (matches workspace) + `reqwest`, `serde`/`serde_json`, `tokio`, `rmcp` (all (060-tool-ablation-study)
- Local filesystem — JSON run-ledger file (one line/record per completed (060-tool-ablation-study)
- Python 3.11+ (glue script, objectscript-coder side); no new + `gepa` (`pip install gepa` — local package, no hosted API; (030-gepa-skill-optimizer)
- None persisted beyond the per-run output JSON (`gepa-run-<tool>.json`) (030-gepa-skill-optimizer)
- Rust 1.92 (workspace edition 2021) + clap 4.x (derive, already used), serde_json (already used), anyhow (already used), tokio (already used) (063-cli-tool-shortcuts)
- N/A — stateless, one-shot CLI invocations (063-cli-tool-shortcuts)

- Rust 2021, tokio async runtime + rmcp 1.2 (macros, server, schemars, transport-io), reqwest 0.12 (async HTTP), bollard 0.17 (Docker), serde + serde_json, tokio 1.x (019-iris-dev-v2-unified)

## Project Structure

```text
src/
tests/
```

## Commands

cargo test [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] cargo clippy

## Code Style

Rust 2021, tokio async runtime: Follow standard conventions

## Recent Changes
- 064-objectscript-coverage: Added iris_coverage tool — %Monitor.System.LineByLine wrapper; HTTP→docker exec fallback for Atelier PUT API compatibility; single-line ObjectScript for all execution contexts
- 063-cli-tool-shortcuts: Added Rust 1.92 (workspace edition 2021) + clap 4.x (derive, already used), serde_json (already used), anyhow (already used), tokio (already used)
- 030-gepa-skill-optimizer: Added Python 3.11+ (glue script, objectscript-coder side); no new + `gepa` (`pip install gepa` — local package, no hosted API;
- 060-tool-ablation-study: Added Rust 2021 edition (matches workspace) + `reqwest`, `serde`/`serde_json`, `tokio`, `rmcp` (all


<!-- MANUAL ADDITIONS START -->
## Testing Philosophy — NON-NEGOTIABLE

This is a **heavily IRIS-specific project**. IRIS is the only valid test object.

- **Always use a live IRIS container for tests.** Never mock IRIS, mock the Atelier
  HTTP client, or stub IRIS responses in unit tests. Mocked IRIS tests lie — they
  pass when the real implementation is broken.
- **Coverage goals require `--include-ignored`** against a live container. The e2e
  job exists for this reason. Unit tests covering pure logic (parsers, guards, gates)
  are fine, but anything that touches IRIS behaviour must run against real IRIS.
- **Local dev container**: `iris-dev-iris` on port 52780. Always verify it is running
  before writing or running IRIS-dependent tests.
- **`--test-threads=1`** is required for all IRIS integration/e2e test runs to prevent
  env-var race conditions across test binaries.
<!-- MANUAL ADDITIONS END -->

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
<!-- SPECKIT END -->
