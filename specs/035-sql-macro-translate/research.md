# Research: iris_execute &sql Macro Translation

## What &sql Actually Compiles To (Constitution II Verification)

**Finding**: The IRIS `&sql(...)` preprocessor does NOT generate `%SQL.Statement` calls. It generates cached query class calls via `$classmethod("%sqlcq.*", "%New")` with a fallback to `BuildQuery^%SYS.SQLSRV`. The generated INT for:

```objectscript
&sql(SELECT Name INTO :name FROM %Dictionary.ClassDefinition WHERE ID = :id)
```

expands to roughly:
```
try { d $classmethod("%sqlcq.USER...hash","%New") }
catch { if ($ze["<CLASS DOES NOT EXIST>"||...) { d %0dsqlA } else { throw } }
...
%0dsqlA: s %xxsql("S",1)="SELECT Name INTO :name FROM %Dictionary.ClassDefinition WHERE ID = :id"
         do BuildQuery^%SYS.SQLSRV(.%xxsql,...)
```

This is namespace-specific, compile-time generated, and not suitable as a runtime translation target.

## Correct Translation Target: %SQL.Statement

**Decision**: Use `%SQL.Statement` class methods as the translation target.

**Verification against live iris-dev-iris (IRIS 2025.1)**:
- `##class(%SQL.Statement).%New()` — verified ✅
- `.%Prepare("SELECT ...")` — verified ✅
- `.%Execute(param1, param2, ...)` — verified ✅
- `.%Next()` — verified ✅
- `.%Get("ColumnName")` — verified ✅
- `.%SQLCODE` — verified ✅
- `##class(%SQL.Statement).%ExecDirect(, "INSERT ...", params...)` — verified ✅

Test run: `SqlStmtTest` class with `%SQL.Statement` SELECT produces identical output to `&sql` for the same query. ✅

**Rationale**: `%SQL.Statement` is the documented, stable, runtime SQL API for IRIS. Unlike `%sqlcq.*` cached classes, it's always available and works in the `execute_via_generator` runtime context.

## Translation Algorithm

### SELECT INTO

Input:
```objectscript
&sql(SELECT Name, Age INTO :name, :age FROM MyApp.Patient WHERE ID = :id)
```

Output:
```objectscript
set _sqlrs1 = ##class(%SQL.Statement).%New()
set _sqlsc1 = _sqlrs1.%Prepare("SELECT Name, Age FROM MyApp.Patient WHERE ID = ?")
set _sqlrs1 = _sqlrs1.%Execute(id)
if _sqlrs1.%Next() {
  set name = _sqlrs1.%Get("Name")
  set age = _sqlrs1.%Get("Age")
} else {
  set name = ""
  set age = ""
  set _sqlSQLCODE1 = _sqlrs1.%SQLCODE
}
```

Next-line SQLCODE rewrite: `if SQLCODE` → `if _sqlSQLCODE1`

### DML (INSERT/UPDATE/DELETE/MERGE)

Input:
```objectscript
&sql(INSERT INTO MyApp.Log (Message, Level) VALUES (:msg, :lvl))
```

Output:
```objectscript
set _sqlrs1 = ##class(%SQL.Statement).%ExecDirect(, "INSERT INTO MyApp.Log (Message, Level) VALUES (?, ?)", msg, lvl)
set _sqlSQLCODE1 = _sqlrs1.%SQLCODE
```

### Parsing Strategy

1. Find `&sql(` — record position
2. Walk forward counting paren depth (handle nested parens in SQL: `WHERE x IN (SELECT...)`)
3. Extract contents between outer `&sql(` and matching `)`
4. Classify: SELECT/INSERT/UPDATE/DELETE/MERGE/other
5. For SELECT: extract `INTO :var1, :var2` clause → output vars; remove INTO clause from SQL; extract WHERE `:param` vars
6. For DML: extract `:varname` in order → positional `?`
7. Check next line for standalone `SQLCODE` or `%msg` reference → rewrite to `_sqlSQLCODEn` / `_sqlrs1.%Message`
8. If CALL or unrecognized: leave unchanged, add warning

### Collision Avoidance

Generated variable names: `_sqlrs1`, `_sqlrs2`, ... ; `_sqlsc1`, `_sqlsc2`, ... ; `_sqlSQLCODE1`, etc.
The `_sql` prefix is reserved for translation output. If user code contains `_sqlrs1`, translation uses `_sqlrs2` (scan for conflicts before assignment — unlikely in practice but handled).

## %SQL.Statement Column Name Source

For `SELECT Name INTO :name` — the column alias in the translated `%Get("Name")` must match the SELECT column name. The translation extracts column names from the SELECT list (before `INTO`). For `SELECT a.Name` → `%Get("Name")` (strip table alias). For `SELECT Name AS n` → `%Get("n")`.

## SQLCODE Semantics Parity (Clarification Q2)

When SELECT INTO returns no rows:
- `%Next()` returns 0 (false)
- Set host vars to `""` (empty string)  
- `_sqlSQLCODE1 = _sqlrs1.%SQLCODE` will be 100 (SQLCODE 100 = no data)
- This matches `&sql` preprocessor behavior exactly ✅
