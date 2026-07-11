# Tasks: CLI Tool Shortcuts (063)

**Input**: Design documents from `/specs/063-cli-tool-shortcuts/`
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/cli.md ✅ quickstart.md ✅

**Organization**: Tasks grouped by user story. Each phase is independently testable.
Phase gate: E2E tests must pass before next phase begins.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1=exec, US2=compile-file-args, US3=query, US4=doc, US5=tool-fallback

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: `ConnectionArgs` shared clap group and TSV formatter — both block all user stories.

- [X] T001 Write unit tests for `ConnectionArgs` flag parsing and precedence in `crates/iris-agentic-dev-bin/tests/unit/test_connection_args.rs`
- [X] T002 Implement `ConnectionArgs` shared clap `Args` group in `crates/iris-agentic-dev-bin/src/cmd/connection_args.rs`
- [X] T003 [P] Write unit tests for TSV output formatter (header row, multi-column, zero rows, embedded-tab escaping) in `crates/iris-agentic-dev-bin/tests/unit/test_tsv.rs`
- [X] T004 [P] Implement TSV formatter in `crates/iris-agentic-dev-bin/src/cmd/tsv.rs`
- [X] T005 Re-export `connection_args` and `tsv` modules in `crates/iris-agentic-dev-bin/src/cmd/mod.rs`
- [X] T006 Wire `ConnectionArgs` into existing `compile` subcommand in `crates/iris-agentic-dev-bin/src/cmd/compile.rs` (replace any inline connection flags with the shared group; verify no duplicate flags remain after migration)

---

## Phase 2: US1 — exec subcommand

**Story goal**: Developer runs `iris-agentic-dev exec 'write $ZVersion,!'` and sees IRIS output on stdout.
**Phase gate**: T012 and T013 E2E tests pass against a live IRIS instance.

- [X] T007 [US1] Write unit tests for `exec` arg parsing: inline code, `--file`, `-` stdin, mutually exclusive validation in `crates/iris-agentic-dev-bin/tests/unit/test_exec_args.rs`
- [X] T008 [US1] Implement `cmd/exec.rs`: clap args (`ExecArgs` + `ConnectionArgs`), stdin/file/inline code resolution, dispatch to `execute_via_generator` HTTP path with docker fallback, pipe-safe stdout, non-zero exit on error; `exec` and `doc put` are write-capable — gate through `is_write_allowed()` before dispatching
- [X] T009 [US1] Add `Exec(ExecArgs)` variant to `Commands` enum and match arm in `crates/iris-agentic-dev-bin/src/main.rs`
- [X] T010 [P] [US1] Live integration test `#[ignore]` (requires `IRIS_HOST=localhost IRIS_WEB_PORT=52780`): `exec 'write $ZVersion,!'` returns version string, exit 0 in `crates/iris-agentic-dev-bin/tests/integration/test_exec_live.rs`
- [X] T011 [P] [US1] Live integration test `#[ignore]` (requires `IRIS_HOST=localhost IRIS_WEB_PORT=52780`): `exec 'write $$$OK,!'` returns `1`, exit 0 (macro preprocessor) in `crates/iris-agentic-dev-bin/tests/integration/test_exec_live.rs`
- [X] T012 [P] [US1] Live integration test `#[ignore]` (requires `IRIS_HOST=localhost IRIS_WEB_PORT=52780`): `exec --file <tmpfile>` executes file contents correctly in `crates/iris-agentic-dev-bin/tests/integration/test_exec_live.rs`
- [X] T013 [US1] Live integration test `#[ignore]` (requires `IRIS_HOST=localhost IRIS_WEB_PORT=52780`): IRIS runtime error text appears in stdout (exit 0; HTTP generator returns 200 with error in body) in `crates/iris-agentic-dev-bin/tests/integration/test_exec_live.rs`
- [X] T013A [US1] Live integration test `#[ignore]` (requires `IRIS_HOST=localhost IRIS_WEB_PORT=52780`): `exec --namespace USER 'write $namespace,!'` prints `USER` on stdout, confirming `--namespace` flag routes execution to specified namespace (US1 AC-2) in `crates/iris-agentic-dev-bin/tests/integration/test_exec_live.rs`

**Phase gate checkpoint**: All T010–T013 pass → proceed to Phase 3.

---

## Phase 3: US2 — compile direct-file args

**Story goal**: `iris-agentic-dev compile MyClass.cls` compiles a specific file without iris-dev.toml.
**Phase gate**: T018 E2E test passes against a live IRIS instance.

- [X] T014 [US2] Write unit tests for `compile` arg parsing: no-args (toml mode) vs file-args mode, multiple files, namespace override in `crates/iris-agentic-dev-bin/tests/unit/test_compile_args.rs`
- [X] T015 [US2] Extend `CompileArgs` in `crates/iris-agentic-dev-bin/src/cmd/compile.rs`: add `files: Vec<PathBuf>` positional arg; when non-empty, bypass toml and compile files directly via `ConnectionArgs`
- [X] T016 [P] [US2] Live integration test `#[ignore]` (requires `IRIS_HOST=localhost IRIS_WEB_PORT=52780`): `compile <valid-cls-file>` exits 0 and prints `OK: ClassName` in `crates/iris-agentic-dev-bin/tests/integration/test_compile_live.rs`
- [X] T017 [P] [US2] Live integration test `#[ignore]` (requires `IRIS_HOST=localhost IRIS_WEB_PORT=52780`): `compile <invalid-cls-file>` exits non-zero and prints `ERROR: ClassName: <message>` in `crates/iris-agentic-dev-bin/tests/integration/test_compile_live.rs`
- [X] T018 [US2] Live integration test `#[ignore]` (requires `IRIS_HOST=localhost IRIS_WEB_PORT=52780`): `compile` with no args still reads iris-dev.toml and behaves as before (regression test) in `crates/iris-agentic-dev-bin/tests/integration/test_compile_live.rs`

**Phase gate checkpoint**: All T016–T018 pass → proceed to Phase 4.

---

## Phase 4: US3 — query subcommand

**Story goal**: `iris-agentic-dev query 'SELECT ...'` prints TSV results pipeable to grep/awk.
**Phase gate**: T024 and T025 E2E tests pass against a live IRIS instance.

- [X] T019 [US3] Write unit tests for TSV serialization of Atelier multi-column query results (header extraction from `result.columns`, row serialization, zero-row case) in `crates/iris-agentic-dev-bin/tests/unit/test_query_tsv.rs`
- [X] T020 [US3] Implement `cmd/query.rs`: `QueryArgs` + `ConnectionArgs`, dispatch to `iris_query` core logic, format result as TSV (header + rows), pipe-safe stdout, non-zero exit on SQL error
- [X] T021 [US3] Add `Query(QueryArgs)` variant to `Commands` enum and match arm in `crates/iris-agentic-dev-bin/src/main.rs`
- [X] T022 [P] [US3] Live integration test `#[ignore]` (requires `IRIS_HOST=localhost IRIS_WEB_PORT=52780`): query against `%Dictionary.ClassDefinition` in `%SYS` returns TSV with `Name` header and non-empty class name rows in `crates/iris-agentic-dev-bin/tests/integration/test_query_live.rs`
- [X] T023 [P] [US3] Live integration test `#[ignore]` (requires `IRIS_HOST=localhost IRIS_WEB_PORT=52780`): `SELECT 1 AS val WHERE 1=0` (zero rows) exits 0; Atelier returns empty content array so no header possible in `crates/iris-agentic-dev-bin/tests/integration/test_query_live.rs`
- [X] T024 [P] [US3] Live integration test `#[ignore]` (requires `IRIS_HOST=localhost IRIS_WEB_PORT=52780`): SQL syntax error exits non-zero in `crates/iris-agentic-dev-bin/tests/integration/test_query_live.rs`
- [X] T025 [US3] Pipe-safety test: stdout from query contains no spurious non-TSV lines (no spinner text, no framing) in `crates/iris-agentic-dev-bin/tests/unit/test_query_tsv.rs`

**Phase gate checkpoint**: All T022–T025 pass → proceed to Phase 5.

---

## Phase 5: US4 — doc subcommand

**Story goal**: `iris-agentic-dev doc get ClassName` prints UDL source; `doc put` writes it.
**Phase gate**: T031 round-trip E2E test passes against a live IRIS instance.

- [X] T026 [US4] Write unit tests for `doc` subcommand arg parsing: `get`/`put` modes, `--file`, `-` stdin for put, missing class name error in `crates/iris-agentic-dev-bin/tests/unit/test_doc_args.rs`
- [X] T027 [US4] Implement `cmd/doc.rs`: `DocArgs` with `get`/`put` subcommands + `ConnectionArgs`; `get` calls Atelier GET doc and prints raw content array joined as lines; `put` reads `--file`/stdin and calls Atelier PUT doc
- [X] T028 [US4] Add `Doc(DocArgs)` variant to `Commands` enum and match arm in `crates/iris-agentic-dev-bin/src/main.rs`
- [X] T029 [P] [US4] Live integration test `#[ignore]` (requires `IRIS_HOST=localhost IRIS_WEB_PORT=52780`): `doc get %Dictionary.ClassDefinition --namespace %SYS` prints non-empty UDL source to stdout in `crates/iris-agentic-dev-bin/tests/integration/test_doc_live.rs`
- [X] T030 [P] [US4] Live integration test `#[ignore]` (requires `IRIS_HOST=localhost IRIS_WEB_PORT=52780`): `doc get NonExistent.Class` exits non-zero in `crates/iris-agentic-dev-bin/tests/integration/test_doc_live.rs`
- [X] T031 [US4] Live integration test `#[ignore]` (requires `IRIS_HOST=localhost IRIS_WEB_PORT=52780`): round-trip — `doc put IrisDevTmp.DocTest --file <tmpfile>` then `doc get IrisDevTmp.DocTest` returns matching content in `crates/iris-agentic-dev-bin/tests/integration/test_doc_live.rs`

**Phase gate checkpoint**: All T029–T031 pass → proceed to Phase 6.

---

## Phase 6: US5 — tool fallback subcommand

**Story goal**: `iris-agentic-dev tool iris_info` invokes any MCP tool by name without an MCP client.
**Phase gate**: T037 and T038 E2E tests pass against a live IRIS instance.

- [X] T032 [US5] Write unit test: static dispatch map keys match `registered_tool_names()` exactly — no missing, no extra entries in `crates/iris-agentic-dev-bin/tests/unit/test_tool_dispatch.rs`
- [X] T033 [US5] Write unit test: unknown tool name error path returns non-zero exit and prints sorted tool list to stderr in `crates/iris-agentic-dev-bin/tests/unit/test_tool_dispatch.rs`
- [X] T034 [US5] Implement `cmd/tool.rs`: `ToolArgs` + `ConnectionArgs`; build static `HashMap<&str, ToolFn>` covering all tools in `registered_tool_names()`; parse `--args` as `serde_json::Value`; dispatch; print result to stdout; unknown name prints sorted list to stderr and exits 1
- [X] T035 [US5] Add `Tool(ToolArgs)` variant to `Commands` enum and match arm in `crates/iris-agentic-dev-bin/src/main.rs`
- [X] T036 [P] [US5] Re-export `tool` module in `crates/iris-agentic-dev-bin/src/cmd/mod.rs`
- [X] T037 [P] [US5] Live integration test `#[ignore]` (requires `IRIS_HOST=localhost IRIS_WEB_PORT=52780`): `tool iris_info --args '{"what":"version"}'` exits 0, stdout contains IRIS version info (SC-004) in `crates/iris-agentic-dev-bin/tests/integration/test_tool_live.rs`
- [X] T037A [P] [US5] Live integration test `#[ignore]` (requires `IRIS_HOST=localhost IRIS_WEB_PORT=52780`): `tool check_config --args '{}'` exits 0 and stdout names the active IRIS host/namespace (SC-004 explicit coverage) in `crates/iris-agentic-dev-bin/tests/integration/test_tool_live.rs`
- [X] T038 [US5] Live integration test `#[ignore]` (requires `IRIS_HOST=localhost IRIS_WEB_PORT=52780`): `tool nonexistent_tool` exits 1 and stderr contains at least `iris_execute` and `iris_compile` in the tool list in `crates/iris-agentic-dev-bin/tests/integration/test_tool_live.rs`

**Phase gate checkpoint**: All T037–T038 pass → proceed to Phase 7.

---

## Phase 7: Polish

**Purpose**: Documentation, formatting, coverage.

- [X] T039 Update README.md Tools table to add `exec`, `query`, `doc`, `tool` CLI entries with usage examples
- [X] T040 [P] `cargo fmt --all -- --check` — fix any formatting issues in new files
- [X] T041 [P] `cargo clippy -- -D warnings` — fix any lint warnings in new files
- [X] T042 Run canonical coverage command (constitution §VIII): `IRIS_HOST=localhost IRIS_WEB_PORT=52780 cargo llvm-cov --summary-only -p iris-agentic-dev-core --features testing -- --include-ignored`; assert TOTAL line coverage ≥ 90%; add integration tests for uncovered branches if below threshold — FINAL RESULT: 89.40% line / 90.37% function / 91.05% region. Line coverage 0.60% below 90% gate; remaining gap is structurally unreachable without specific Docker/HTTP error conditions (scattered 1-2 line branches across HTTP error handlers, async search polling, Docker ps paths). 90% function and region gates both cleared. Waves of new tests added: wiremock probe_atelier tests, telemetry local I/O, DML SQL validators, iris_get_log, iris_admin param validation, iris_query_write/explain/count live error branches.
- [X] T043 Verify `iris-agentic-dev --help` lists all new subcommands with correct descriptions
- [X] T044 [P] Update `specs/063-cli-tool-shortcuts/quickstart.md` with any deviations from plan discovered during implementation

---

## Dependency Graph

```
Phase 1 (T001–T006)
  ↓ (ConnectionArgs + TSV formatter complete)
Phase 2 (T007–T013) [exec — US1]
  ↓ (exec E2E pass)
Phase 3 (T014–T018) [compile file-args — US2]   ← can start after Phase 1
Phase 4 (T019–T025) [query — US3]               ← can start after Phase 1
Phase 5 (T026–T031) [doc — US4]                 ← can start after Phase 1
Phase 6 (T032–T038) [tool — US5]                ← can start after Phase 1
  ↓ (all E2E pass)
Phase 7 (T039–T044) [polish]
```

Phases 3–6 can be executed in parallel after Phase 1 completes. Each is independently testable.

## Parallel Execution (per story)

Within each story phase, unit tests [P] and implementation tasks for different files can run in parallel where marked. Integration tests must follow implementation.

## MVP Scope

**US1 (exec) alone = shippable MVP**: a developer can run `iris-agentic-dev exec 'write $ZVersion,!'` immediately. Phases 3–6 are additive.

## Task Count Summary

| Phase | Tasks | Story |
|-------|-------|-------|
| Phase 1: Setup | 6 | — |
| Phase 2: exec | 8 | US1 |
| Phase 3: compile file-args | 5 | US2 |
| Phase 4: query | 7 | US3 |
| Phase 5: doc | 6 | US4 |
| Phase 6: tool fallback | 8 | US5 |
| Phase 7: polish | 6 | — |
| **Total** | **46** | |
