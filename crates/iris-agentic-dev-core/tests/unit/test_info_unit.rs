//! Unit tests for info.rs — InfoParams, MacroParams, GenerateParams, TableInfoParams serde.

use iris_agentic_dev_core::tools::info::{
    GenerateParams, InfoParams, MacroParams, TableInfoParams,
};

#[test]
fn info_params_defaults() {
    let p: InfoParams = serde_json::from_str(r#"{"what":"documents"}"#).unwrap();
    assert_eq!(p.what, "documents");
    assert!(p.doc_type.is_none());
    assert_eq!(p.namespace, "USER");
    assert!(!p.inline);
}

#[test]
fn info_params_with_doc_type() {
    let p: InfoParams = serde_json::from_str(r#"{"what":"documents","doc_type":"CLS"}"#).unwrap();
    assert_eq!(p.doc_type.as_deref(), Some("CLS"));
}

#[test]
fn info_params_missing_what_fails() {
    let r: Result<InfoParams, _> = serde_json::from_str(r#"{}"#);
    assert!(r.is_err(), "what is required");
}

#[test]
fn macro_params_defaults() {
    let p: MacroParams = serde_json::from_str(r#"{"action":"list"}"#).unwrap();
    assert_eq!(p.action, "list");
    assert!(p.name.is_none());
    assert!(p.args.is_empty());
    assert_eq!(p.namespace, "USER");
}

#[test]
fn macro_params_with_name_and_args() {
    let p: MacroParams =
        serde_json::from_str(r#"{"action":"expand","name":"MYCLASS","args":["arg1"]}"#).unwrap();
    assert_eq!(p.name.as_deref(), Some("MYCLASS"));
    assert_eq!(p.args.len(), 1);
}

#[test]
fn generate_params_defaults_gen_type_class() {
    let p: GenerateParams = serde_json::from_str(r#"{"description":"a simple class"}"#).unwrap();
    assert_eq!(p.gen_type, "class");
    assert!(p.class_name.is_none());
    assert_eq!(p.namespace, "USER");
}

#[test]
fn generate_params_test_type() {
    let p: GenerateParams = serde_json::from_str(
        r#"{"description":"tests for Foo","gen_type":"test","class_name":"Foo.Bar"}"#,
    )
    .unwrap();
    assert_eq!(p.gen_type, "test");
    assert_eq!(p.class_name.as_deref(), Some("Foo.Bar"));
}

#[test]
fn table_info_params_defaults() {
    let p: TableInfoParams = serde_json::from_str(r#"{"table":"SQLUser.MyTable"}"#).unwrap();
    assert_eq!(p.table, "SQLUser.MyTable");
    assert_eq!(p.namespace, "USER");
    assert!(!p.include_row_count);
}

#[test]
fn table_info_params_with_row_count() {
    let p: TableInfoParams =
        serde_json::from_str(r#"{"table":"App.Orders","include_row_count":true}"#).unwrap();
    assert!(p.include_row_count);
}

#[test]
fn table_info_params_missing_table_fails() {
    let r: Result<TableInfoParams, _> = serde_json::from_str(r#"{}"#);
    assert!(r.is_err(), "table is required");
}
