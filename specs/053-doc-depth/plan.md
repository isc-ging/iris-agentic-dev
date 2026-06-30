# Implementation Plan: Document Depth — iris_doc Extensions + iris_execute_method

**Branch**: `053-doc-depth`
**Spec**: spec.md
**Depends on**: 051 (dispatch_gate, McpTemplate — merged)

## Tech Stack

- Rust 1.92 (workspace edition 2021)
- `iris-agentic-dev-core` crate — all changes here
- `serde_json` — param parsing, response building
- `reqwest` — HTTP calls to Atelier REST endpoints
- Atelier REST API — `/doc/{name}` (get, fragment slicing), `/doc/{name}.INT` (compiled),
  `/docs` with filter params (list)
- `execute_via_generator` — ClassMethod invocation for `iris_execute_method`
- Policy gate: `dispatch_gate()` from `crates/iris-agentic-dev-core/src/policy/gate.rs`

## File Structure

```text
crates/iris-agentic-dev-core/src/tools/doc.rs         # MODIFY — add Fragment/Compiled/List modes
crates/iris-agentic-dev-core/src/tools/mod.rs         # MODIFY — new iris_execute_method tool + descriptions
crates/iris-agentic-dev-core/src/iris/server_manager.rs  # MODIFY — tool_to_category for iris_execute_method
tests/unit/test_iris_doc_depth_unit.rs                 # NEW — unit tests (no IRIS)
tests/integration/test_iris_doc_depth_live.rs          # NEW — integration tests (#[ignore])
```

## DocMode Extension

Add three new variants to the `DocMode` enum in `doc.rs`:

```rust
pub enum DocMode {
    Get,
    Put,
    Delete,
    Head,
    Fragment,   // NEW — line range read
    Compiled,   // NEW — fetch INT/OBJ compiled form
    List,       // NEW — enumerate docs matching pattern
}
```

New params added to `IrisDocParams`:

- `start: Option<i64>` — fragment start line (1-based)
- `end: Option<i64>` — fragment end line (inclusive)
- `compiled_type: Option<String>` — `"INT"` (default) or `"OBJ"` for mode=compiled
- `pattern: Option<String>` — glob pattern for mode=list (required)
- `category: Option<String>` — `"CLS"`, `"MAC"`, `"INT"`, `"INC"`, `"ALL"` filter for mode=list
- `max_results: Option<i64>` — cap for mode=list (default 200, max 1000)

## Fragment Implementation

Atelier `GET /doc/{name}` returns `result.content` as a flat `Vec<String>` of line strings
(confirmed from existing `doc_content_to_string`). Fragment slices this array:

```rust
async fn handle_fragment(iris, client, p) {
    // fetch full doc via existing GET endpoint
    // slice lines[start-1..=end-1], clamping end to len
    // return { lines: Vec<String>, start, end, clamped, total_lines }
}
```

No new Atelier endpoint needed — reuses existing `/doc/{name}` GET.

## Compiled Implementation

Atelier supports fetching compiled INT by appending `.INT` to the class name:

```text
GET /api/atelier/v1/{ns}/doc/MyClass.INT
```

For `.MAC` routines: request `MyRoutine.INT` (same pattern).
For `.INC` includes: return `NOT_COMPILED` immediately (no INT form exists).

The response shape mirrors `mode=get` but with `category: "INT"`.

Stale detection: compare `ts` field from the INT response vs the CLS source `ts` — if INT
`ts` is older, set `stale: true`. If either timestamp is absent, omit `stale`.

## List Implementation

Atelier `GET /docs?filter={pattern}&cat={category}` returns a document listing.
Check the existing `iris_info(what=documents)` handler in `info.rs` — it uses `/docnames/CLS`
already. For `mode=list` we need the richer `/docs` endpoint that returns metadata
(size, modified date per document).

```text
GET /api/atelier/v1/{ns}/docs?filter={glob}&cat={cat}&generated=0
```

Response: `result.content` array of `{name, cat, ts, size}` objects.

Clamp to `max_results` (default 200, max 1000). Pattern validation: reject empty,
`*`, `**`, or patterns starting with `*` with no prefix — `MISSING_PARAMS`.

## iris_execute_method — New Tool

New tool registered in `mod.rs`. No new file needed — handler inline in `mod.rs` or
small helper in `doc.rs`.

Params: `class` (required), `method` (required), `args: Vec<String>` (default empty),
`namespace` (default connection default).

Implementation via `execute_via_generator`:

```objectscript
 Set result = ##class({class}).{method}({args_csv})
 Write result,$C(10)
```

Gate classification: `ToolCategory::Execute` — blocked on `live` and `test` templates.
`dispatch_gate()` applies — system blocklist and PHI name gate on `class` param.

**Constraint**: No `{`/`}` in generator output (same as iris_global). Return value as
plain text; `iris_execute_method` only supports string-returning methods for v1.

## Tool Category

- `mode=fragment`, `mode=compiled`, `mode=list` → `ToolCategory::Query` (existing iris_doc
  is already Query; these new modes inherit it — no `env_gate.rs` change needed)
- `iris_execute_method` → `ToolCategory::Execute` — add to `tool_to_category()` in
  `server_manager.rs`

## Toolset Registration

`iris_execute_method` uses `execute_via_generator` (HTTP-only). Belongs in
**`Toolset::Merged`** — add to both `registered_tool_names()` and the Merged removal list
in `with_registry_and_toolset()`.

---

## Constitution Check

| Principle                      | Status  | Notes                                                                                   |
| ------------------------------ | ------- | --------------------------------------------------------------------------------------- |
| I. Zero-Install Binary         | ✅ Pass | All modes use Atelier HTTP; `execute_via_generator` for method invocation               |
| II. ObjectScript Sanity        | ✅ Pass | Fragment/compiled/list use existing Atelier endpoints; `##class().method()` is standard |
| III. HTTP-First                | ✅ Pass | No Docker dependency; all calls via `reqwest`                                           |
| IV. Test-First, Fixture-Driven | ✅ Pass | Unit tests precede implementation in every phase                                        |
| V. Output Shape Parity         | ✅ Pass | Response shapes defined in spec; error codes follow SCREAMING_SNAKE_CASE                |
| VI. Environment Guard          | ✅ Pass | `iris_execute_method` is Execute-gated; new doc modes are Query                         |
| VII. Dependency Minimalism     | ✅ Pass | No new crates; reuses existing `doc.rs` infrastructure                                  |

---

## Phase Structure

1. **Setup**: Add `DocMode` variants + new params to `IrisDocParams` + compile stub arms
2. **US1 (fragment)**: Unit tests → `handle_fragment` implementation
3. **US2 (compiled)**: Unit tests → `handle_compiled` implementation
4. **US3 (list)**: Unit tests → `handle_list` implementation
5. **US4 (iris_execute_method)**: Unit tests → new tool registration + handler
6. **Polish**: Integration tests, `check_config` inventory, AGENTS.md update, fmt/clippy
