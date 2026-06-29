//! iris_global — read, write, kill, and list IRIS globals.

use regex::Regex;
use std::sync::OnceLock;

fn err_json(code: &str, msg: &str) -> serde_json::Value {
    serde_json::json!({"success": false, "error_code": code, "message": msg})
}

// ---------------------------------------------------------------------------
// Subscript validation
// ---------------------------------------------------------------------------

static SUBSCRIPT_RE: OnceLock<Regex> = OnceLock::new();

fn subscript_regex() -> &'static Regex {
    SUBSCRIPT_RE.get_or_init(|| Regex::new(r"^[a-zA-Z0-9 _.:\-]+$").expect("valid regex"))
}

/// Validate that each subscript matches the allowlist pattern.
/// Returns an `INVALID_SUBSCRIPT` error JSON on the first failing subscript.
pub fn validate_subscripts(subscripts: &[String]) -> Result<(), serde_json::Value> {
    let re = subscript_regex();
    for sub in subscripts {
        if !re.is_match(sub) {
            return Err(serde_json::json!({
                "success": false,
                "error_code": "INVALID_SUBSCRIPT",
                "message": format!("subscript '{}' contains disallowed characters (allowed: a-z A-Z 0-9 space . _ : -)", sub),
                "subscript": sub,
                "pattern": "^[a-zA-Z0-9 _.:\\-]+$"
            }));
        }
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// Global name normalization
// ---------------------------------------------------------------------------

/// Strip a leading `^` from a global name. `^MyApp` → `MyApp`.
pub fn normalize_global_name(name: &str) -> String {
    name.strip_prefix('^').unwrap_or(name).to_string()
}

// ---------------------------------------------------------------------------
// Global reference builder
// ---------------------------------------------------------------------------

/// Build an IRIS global reference string for use in ObjectScript.
/// `build_global_ref("MyApp", &["a","b"])` → `^MyApp("a","b")`
/// `build_global_ref("MyApp", &[])` → `^MyApp`
///
/// Subscripts MUST already be validated (no quotes or special chars).
pub fn build_global_ref(name: &str, subscripts: &[String]) -> String {
    if subscripts.is_empty() {
        format!("^{}", name)
    } else {
        let subs: Vec<String> = subscripts.iter().map(|s| format!("\"{}\"", s)).collect();
        format!("^{}({})", name, subs.join(","))
    }
}

// ---------------------------------------------------------------------------
// ObjectScript code builders — output-parsing helpers
// ---------------------------------------------------------------------------

/// Parse the output from execute_via_generator for errors.
/// Lines starting with "ERROR: " indicate an ObjectScript catch or $ZERROR.
pub fn parse_execute_output(output: &str) -> Result<String, serde_json::Value> {
    let trimmed = output.trim();
    if let Some(msg) = trimmed.strip_prefix("ERROR: ") {
        return Err(serde_json::json!({
            "success": false,
            "error_code": "IRIS_EXECUTE_ERROR",
            "message": msg.trim()
        }));
    }
    Ok(trimmed.to_string())
}

// ---------------------------------------------------------------------------
// Clamp helpers
// ---------------------------------------------------------------------------

pub fn clamp_max_nodes(v: i64) -> i64 {
    v.clamp(1, 1000)
}

pub fn clamp_max_subscripts(v: i64) -> i64 {
    v.clamp(1, 500)
}

// ---------------------------------------------------------------------------
// ObjectScript generators
// ---------------------------------------------------------------------------

/// Build ObjectScript for a single-node `get`.
pub fn build_get_code(gref: &str) -> String {
    // $Data returns 0 if not set, 1 if set with no children, 10 children only, 11 both.
    format!(
        r#" Set gref = "{gref}"
 Set val = $Get(@gref)
 Set def = ($Data(@gref) > 0)
 If def {{
   Write "{{""success"":true,""defined"":true,""value"":""",val,"""}}",$C(10)
 }} Else {{
   Write "{{""success"":true,""defined"":false,""value"":null}}",$C(10)
 }}"#
    )
}

/// Build ObjectScript for a subtree `get`.
pub fn build_subtree_get_code(gref: &str, max_nodes: i64) -> String {
    // Uses $Query to traverse the subtree. $ZH gives fractional seconds since midnight.
    // Stops when $Query leaves the subtree (prefix check) or node/time cap hit.
    format!(
        r#" Set startTime = $ZH
 Set maxNodes = {max_nodes}
 Set grefBase = "{gref}"
 Set node = grefBase
 Set count = 0
 Set truncated = 0
 Set out = "["
 For {{
   Set node = $Query(@node)
   Quit:node=""
   Quit:$Extract(node,1,$Length(grefBase))'=grefBase
   If count >= maxNodes {{ Set truncated = 1  Quit }}
   If ($ZH - startTime) > 5 {{ Set truncated = 1  Quit }}
   Set val = @node
   If count > 0 {{ Set out = out_","  }}
   Set out = out_"{{""path"":"""_node_""",""value"":"""_val_"""}}"
   Set count = count + 1
 }}
 Set out = out_"]"
 Write "{{""success"":true,""truncated"":"_truncated_",""node_count"":"_count_",""nodes"":"_out_"}}",$C(10)"#
    )
}

/// Build ObjectScript for a `set` operation.
pub fn build_set_objectscript(gref: &str, value: &str) -> String {
    // Value is embedded as a literal string. Since subscripts are allowlisted,
    // the gref is safe. The value may contain any chars — we escape quotes only.
    let escaped_value = value.replace('"', "\"\"");
    format!(
        r#" Set gref = "{gref}"
 Set @gref = "{escaped_value}"
 Write "{{""success"":true}}",$C(10)"#
    )
}

/// Build ObjectScript for a `kill` operation.
pub fn build_kill_code(gref: &str) -> String {
    format!(
        r#" Set gref = "{gref}"
 Kill @gref
 Write "{{""success"":true}}",$C(10)"#
    )
}

/// Build ObjectScript for a `list` operation.
pub fn build_list_code(gref: &str, max_subscripts: i64) -> String {
    // $Order on the parent node returns first-level subscripts.
    // gref is the parent reference (e.g. `^MyApp("a")`).
    // We iterate $Order on the subscript level.
    format!(
        r#" Set maxSubs = {max_subscripts}
 Set gref = "{gref}"
 Set sub = ""
 Set count = 0
 Set truncated = 0
 Set out = "["
 For {{
   Set sub = $Order(@gref@(sub))
   Quit:sub=""
   If count >= maxSubs {{ Set truncated = 1  Quit }}
   If count > 0 {{ Set out = out_","  }}
   Set out = out_""""_sub_""""
   Set count = count + 1
 }}
 Set out = out_"]"
 Write "{{""success"":true,""truncated"":"_truncated_",""subscripts"":"_out_"}}",$C(10)"#
    )
}

// ---------------------------------------------------------------------------
// Handler params
// ---------------------------------------------------------------------------

use schemars::JsonSchema;
use serde::Deserialize;

#[derive(Debug, Clone, Deserialize, JsonSchema)]
pub struct IrisGlobalParams {
    /// Action: get, set, kill, list
    pub action: String,
    /// Global name (with or without leading ^)
    pub global_name: String,
    /// Subscripts (each must match ^[a-zA-Z0-9 _.:\-]+$)
    pub subscripts: Option<Vec<String>>,
    /// Value to set (required for action=set)
    pub value: Option<String>,
    /// IRIS namespace (defaults to connection default)
    pub namespace: Option<String>,
    /// get only: return all descendant nodes
    pub subtree: Option<bool>,
    /// get+subtree: max nodes returned (default 100, max 1000)
    pub max_nodes: Option<i64>,
    /// list: max subscripts returned (default 50, max 500)
    pub max_subscripts: Option<i64>,
    /// Bypass PHI name gate (per spec 051)
    #[serde(rename = "acknowledgePhi")]
    pub acknowledge_phi: Option<bool>,
}

// ---------------------------------------------------------------------------
// Main handler — called from tools/mod.rs
// ---------------------------------------------------------------------------

/// Handle an `iris_global` tool call.
/// Returns the JSON response value (not wrapped in CallToolResult — caller wraps).
pub async fn handle_iris_global(
    iris: &crate::iris::connection::IrisConnection,
    client: &reqwest::Client,
    params: &IrisGlobalParams,
    gate_result: Result<(), serde_json::Value>,
) -> serde_json::Value {
    // Gate result already evaluated by caller; propagate if blocked.
    if let Err(gate_err) = gate_result {
        return gate_err;
    }

    let subs = params.subscripts.clone().unwrap_or_default();
    if let Err(e) = validate_subscripts(&subs) {
        return e;
    }

    let name = normalize_global_name(&params.global_name);
    let gref = build_global_ref(&name, &subs);
    let ns = params
        .namespace
        .clone()
        .unwrap_or_else(|| iris.namespace.clone());

    match params.action.as_str() {
        "get" => {
            let subtree = params.subtree.unwrap_or(false);
            let code = if subtree {
                let max_nodes = clamp_max_nodes(params.max_nodes.unwrap_or(100));
                build_subtree_get_code(&gref, max_nodes)
            } else {
                build_get_code(&gref)
            };
            match iris.execute_via_generator(&code, &ns, client).await {
                Err(e) => {
                    let msg = e.to_string();
                    if msg.contains("HTTP 4")
                        || msg.contains("HTTP 5")
                        || msg.contains("connection")
                    {
                        err_json("IRIS_UNREACHABLE", &msg)
                    } else {
                        err_json("IRIS_EXECUTE_ERROR", &msg)
                    }
                }
                Ok(output) => match parse_execute_output(&output) {
                    Err(e) => e,
                    Ok(json_str) => serde_json::from_str(&json_str).unwrap_or_else(|_| {
                        err_json(
                            "IRIS_EXECUTE_ERROR",
                            &format!("unexpected output: {json_str}"),
                        )
                    }),
                },
            }
        }
        "set" => {
            let value = match &params.value {
                Some(v) => v.clone(),
                None => {
                    return err_json("INVALID_PARAMS", "action=set requires a 'value' parameter")
                }
            };
            let code = build_set_objectscript(&gref, &value);
            match iris.execute_via_generator(&code, &ns, client).await {
                Err(e) => err_json("IRIS_UNREACHABLE", &e.to_string()),
                Ok(output) => match parse_execute_output(&output) {
                    Err(e) => e,
                    Ok(json_str) => serde_json::from_str(&json_str).unwrap_or_else(|_| {
                        err_json(
                            "IRIS_EXECUTE_ERROR",
                            &format!("unexpected output: {json_str}"),
                        )
                    }),
                },
            }
        }
        "kill" => {
            let code = build_kill_code(&gref);
            match iris.execute_via_generator(&code, &ns, client).await {
                Err(e) => err_json("IRIS_UNREACHABLE", &e.to_string()),
                Ok(output) => match parse_execute_output(&output) {
                    Err(e) => e,
                    Ok(json_str) => serde_json::from_str(&json_str).unwrap_or_else(|_| {
                        err_json(
                            "IRIS_EXECUTE_ERROR",
                            &format!("unexpected output: {json_str}"),
                        )
                    }),
                },
            }
        }
        "list" => {
            let max_subs = clamp_max_subscripts(params.max_subscripts.unwrap_or(50));
            let code = build_list_code(&gref, max_subs);
            match iris.execute_via_generator(&code, &ns, client).await {
                Err(e) => err_json("IRIS_UNREACHABLE", &e.to_string()),
                Ok(output) => match parse_execute_output(&output) {
                    Err(e) => e,
                    Ok(json_str) => serde_json::from_str(&json_str).unwrap_or_else(|_| {
                        err_json(
                            "IRIS_EXECUTE_ERROR",
                            &format!("unexpected output: {json_str}"),
                        )
                    }),
                },
            }
        }
        other => err_json(
            "INVALID_ACTION",
            &format!("unknown action: {other} (expected: get, set, kill, list)"),
        ),
    }
}
