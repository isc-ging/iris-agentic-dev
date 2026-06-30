# Tasks: Document Depth — iris_doc Extensions + iris_execute_method

**Input**: Design documents from `/specs/053-doc-depth/`
**Prerequisites**: plan.md ✓, spec.md ✓ (clarified 2026-06-29)

**Organization**: Tasks grouped by user story. US1 = fragment (P1), US2 = compiled (P1),
US3 = list (P2), US4 = iris_execute_method (P2). Phase 1 setup + Phase 2 foundational
must complete before any US phase begins.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add new DocMode variants + params to IrisDocParams + stub dispatch arms + register
iris_execute_method. All US phases depend on this compiling.

- [ ] T001 Add `Fragment`, `Compiled`, `List` variants to the `DocMode` enum in
      `crates/iris-agentic-dev-core/src/tools/doc.rs` — add `from_str` match arms for
      `"fragment"`, `"compiled"`, `"list"` alongside existing modes
- [ ] T002 Add new optional fields to `IrisDocParams` struct in
      `crates/iris-agentic-dev-core/src/tools/doc.rs`:
      `start: Option<i64>`, `end: Option<i64>`, `compiled_type: Option<String>`,
      `pattern: Option<String>`, `category: Option<String>`, `max_results: Option<i64>`
- [ ] T003 Add stub match arms in the `handle_iris_doc` dispatch in
      `crates/iris-agentic-dev-core/src/tools/doc.rs` for `DocMode::Fragment`,
      `DocMode::Compiled`, `DocMode::List` — return `not_implemented` JSON placeholder
- [ ] T004 Add `iris_execute_method` stub tool handler function in
      `crates/iris-agentic-dev-core/src/tools/mod.rs` — define `IrisExecuteMethodParams`
      struct with `class`, `method`, `args`, `namespace` fields; stub returns `not_implemented`
- [ ] T005 Route `"iris_execute_method"` in the tool dispatch match arm in
      `crates/iris-agentic-dev-core/src/tools/mod.rs`
- [ ] T006 Add `"iris_execute_method"` to `registered_tool_names()` in
      `crates/iris-agentic-dev-core/src/tools/mod.rs`
- [ ] T007 Add `iris_execute_method` → `ToolCategory::Execute` in `tool_to_category()` in
      `crates/iris-agentic-dev-core/src/iris/server_manager.rs`
- [ ] T008 Add `iris_execute_method` to the `Toolset::Merged` tier in
      `crates/iris-agentic-dev-core/src/tools/mod.rs` — add to both
      `with_registry_and_toolset()` Merged removal list AND confirm it is in
      `registered_tool_names()` (T006); these two lists must stay in sync
- [ ] T009 Run `cargo build -p iris-agentic-dev-core` — confirm clean compile with stubs

**Checkpoint**: New `DocMode` variants compile, `iris_execute_method` registered in Merged
tier, routes to stubs, compiles clean.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Fragment helper for line slicing + list pattern validation + clamp helpers.
All needed before US implementations.

- [ ] T010 Implement `clamp_max_results(v: i64) -> i64` helper in
      `crates/iris-agentic-dev-core/src/tools/doc.rs` — clamps to `[1, 1000]`
- [ ] T011 Implement `validate_list_pattern(pattern: &str) -> Result<(), serde_json::Value>` in
      `crates/iris-agentic-dev-core/src/tools/doc.rs` — rejects empty string, bare `"*"`,
      `"**"`, or patterns starting with `*` with no preceding prefix; returns
      `MISSING_PARAMS` error JSON on failure
- [ ] T012 Implement `slice_lines(lines: &[String], start: i64, end: i64) -> (Vec<String>, i64, i64, bool)` in
      `crates/iris-agentic-dev-core/src/tools/doc.rs` — takes 1-based start/end, clamps end
      to `lines.len()`, returns `(sliced, actual_start, actual_end, was_clamped)`
- [ ] T013 Run `cargo test -p iris-agentic-dev-core` — confirm all pre-existing tests still
      pass after additions

**Checkpoint**: Helper functions exist and compile. Pre-existing tests still green.

---

## Phase 3: User Story 1 — fragment (Priority: P1) 🎯 MVP

**Goal**: Read a specific line range from a document without fetching the full source.

**Independent Test**: Call `iris_doc` with `mode=fragment`, `name="User.SomeClass.cls"`,
`start=1`, `end=10` on a live IRIS. Verify 10 lines returned with correct content.

### Tests for US1

> Write FIRST. Must FAIL before T020.

- [ ] T014 [US1] Create `crates/iris-agentic-dev-core/tests/unit/test_iris_doc_depth_unit.rs` —
      test `slice_lines`: `start=1, end=3` on 5-line array returns 3 lines, `actual_start=1`,
      `actual_end=3`, `clamped=false`
- [ ] T015 [P] [US1] Add unit test to `test_iris_doc_depth_unit.rs` — `slice_lines` with
      `end > len`: `end=999` on 5-line array returns all 5 lines with `clamped=true`,
      `actual_end=5`
- [ ] T016 [P] [US1] Add unit test to `test_iris_doc_depth_unit.rs` — `slice_lines` with
      `start > len`: returns empty vec, `clamped=true`
- [ ] T017 [P] [US1] Add unit test to `test_iris_doc_depth_unit.rs` — `mode=fragment` with
      missing `start` param → structured error `MISSING_PARAMS` (not panic)
- [ ] T018 [P] [US1] Add unit test to `test_iris_doc_depth_unit.rs` — `mode=fragment` with
      `start > end` (e.g. `start=10, end=5`) → structured error `INVALID_PARAMS`
- [ ] T019 [US1] Create `crates/iris-agentic-dev-core/tests/integration/test_iris_doc_depth_live.rs`
      — `#[ignore]`; fetch `%Library.Integer.cls` fragment `start=1 end=5`, verify 5 strings
      returned, each non-empty

### Implementation for US1

- [ ] T020 [US1] Implement `DocMode::Fragment` arm in `handle_iris_doc` in
      `crates/iris-agentic-dev-core/src/tools/doc.rs`:
  - Validate `start` present (`MISSING_PARAMS` if absent), `end` present (`MISSING_PARAMS`
    if absent), `start >= 1` and `end >= start` (`INVALID_PARAMS` if violated)
  - Fetch full document content via existing Atelier GET `/doc/{name}` path
  - Parse `result.content` array (same path as `DocMode::Get`)
  - Call `slice_lines(&lines, start, end)` to extract range
  - Return `{success: true, lines: Vec<String>, start: i64, end: i64, clamped: bool,
total_lines: i64, name: String}`
- [ ] T021 [US1] Run `cargo test -p iris-agentic-dev-core test_iris_doc_depth` — all US1
      unit tests pass

**Checkpoint**: US1 complete. `iris_doc fragment` returns bounded line range.
`MISSING_PARAMS` and `INVALID_PARAMS` fire before any IRIS call.

---

## Phase 4: User Story 2 — compiled (Priority: P1)

**Goal**: Fetch the compiled INT representation of a class or routine.

**Independent Test**: Call `iris_doc` with `mode=compiled`, `name="User.SomeClass.cls"` on
a live IRIS with a compiled class. Verify INT content returned.

### Tests for US2

> Write FIRST. Must FAIL before T027.

- [ ] T022 [P] [US2] Add unit test to `test_iris_doc_depth_unit.rs` — `mode=compiled` with
      `name` ending `.INC` → structured error `NOT_COMPILED` (no INT form for include files)
- [ ] T023 [P] [US2] Add unit test to `test_iris_doc_depth_unit.rs` — compiled INT name
      derivation: `"MyClass.cls"` → `"MyClass.INT"`, `"MyRoutine.mac"` → `"MyRoutine.INT"`,
      case-insensitive extension matching
- [ ] T024 [P] [US2] Add unit test to `test_iris_doc_depth_unit.rs` — `compiled_type`
      validation: `"INT"` and `"OBJ"` accepted; anything else → `INVALID_PARAMS`
- [ ] T025 [US2] Add integration test to `test_iris_doc_depth_live.rs` — `#[ignore]`;
      fetch `%Library.Integer.cls` compiled form, verify content is non-empty and category
      field is `"INT"`

### Implementation for US2

- [ ] T026 [US2] Implement `DocMode::Compiled` arm in `handle_iris_doc` in
      `crates/iris-agentic-dev-core/src/tools/doc.rs`:
  - Return `NOT_COMPILED` immediately if `name` ends with `.inc` (case-insensitive)
  - Validate `compiled_type` if provided — only `"INT"` or `"OBJ"` (default `"INT"`)
  - Derive target doc name: strip original extension, append `.INT` or `.OBJ`
  - Fetch via Atelier GET `/doc/{derived_name}` using existing get path
  - Return `{success: true, name: original_name, compiled_name: derived_name, category: "INT",
content: String, total_lines: i64}` — join lines with `\n` for content field
- [ ] T027 [US2] Run `cargo test -p iris-agentic-dev-core test_iris_doc_depth` — all US1+US2
      unit tests pass

**Checkpoint**: US2 complete. `iris_doc compiled` returns INT representation.
`NOT_COMPILED` fires for `.INC` files.

---

## Phase 5: User Story 3 — list (Priority: P2)

**Goal**: Enumerate documents in a namespace matching a glob pattern with metadata.

**Independent Test**: Call `iris_doc` with `mode=list`, `pattern="User.*"`, `category="CLS"`
on a live IRIS. Verify array of doc metadata objects returned.

### Tests for US3

> Write FIRST. Must FAIL before T033.

- [ ] T028 [P] [US3] Add unit test to `test_iris_doc_depth_unit.rs` — `validate_list_pattern`
      accepts `"User.*"`, `"MyPkg.Sub*"`, `"Exact.Name.cls"`
- [ ] T029 [P] [US3] Add unit test to `test_iris_doc_depth_unit.rs` — `validate_list_pattern`
      rejects `""`, `"*"`, `"**"`, `"*.cls"` (star-only prefix) → `MISSING_PARAMS`
- [ ] T030 [P] [US3] Add unit test to `test_iris_doc_depth_unit.rs` — `clamp_max_results`:
      `9999` → `1000`, `0` → `1`, `200` → `200`
- [ ] T031 [P] [US3] Add unit test to `test_iris_doc_depth_unit.rs` — `mode=list` missing
      `pattern` → `MISSING_PARAMS`
- [ ] T032 [US3] Add integration test to `test_iris_doc_depth_live.rs` — `#[ignore]`;
      list with `pattern="%Library.*"`, `category="CLS"`, `max_results=5`; verify response
      has `{success: true, documents: [...], total_returned: 5, truncated: true}`

### Implementation for US3

- [ ] T033 [US3] Implement `DocMode::List` arm in `handle_iris_doc` in
      `crates/iris-agentic-dev-core/src/tools/doc.rs`:
  - Validate `pattern` present via `validate_list_pattern` → `MISSING_PARAMS` on failure
  - Validate `category` if provided — allowed values: `"CLS"`, `"MAC"`, `"INT"`, `"INC"`,
    `"ALL"` (default `"ALL"`) → `INVALID_PARAMS` on unknown
  - Clamp `max_results` (default 200) via `clamp_max_results`
  - Build Atelier URL: `GET /api/atelier/v1/{ns}/docs?filter={pattern}&cat={cat}&generated=0`
  - Fetch, parse `result.content` array of `{name, cat, ts, size}` objects
  - Apply `max_results` cap, set `truncated` if capped
  - Return `{success: true, documents: [{name, category, ts, size}...],
total_returned: i64, truncated: bool, namespace: String}`
- [ ] T034 [US3] Run `cargo test -p iris-agentic-dev-core test_iris_doc_depth` — all US1–US3
      unit tests pass

**Checkpoint**: US3 complete. `iris_doc list` enumerates docs with metadata and truncation.

---

## Phase 6: User Story 4 — iris_execute_method (Priority: P2)

**Goal**: Invoke a ClassMethod directly by class+method+args without writing wrapper code.

**Independent Test**: Call `iris_execute_method` with `class="%Library.Integer"`,
`method="IsValid"`, `args=["42"]` on a live IRIS. Verify `1` returned.

### Tests for US4

> Write FIRST. Must FAIL before T040.

- [ ] T035 [US4] Add unit test to `test_iris_doc_depth_unit.rs` — `iris_execute_method`
      missing `class` → `MISSING_PARAMS`
- [ ] T036 [P] [US4] Add unit test to `test_iris_doc_depth_unit.rs` — `iris_execute_method`
      missing `method` → `MISSING_PARAMS`
- [ ] T037 [P] [US4] Add unit test to `test_iris_doc_depth_unit.rs` — `iris_execute_method`
      on `mcpTemplate=live` → `ENV_GATE_BLOCKED` (Execute category blocked on live)
- [ ] T038 [P] [US4] Add unit test to `test_iris_doc_depth_unit.rs` — `iris_execute_method`
      on `mcpTemplate=test` → `ENV_GATE_BLOCKED`
- [ ] T039 [US4] Add integration test to `test_iris_doc_depth_live.rs` — `#[ignore]`;
      call `%Library.Integer:IsValid` with `args=["42"]`, verify `"1"` in result; call
      with `args=["not-an-int"]`, verify `"0"` in result

### Implementation for US4

- [ ] T040 [US4] Implement `iris_execute_method` handler in
      `crates/iris-agentic-dev-core/src/tools/mod.rs`:
  - Parse `class` (required), `method` (required), `args: Vec<String>` (default `[]`),
    `namespace` (default connection default)
  - Call `dispatch_gate("iris_execute_method", ...)` — returns `ENV_GATE_BLOCKED` on
    live/test templates (Execute category)
  - Build ObjectScript for `execute_via_generator`:
    - Validate `class` against system blocklist pattern (same PHI/system check as iris_global:
      reject `%SYS`-rooted, PAPMI, etc.) → `SYSTEM_BLOCKLIST` / `PHI_GATE_BLOCKED`
    - Build args as comma-separated quoted literals (escape `"` → `""` in each arg)
    - Code: `Set result = ##class({class}).{method}({args_csv})\n Write result,$C(10)`
    - **No `{`/`}` in output** — plain string result only; document v1 limitation
  - Call `execute_via_generator(&code, &ns, client)`
  - Return `{success: true, result: String}` on success; `IRIS_EXECUTE_ERROR` on error
- [ ] T041 [US4] Run `cargo test -p iris-agentic-dev-core test_iris_doc_depth` — all US1–US4
      unit tests pass

**Checkpoint**: US4 complete. `iris_execute_method` invokes ClassMethod, Execute-gated.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Integration tests, tool inventory, AGENTS.md update, final fmt/clippy pass.

- [ ] T042 [P] Verify `iris_execute_method` appears in `check_config` tool inventory —
      add assertion to `crates/iris-agentic-dev-core/tests/unit/test_server_manager.rs`
      that `registered_tool_names()` contains `"iris_execute_method"`
- [ ] T043 [P] Update `light-skills/AGENTS.md` — add `iris_doc` mode extensions
      (`fragment`, `compiled`, `list`) and `iris_execute_method` to the MCP tool reference
      section with usage examples for each mode
- [ ] T044 Run full test suite: `cargo test -p iris-agentic-dev-core` — all non-ignored
      tests pass, zero regressions
- [ ] T045 Run `cargo fmt --all -- --check` — no formatting diff
- [ ] T046 Run `cargo clippy -p iris-agentic-dev-core -- -D warnings` — zero warnings
- [ ] T047 [P] Update spec status to `Status: Implemented` in
      `specs/053-doc-depth/spec.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 (needs doc.rs additions to exist)
- **Phase 3 (US1 fragment)**: Depends on Phase 2 (needs `slice_lines` helper)
- **Phase 4 (US2 compiled)**: Depends on Phase 1; independent of Phase 3
- **Phase 5 (US3 list)**: Depends on Phase 2 (needs `validate_list_pattern`, `clamp_max_results`)
- **Phase 6 (US4 iris_execute_method)**: Depends on Phase 1; independent of US1–US3
- **Phase 7 (Polish)**: Depends on all US phases complete

### User Story Dependencies

- **US1 (fragment)**: Phase 2 complete
- **US2 (compiled)**: Phase 1 complete; independent of US1
- **US3 (list)**: Phase 2 complete; independent of US1/US2
- **US4 (iris_execute_method)**: Phase 1 complete; independent of US1/US2/US3

### Within Each Phase

- Tests written FIRST, must FAIL before implementation
- Phase 2 helpers must exist before US1/US3 implementation
- Action-aware gate for `iris_execute_method` uses existing Execute category — no
  `env_gate.rs` change needed (unlike iris_global which needed action-aware override)

### Parallel Opportunities

- T014–T018 (US1 unit tests) — T015–T018 parallel after T014 creates the file
- T022–T024 (US2 unit tests) — all parallel (appending to existing file)
- T028–T031 (US3 unit tests) — all parallel
- T035–T038 (US4 unit tests) — T036–T038 parallel after T035
- T042–T043 (Polish) — parallel

---

## Parallel Example: Phase 3 (US1)

```text
# Write tests first (T014 creates file, T015–T018 parallel):
T014 → [T015, T016, T017, T018 in parallel] → T019

# Then implement (T020 sequential, T021 validates):
T020 → T021
```

---

## Implementation Strategy

### MVP First (US1 + US2 only — the two P1 stories)

1. Complete Phase 1: Setup (T001–T009)
2. Complete Phase 2: Foundational (T010–T013)
3. Complete Phase 3: US1 fragment (T014–T021)
4. Complete Phase 4: US2 compiled (T022–T027)
5. **STOP and VALIDATE**: `cargo test test_iris_doc_depth` green; fragment + compiled work live
6. Ship — fragment and compiled are the highest-value read operations

### Incremental Delivery

1. Setup + Foundational → new DocMode variants compile, helpers ready
2. US1 fragment → line range reads without full fetch
3. US2 compiled → INT representation for stack trace correlation
4. US3 list → document enumeration with metadata
5. US4 iris_execute_method → ClassMethod invocation
6. Polish → inventory, docs, fmt/clippy

---

## Notes

- `iris_execute_method` is the only truly new tool (not a new mode of an existing tool).
  It must appear in `check_config` inventory and the Merged toolset removal list.
- Fragment re-fetches the full doc then slices in Rust — this is intentional; Atelier has
  no server-side line range parameter. For large classes this is acceptable: the bottleneck
  is IRIS network latency, not slice allocation.
- Compiled mode fetches `.INT` — if the class was never compiled (e.g., newly written),
  Atelier returns a 404 or empty content. Handle as `NOT_COMPILED` response (same as INC).
- `iris_execute_method` v1 limitation: only string-returning methods. If the method returns
  an object reference or multi-dimensional array, `Write result` will produce the OID string
  or an error. Document this in AGENTS.md under known limitations.
- All integration tests use `%Library.*` system classes (read-only, always present on IRIS)
  to avoid test-data setup complexity.
