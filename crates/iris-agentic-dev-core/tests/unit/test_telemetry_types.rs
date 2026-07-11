//! Unit tests for telemetry core types (T007). No live IRIS required.

use iris_agentic_dev_core::telemetry::{ago_secs, now_rfc3339, Session, ToolCallRecord};
use uuid::Uuid;

#[test]
fn tool_call_record_round_trips_via_serde_json() {
    let sid = Uuid::new_v4();
    let record = ToolCallRecord::now("iris_compile", true, 42, sid);
    let json = serde_json::to_string(&record).unwrap();
    let back: ToolCallRecord = serde_json::from_str(&json).unwrap();
    assert_eq!(back.tool, "iris_compile");
    assert!(back.success);
    assert_eq!(back.duration_ms, 42);
    assert_eq!(back.session_id, sid);
}

#[test]
fn session_new_produces_non_nil_uuid() {
    let s = Session::new();
    assert_ne!(s.id, Uuid::nil());
}

#[test]
fn two_sessions_produce_distinct_ids() {
    let a = Session::new();
    let b = Session::new();
    assert_ne!(a.id, b.id);
}

#[test]
fn now_rfc3339_produces_non_empty_string() {
    let ts = now_rfc3339();
    assert!(!ts.is_empty());
    // Should be parseable as RFC3339
    assert!(chrono::DateTime::parse_from_rfc3339(&ts).is_ok());
}

#[test]
fn ago_secs_returns_zero_for_invalid_timestamp() {
    assert_eq!(ago_secs("not-a-timestamp"), 0);
    assert_eq!(ago_secs(""), 0);
}

#[test]
fn ago_secs_returns_nonzero_for_past_timestamp() {
    // A timestamp far in the past should produce a large positive value
    let old_ts = "2020-01-01T00:00:00Z";
    let secs = ago_secs(old_ts);
    assert!(secs > 0, "past timestamp should have positive ago_secs");
}

#[test]
fn tool_call_record_with_params_serializes() {
    let sid = Uuid::new_v4();
    let mut record = ToolCallRecord::now("iris_query", true, 55, sid);
    record.params = Some(serde_json::json!({"query": "SELECT 1"}));
    let json = serde_json::to_string(&record).unwrap();
    let back: ToolCallRecord = serde_json::from_str(&json).unwrap();
    assert_eq!(back.params.unwrap()["query"], "SELECT 1");
}
