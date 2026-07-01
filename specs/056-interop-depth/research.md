# Research: Interoperability Depth Tools

Verified against live IRIS 2026.2.0L (Build 208U), `iris-dev-iris` container.

## iris_message_body — Ens.MessageHeader / body classes

- **`Ens.MessageHeader` exists**: YES. Verified properties (does NOT have a `MessageBody`
  object property as the plan assumed):
  `MessageBodyClassName` (%String), `MessageBodyId` (%String), `Status`, `IsError`,
  `SourceConfigName`, `TargetConfigName`, `TimeCreated`, `TimeProcessed`, `SessionId`.
- **Decision**: Open the header via `##class(Ens.MessageHeader).%OpenId(msgId)`. If not an
  object → `MESSAGE_NOT_FOUND`. Then open the body via
  `##class($header.MessageBodyClassName).%OpenId($header.MessageBodyId)` (dynamic class
  open via `##class()` with a runtime class-name string — supported ObjectScript pattern
  using indirection `$CLASSNAME` or `##class(@className).%OpenId(...)`).
- **`Ens.StreamContainer` exists**: YES. Properties: `Stream` (`%Stream.Object`, generic),
  plus typed variants `StreamBF/StreamBG/StreamCF/StreamCG` (file/global, binary/character).
  Use the generic `Stream` property for `%IsA("Ens.StreamContainer")` detection, then
  `.Stream.Read(maxBytes)` (via `%Stream.Object` API) to fetch up to `max_bytes`.
- **Plain-string bodies**: Many custom body classes simply store content directly as a
  string property (commonly named `MessageString`, `RawContent`, or similar) — not
  standardized. v1 strategy: if the body class is NOT `Ens.StreamContainer`-derived and
  is NOT `%Stream.Object`-derived, serialize via `%XML.Writer` or fall back to a documented
  `body_property` convention (`%Stream.Object`-compatible classes preferred; else attempt
  `$Property(body, "RawContent")` as a best-effort, returning `UNSUPPORTED_BODY_CLASS` if
  no recognizable content property exists).

## iris_business_rule_info — Ens.Rule.RuleSet / Ens.Rule.Rule

- **`EnsLib.Rules.Definition` does NOT exist** (plan's assumption was wrong — hallucinated
  class name).
- **Correct API**: `Ens.Rule.RuleSet` is the rule-set persistent class. SQL-projected to
  `Ens_Rule.RuleSet` (verified: `SELECT TOP 5 * FROM Ens_Rule.RuleSet` → SQLCODE 0).
  Verified columns: `Name`, `Production`, `ShortDescription`, `TimeModified`, `Version`,
  `HasErrors`, `RoutineName`, `FullName`, `EffectiveEndDateTime`. The `Rules` property is
  a collection of `Ens.Rule.Rule`.
- **`Ens.Rule.Rule` exists**, properties verified: `Actions` (`Ens.Rule.Action`),
  `Conditions` (`Ens.Rule.Condition`), `Disabled` (%Boolean), `ReturnValue`, `RuleNo`,
  `RuleSet` (parent ref), `SubRules`.
- **`Ens.Rule.Definition`** is an *abstract* base class — actual compiled business rule
  classes are generated subclasses (e.g. `MyApp.RoutingRule`), not directly queryable as
  a flat extent. v1 scope decision: use `Ens_Rule.RuleSet` SQL table for `action=list`
  (gives name/description/modified — matches FR-011's required shape directly, no need
  to enumerate subclasses of the abstract base). For `action=get`, open the `RuleSet` by
  `Name`, then iterate its `Rules` collection to build `conditions`/`actions` arrays from
  each `Ens.Rule.Rule`'s `Conditions`/`Actions` collections.
- **No rules configured on dev instance** — empty result set confirmed valid (SQLCODE 0,
  zero rows), not an error. `action=list` on an empty/no-Ensemble namespace must distinguish
  "table exists, zero rows" (empty `rules: []`) from "table doesn't exist"
  (`INTEROP_NOT_AVAILABLE`, checked via `%Dictionary.ClassDefinition.%ExistsId("Ens.Rule.RuleSet")`
  before querying).

## iris_production_diff — Ens.Config.Production / Ens.Config.Item

- **`Ens.Config.Production` exists**: YES, persistent, SQL-projected to `Ens_Config.Production`
  (verified SQLCODE 0). Properties: `Name`, `Description`, `Items` (collection of
  `Ens.Config.Item`), `ActorPoolSize`, `TestingEnabled`.
- **`Ens.Config.Item` exists**: YES, SQL-projected to `Ens_Config.Item` (verified SQLCODE 0).
  Properties: `Name`, `ClassName`, `Category`, `Enabled`, `Production` (parent ref),
  `PoolSize`, `Comment`, `Schedule`. This is the per-business-host record — matches the
  spec's `ProductionItem` entity directly.
- **SCM check**: `%Studio.SourceControl.Interface` exists, confirmed by the existing
  `iris_source_control` tool implementation (`crates/iris-agentic-dev-core/src/tools/scm.rs`),
  which already uses `##class(%Studio.SourceControl.Interface).SourceControlCreate(...)`
  and `.GetStatus(docName, .isInSC, .editable, .isCheckedOut, .owner)`. Reuse this exact
  pattern: doc name for a production is `<ProductionClassName>.cls`.
- **Diff strategy (v1, per spec assumption §6 — no property-level diff)**:
  1. Check SCM status for `<production>.cls` via `GetStatus` — if `isInSC=0` → `NO_SCM`.
  2. If in SCM but the document does not yet have a committed revision (SCM-specific —
     for the default `%Studio.SourceControl.Interface` deployments, "no committed version"
     is the same `UNCONTROLLED` outcome as "not in SCM" from this API's perspective — treat
     `NO_SCM_VERSION` as a sub-case only reachable if the SCM implementation differentiates;
     document this as a known limitation since the default SCM plugin used by
     `iris_source_control` does not expose a distinct "configured but uncommitted" state).
  3. Fetch current production's `Items` via `Ens.Config.Production.%OpenId(name)` (open
     by class name — production name typically equals its ObjectScript class name).
  4. Fetch the SCM-committed source via Atelier REST `GET .../doc/<ProductionClassName>.cls`
     (same mechanism the rest of the codebase uses for doc retrieval — already available
     via `IrisConnection`), parse the `<Item Name=... ClassName=... Enabled=...>` XML
     elements out of the class's XData/UDL definition block to get the committed item set.
  5. Diff committed vs current item sets by `Name` key: present-in-current-only → `added`;
     present-in-SCM-only → `removed`; present-in-both with `ClassName`/`Enabled` differing →
     `modified`.

## Constitution Compliance

| Principle | Status |
|---|---|
| I. Zero-Install | Pass — `execute_via_generator` (HTTP) only, no Docker required |
| II. ObjectScript Sanity | **Pass** — all APIs re-verified against live IRIS 2026.2; plan's `EnsLib.Rules.Definition` and `header.MessageBody` assumptions were WRONG and corrected above |
| III. HTTP-First | Pass |
| IV. Test-First | Pass — unit tests precede implementation per tasks.md |
| V. Output Shape Parity | Pass — response shapes below |
| VI. Environment Guard | Pass — all three Query category, no write gating needed |
| VII. Dependency Minimalism | Pass — no new crates |
| VIII. 90% Coverage Gate | Tracked at Polish phase |

## Corrected Response Shapes

No change to spec.md response JSON shapes — only the internal ObjectScript/class names
used to produce them differ from plan.md. Plan.md's example code blocks for
`iris_message_body` and `iris_business_rule_info` are WRONG and must not be used verbatim;
see corrected ObjectScript patterns in this document instead.
