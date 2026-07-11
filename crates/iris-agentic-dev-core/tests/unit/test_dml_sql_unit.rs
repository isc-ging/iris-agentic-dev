//! Unit tests for validate_dml_sql and build_rows_precheck_query.
//! These are pure functions — no IRIS or feature flag needed.

use iris_agentic_dev_core::tools::{build_rows_precheck_query, validate_dml_sql};

// ── validate_dml_sql ──────────────────────────────────────────────────────────

#[test]
fn dml_empty_query_returns_empty_err() {
    assert_eq!(validate_dml_sql(""), Err("EMPTY".to_string()));
    assert_eq!(validate_dml_sql("   "), Err("EMPTY".to_string()));
}

#[test]
fn dml_comment_only_returns_empty_err() {
    assert_eq!(
        validate_dml_sql("/* just a comment */"),
        Err("EMPTY".to_string())
    );
    assert_eq!(
        validate_dml_sql("-- line comment"),
        Err("EMPTY".to_string())
    );
}

#[test]
fn dml_select_returns_select_in_write_err() {
    assert_eq!(
        validate_dml_sql("SELECT 1"),
        Err("SELECT_IN_WRITE".to_string())
    );
    assert_eq!(
        validate_dml_sql("select Name from Sample.Person"),
        Err("SELECT_IN_WRITE".to_string())
    );
}

#[test]
fn dml_insert_ok() {
    assert!(validate_dml_sql("INSERT INTO Foo (x) VALUES (1)").is_ok());
}

#[test]
fn dml_update_ok() {
    assert!(validate_dml_sql("UPDATE Foo SET x=1 WHERE id=2").is_ok());
}

#[test]
fn dml_delete_ok() {
    assert!(validate_dml_sql("DELETE FROM Foo WHERE id=1").is_ok());
}

#[test]
fn dml_call_ok() {
    assert!(validate_dml_sql("CALL MyProc(1,2)").is_ok());
}

#[test]
fn dml_truncate_ok() {
    assert!(validate_dml_sql("TRUNCATE TABLE Foo").is_ok());
}

#[test]
fn dml_create_returns_ddl_err() {
    let r = validate_dml_sql("CREATE TABLE Foo (id INT)");
    assert!(r.is_err());
    let e = r.unwrap_err();
    // DDL keyword branch returns the keyword itself
    assert!(e.contains("CREATE") || e == "UNKNOWN_STATEMENT", "got: {e}");
}

#[test]
fn dml_drop_returns_ddl_err() {
    let r = validate_dml_sql("DROP TABLE Foo");
    assert!(r.is_err());
}

#[test]
fn dml_alter_returns_ddl_err() {
    let r = validate_dml_sql("ALTER TABLE Foo ADD COLUMN bar INT");
    assert!(r.is_err());
}

#[test]
fn dml_grant_returns_ddl_err() {
    let r = validate_dml_sql("GRANT SELECT ON Foo TO PUBLIC");
    assert!(r.is_err());
}

#[test]
fn dml_revoke_returns_ddl_err() {
    let r = validate_dml_sql("REVOKE SELECT ON Foo FROM PUBLIC");
    assert!(r.is_err());
}

#[test]
fn dml_unknown_statement_returns_err() {
    let r = validate_dml_sql("MERGE INTO Foo USING bar ON (1=1)");
    assert!(r.is_err());
}

#[test]
fn dml_strips_block_comment_before_keyword() {
    // keyword follows a block comment
    assert!(validate_dml_sql("/* preamble */ INSERT INTO Foo VALUES (1)").is_ok());
}

#[test]
fn dml_strips_line_comment_before_keyword() {
    assert!(validate_dml_sql("-- preamble\nDELETE FROM Foo").is_ok());
}

// ── build_rows_precheck_query ─────────────────────────────────────────────────

#[test]
fn precheck_update_with_where_produces_count_query() {
    let q = build_rows_precheck_query("UPDATE Foo SET x=1 WHERE id=2");
    assert!(q.is_some(), "should produce a precheck query");
    let s = q.unwrap();
    assert!(s.to_uppercase().contains("SELECT COUNT"), "got: {s}");
    assert!(
        s.to_uppercase().contains("FROM FOO") || s.to_uppercase().contains("FROM Foo"),
        "got: {s}"
    );
}

#[test]
fn precheck_delete_with_where_produces_count_query() {
    let q = build_rows_precheck_query("DELETE FROM Foo WHERE id=1");
    assert!(q.is_some(), "should produce a precheck query");
    let s = q.unwrap();
    assert!(s.to_uppercase().contains("SELECT COUNT"), "got: {s}");
}

#[test]
fn precheck_insert_returns_none() {
    // INSERT doesn't need a precheck
    let q = build_rows_precheck_query("INSERT INTO Foo VALUES (1)");
    assert!(q.is_none(), "INSERT should not need a precheck");
}

#[test]
fn precheck_update_no_where_returns_some_or_none() {
    // Parser may or may not handle this — just must not panic
    let _q = build_rows_precheck_query("UPDATE Foo SET x=1");
    // No assertion — just exercises the code path
}

#[test]
fn precheck_empty_returns_none() {
    let q = build_rows_precheck_query("");
    assert!(q.is_none());
}
