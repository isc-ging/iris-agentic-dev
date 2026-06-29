// Coverage gap tests: exercise uncovered paths in workspace_config, server_manager,
// audit_log, and tools helpers identified after 051-phi-policy-env-gates.
//
// Each section targets specific uncovered lines confirmed via cargo-llvm-cov LCOV output.

// ── ToolCategory::FromStr ─────────────────────────────────────────────────────

mod tool_category {
    use iris_agentic_dev_core::iris::workspace_config::ToolCategory;
    use std::str::FromStr;

    #[test]
    fn from_str_all_variants() {
        let cases = [
            ("compile", ToolCategory::Compile),
            ("execute", ToolCategory::Execute),
            ("query", ToolCategory::Query),
            ("search", ToolCategory::Search),
            ("docs", ToolCategory::Docs),
            ("source_control", ToolCategory::SourceControl),
            ("debug", ToolCategory::Debug),
            ("admin", ToolCategory::Admin),
            ("skill", ToolCategory::Skill),
            ("kb", ToolCategory::Kb),
        ];
        for (s, expected) in &cases {
            let got =
                ToolCategory::from_str(s).unwrap_or_else(|e| panic!("from_str({s}) failed: {e}"));
            assert_eq!(got, *expected, "from_str({s}) mismatch");
        }
    }

    #[test]
    fn from_str_unknown_returns_err() {
        let e = ToolCategory::from_str("nonexistent").unwrap_err();
        assert!(
            e.contains("nonexistent"),
            "error must name the bad input: {e}"
        );
    }

    #[test]
    fn as_str_roundtrips_all_variants() {
        let variants = [
            ToolCategory::Compile,
            ToolCategory::Execute,
            ToolCategory::Query,
            ToolCategory::Search,
            ToolCategory::Docs,
            ToolCategory::SourceControl,
            ToolCategory::Debug,
            ToolCategory::Admin,
            ToolCategory::Skill,
            ToolCategory::Kb,
        ];
        for v in &variants {
            let s = v.as_str();
            let back = ToolCategory::from_str(s)
                .unwrap_or_else(|e| panic!("roundtrip failed for {s}: {e}"));
            assert_eq!(back, *v, "roundtrip failed for {s}");
        }
    }
}

// ── DataPolicy deserialization ────────────────────────────────────────────────

mod data_policy {
    use iris_agentic_dev_core::iris::workspace_config::DataPolicy;

    #[test]
    fn deserialize_block() {
        let v: DataPolicy = toml::from_str("dataPolicy = \"block\"")
            .map(|t: toml::Value| t["dataPolicy"].clone())
            .and_then(|v| v.try_into())
            .unwrap();
        assert_eq!(v, DataPolicy::Block);
    }

    #[test]
    fn deserialize_allow() {
        let toml_str = "[policy.test]\ndataPolicy = \"allow\"\n";
        let parsed: toml::Value = toml::from_str(toml_str).unwrap();
        let dp_str = parsed["policy"]["test"]["dataPolicy"].as_str().unwrap();
        assert_eq!(dp_str, "allow");
    }

    #[test]
    fn deserialize_redact() {
        let toml_str = "[policy.test]\ndataPolicy = \"redact\"\n";
        let parsed: toml::Value = toml::from_str(toml_str).unwrap();
        let dp_str = parsed["policy"]["test"]["dataPolicy"].as_str().unwrap();
        assert_eq!(dp_str, "redact");
    }

    #[test]
    fn load_fleet_config_parses_data_policy_block() {
        use iris_agentic_dev_core::iris::workspace_config::{
            load_fleet_config_from_str, DataPolicy,
        };
        let toml = "[policy.prod]\ndataPolicy = \"block\"\n";
        let cfg = load_fleet_config_from_str(toml).unwrap();
        let pol = cfg.policies.get("prod").unwrap();
        assert_eq!(pol.data_policy, Some(DataPolicy::Block));
    }

    #[test]
    fn load_fleet_config_parses_data_policy_allow() {
        use iris_agentic_dev_core::iris::workspace_config::{
            load_fleet_config_from_str, DataPolicy,
        };
        let toml = "[policy.staging]\ndataPolicy = \"allow\"\n";
        let cfg = load_fleet_config_from_str(toml).unwrap();
        let pol = cfg.policies.get("staging").unwrap();
        assert_eq!(pol.data_policy, Some(DataPolicy::Allow));
    }

    #[test]
    fn load_fleet_config_parses_data_policy_redact() {
        use iris_agentic_dev_core::iris::workspace_config::{
            load_fleet_config_from_str, DataPolicy,
        };
        let toml = "[policy.dev]\ndataPolicy = \"redact\"\n";
        let cfg = load_fleet_config_from_str(toml).unwrap();
        let pol = cfg.policies.get("dev").unwrap();
        assert_eq!(pol.data_policy, Some(DataPolicy::Redact));
    }
}

// ── FleetConfig / load_fleet_config_from_str ─────────────────────────────────

mod fleet_config {
    use iris_agentic_dev_core::iris::workspace_config::{
        load_fleet_config_from_str, McpTemplate, ToolCategory,
    };

    #[test]
    fn parses_mcp_template_live() {
        let toml = "[policy.prod]\nmcpTemplate = \"live\"\n";
        let cfg = load_fleet_config_from_str(toml).unwrap();
        let pol = cfg.policies.get("prod").unwrap();
        assert_eq!(pol.mcp_template, Some(McpTemplate::Live));
    }

    #[test]
    fn parses_mcp_template_test() {
        let toml = "[policy.staging]\nmcpTemplate = \"test\"\n";
        let cfg = load_fleet_config_from_str(toml).unwrap();
        let pol = cfg.policies.get("staging").unwrap();
        assert_eq!(pol.mcp_template, Some(McpTemplate::Test));
    }

    #[test]
    fn parses_mcp_template_dev() {
        let toml = "[policy.local]\nmcpTemplate = \"dev\"\n";
        let cfg = load_fleet_config_from_str(toml).unwrap();
        let pol = cfg.policies.get("local").unwrap();
        assert_eq!(pol.mcp_template, Some(McpTemplate::Dev));
    }

    #[test]
    fn parses_global_blocklist() {
        let toml = "[policy.prod]\nglobalBlocklist = [\"^Secret*\", \"^Internal\"]\n";
        let cfg = load_fleet_config_from_str(toml).unwrap();
        let pol = cfg.policies.get("prod").unwrap();
        assert_eq!(pol.global_blocklist.len(), 2);
        assert!(pol.global_blocklist.contains(&"^Secret*".to_string()));
        assert!(pol.global_blocklist.contains(&"^Internal".to_string()));
    }

    #[test]
    fn parses_data_policy_kill_allowlist() {
        let toml = "[policy.prod]\ndataPolicyKillAllowlist = [\"^TempWork*\"]\n";
        let cfg = load_fleet_config_from_str(toml).unwrap();
        let pol = cfg.policies.get("prod").unwrap();
        assert_eq!(pol.data_policy_kill_allowlist, vec!["^TempWork*"]);
    }

    #[test]
    fn parses_allow_categories() {
        let toml = "[policy.readonly]\nallow = [\"query\", \"search\", \"docs\"]\n";
        let cfg = load_fleet_config_from_str(toml).unwrap();
        let pol = cfg.policies.get("readonly").unwrap();
        let allow = pol.allow.as_ref().unwrap();
        assert!(allow.contains(&ToolCategory::Query));
        assert!(allow.contains(&ToolCategory::Search));
        assert!(allow.contains(&ToolCategory::Docs));
    }

    #[test]
    fn parses_multiple_policy_blocks() {
        let toml = r#"
[policy.prod]
mcpTemplate = "live"

[policy.staging]
mcpTemplate = "test"

[policy.dev]
mcpTemplate = "dev"
"#;
        let cfg = load_fleet_config_from_str(toml).unwrap();
        assert_eq!(cfg.policies.len(), 3);
        assert_eq!(
            cfg.policies.get("prod").unwrap().mcp_template,
            Some(McpTemplate::Live)
        );
        assert_eq!(
            cfg.policies.get("staging").unwrap().mcp_template,
            Some(McpTemplate::Test)
        );
        assert_eq!(
            cfg.policies.get("dev").unwrap().mcp_template,
            Some(McpTemplate::Dev)
        );
    }

    #[test]
    fn policy_server_name_populated_from_key() {
        let toml = "[policy.my-server]\nmcpTemplate = \"live\"\n";
        let cfg = load_fleet_config_from_str(toml).unwrap();
        let pol = cfg.policies.get("my-server").unwrap();
        assert_eq!(pol.server_name, "my-server");
    }

    #[test]
    fn empty_toml_yields_empty_policies() {
        let cfg = load_fleet_config_from_str("").unwrap();
        assert!(cfg.policies.is_empty());
    }
}

// ── load_workspace_config error/legacy paths ──────────────────────────────────

mod workspace_config_loading {
    use iris_agentic_dev_core::iris::workspace_config::{load_workspace_config, workspace_root};
    use std::io::Write;

    fn write_file(dir: &tempfile::TempDir, name: &str, contents: &str) {
        let path = dir.path().join(name);
        let mut f = std::fs::File::create(&path).unwrap();
        f.write_all(contents.as_bytes()).unwrap();
    }

    #[test]
    fn load_workspace_config_parse_error_returns_none() {
        let dir = tempfile::TempDir::new().unwrap();
        write_file(&dir, ".iris-agentic-dev.toml", "not = valid = toml = !!!");
        let result = load_workspace_config(Some(dir.path().to_str().unwrap()));
        assert!(result.is_none(), "parse error must return None");
    }

    #[test]
    fn load_workspace_config_missing_file_returns_none() {
        let result = load_workspace_config(Some("/definitely/not/a/real/path/ever"));
        assert!(result.is_none());
    }

    #[test]
    fn load_fleet_config_parse_error_returns_none() {
        use iris_agentic_dev_core::iris::workspace_config::load_fleet_config;
        let dir = tempfile::TempDir::new().unwrap();
        write_file(&dir, ".iris-agentic-dev.toml", "bad = bad = bad");
        let result = load_fleet_config(Some(dir.path().to_str().unwrap()));
        assert!(
            result.is_none(),
            "fleet config parse error must return None"
        );
    }

    #[test]
    fn workspace_root_empty_workspace_var_falls_through() {
        // OBJECTSCRIPT_WORKSPACE = "" should not use env var, fall to path arg
        let _guard: std::sync::MutexGuard<'_, ()> = super::WORKSPACE_LOCK.lock().unwrap_or_else(
            |e: std::sync::PoisonError<std::sync::MutexGuard<'_, ()>>| e.into_inner(),
        );
        std::env::set_var("OBJECTSCRIPT_WORKSPACE", "");
        let root = workspace_root(Some("/explicit/path"));
        std::env::remove_var("OBJECTSCRIPT_WORKSPACE");
        assert_eq!(root.to_str().unwrap(), "/explicit/path");
    }

    #[test]
    fn workspace_root_dot_path_falls_through_to_walkup() {
        let _guard: std::sync::MutexGuard<'_, ()> = super::WORKSPACE_LOCK.lock().unwrap_or_else(
            |e: std::sync::PoisonError<std::sync::MutexGuard<'_, ()>>| e.into_inner(),
        );
        std::env::remove_var("OBJECTSCRIPT_WORKSPACE");
        // "." is treated as empty — should trigger walk-up, not return "."
        let root = workspace_root(Some("."));
        // Result is not literally "." — it walked up (may be cwd or a parent)
        assert_ne!(
            root.to_str().unwrap(),
            ".",
            "workspace_root(\".\") must not return literal \".\""
        );
    }

    #[test]
    fn workspace_root_empty_path_falls_through_to_walkup() {
        let _guard: std::sync::MutexGuard<'_, ()> = super::WORKSPACE_LOCK.lock().unwrap_or_else(
            |e: std::sync::PoisonError<std::sync::MutexGuard<'_, ()>>| e.into_inner(),
        );
        std::env::remove_var("OBJECTSCRIPT_WORKSPACE");
        let root = workspace_root(Some(""));
        // Walk-up result: path returned is a real directory, not empty
        assert!(!root.to_str().unwrap().is_empty());
    }

    #[test]
    fn load_workspace_config_legacy_iris_dev_toml() {
        let dir = tempfile::TempDir::new().unwrap();
        write_file(&dir, ".iris-dev.toml", "container = \"legacy-iris\"\n");
        // No .iris-agentic-dev.toml — should fall back to legacy
        let cfg = load_workspace_config(Some(dir.path().to_str().unwrap()));
        assert!(cfg.is_some(), "must load from legacy .iris-dev.toml");
        let cfg = cfg.unwrap();
        assert_eq!(cfg.container.as_deref(), Some("legacy-iris"));
    }

    #[test]
    fn load_workspace_config_prefers_new_over_legacy() {
        let dir = tempfile::TempDir::new().unwrap();
        write_file(&dir, ".iris-agentic-dev.toml", "container = \"new-iris\"\n");
        write_file(&dir, ".iris-dev.toml", "container = \"legacy-iris\"\n");
        let cfg = load_workspace_config(Some(dir.path().to_str().unwrap())).unwrap();
        assert_eq!(cfg.container.as_deref(), Some("new-iris"));
    }

    #[test]
    fn load_fleet_config_with_policy_block() {
        use iris_agentic_dev_core::iris::workspace_config::{load_fleet_config, McpTemplate};
        let dir = tempfile::TempDir::new().unwrap();
        write_file(
            &dir,
            ".iris-agentic-dev.toml",
            "[policy.prod]\nmcpTemplate = \"live\"\n",
        );
        let cfg = load_fleet_config(Some(dir.path().to_str().unwrap())).unwrap();
        let pol = cfg.policies.get("prod").unwrap();
        assert_eq!(pol.mcp_template, Some(McpTemplate::Live));
    }

    #[test]
    fn load_fleet_config_legacy_iris_dev_toml() {
        use iris_agentic_dev_core::iris::workspace_config::load_fleet_config;
        let dir = tempfile::TempDir::new().unwrap();
        write_file(&dir, ".iris-dev.toml", "container = \"legacy-fleet\"\n");
        let cfg = load_fleet_config(Some(dir.path().to_str().unwrap()));
        assert!(
            cfg.is_some(),
            "fleet config must load from legacy .iris-dev.toml"
        );
        assert_eq!(
            cfg.unwrap().workspace.container.as_deref(),
            Some("legacy-fleet")
        );
    }
}

static WORKSPACE_LOCK: std::sync::Mutex<()> = std::sync::Mutex::new(());

// ── server_manager: select_server multi-profile + policy template variants ────

mod server_manager_coverage {
    use iris_agentic_dev_core::iris::server_manager::{
        build_server_manager_config_json, select_server, ServerManagerCredentialEntry,
        ServerManagerProfile, SmCredentialError,
    };
    use iris_agentic_dev_core::iris::workspace_config::{
        ConnectionPolicy, DataPolicy, McpTemplate, ToolCategory,
    };

    fn profile(name: &str) -> ServerManagerProfile {
        ServerManagerProfile {
            name: name.to_string(),
            host: "localhost".to_string(),
            port: 52773,
            scheme: "http".to_string(),
            path_prefix: None,
            username: "_SYSTEM".to_string(),
            password_deprecated: None,
        }
    }

    // ── select_server ─────────────────────────────────────────────────────────

    #[test]
    fn select_server_zero_profiles_returns_ambiguous() {
        let r = select_server(&[]);
        assert!(
            matches!(r, Err(SmCredentialError::Ambiguous { available }) if available.is_empty())
        );
    }

    #[test]
    fn select_server_single_auto_selects() {
        let profiles = vec![profile("dev")];
        let r = select_server(&profiles).unwrap();
        assert_eq!(r.name, "dev");
    }

    #[test]
    fn select_server_multi_no_env_var_returns_ambiguous() {
        std::env::remove_var("IRIS_SERVER_NAME");
        let profiles = vec![profile("dev"), profile("staging"), profile("prod")];
        let r = select_server(&profiles);
        assert!(matches!(r, Err(SmCredentialError::Ambiguous { .. })));
    }

    #[test]
    fn select_server_multi_with_env_var_selects_match() {
        std::env::set_var("IRIS_SERVER_NAME", "staging");
        let profiles = vec![profile("dev"), profile("staging"), profile("prod")];
        let r = select_server(&profiles).unwrap();
        assert_eq!(r.name, "staging");
        std::env::remove_var("IRIS_SERVER_NAME");
    }

    #[test]
    fn select_server_multi_with_env_var_no_match_returns_ambiguous() {
        std::env::set_var("IRIS_SERVER_NAME", "nonexistent");
        let profiles = vec![profile("dev"), profile("prod")];
        let r = select_server(&profiles);
        assert!(matches!(r, Err(SmCredentialError::Ambiguous { .. })));
        std::env::remove_var("IRIS_SERVER_NAME");
    }

    #[test]
    fn select_server_case_insensitive_match() {
        std::env::set_var("IRIS_SERVER_NAME", "STAGING");
        let profiles = vec![profile("dev"), profile("staging")];
        let r = select_server(&profiles).unwrap();
        assert_eq!(r.name, "staging");
        std::env::remove_var("IRIS_SERVER_NAME");
    }

    // ── build_server_manager_config_json: all policy template variants ────────

    #[test]
    fn policy_mcp_template_dev_serialized() {
        let profiles = vec![profile("local")];
        let cred_entries = vec![ServerManagerCredentialEntry {
            server_name: "local".to_string(),
            status: "resolved".to_string(),
            policy: Some(ConnectionPolicy {
                server_name: "local".to_string(),
                allow: None,
                mcp_template: Some(McpTemplate::Dev),
                data_policy: None,
                global_blocklist: vec![],
                data_policy_kill_allowlist: vec![],
            }),
        }];
        let json = build_server_manager_config_json(&profiles, Some("local"), &cred_entries);
        let servers = json["servers"].as_array().unwrap();
        assert_eq!(servers[0]["policy"]["mcp_template"], "dev");
    }

    #[test]
    fn policy_mcp_template_test_serialized() {
        let profiles = vec![profile("staging")];
        let cred_entries = vec![ServerManagerCredentialEntry {
            server_name: "staging".to_string(),
            status: "resolved".to_string(),
            policy: Some(ConnectionPolicy {
                server_name: "staging".to_string(),
                allow: None,
                mcp_template: Some(McpTemplate::Test),
                data_policy: None,
                global_blocklist: vec![],
                data_policy_kill_allowlist: vec![],
            }),
        }];
        let json = build_server_manager_config_json(&profiles, Some("staging"), &cred_entries);
        let servers = json["servers"].as_array().unwrap();
        assert_eq!(servers[0]["policy"]["mcp_template"], "test");
    }

    #[test]
    fn policy_mcp_template_live_serialized() {
        let profiles = vec![profile("prod")];
        let cred_entries = vec![ServerManagerCredentialEntry {
            server_name: "prod".to_string(),
            status: "resolved".to_string(),
            policy: Some(ConnectionPolicy {
                server_name: "prod".to_string(),
                allow: None,
                mcp_template: Some(McpTemplate::Live),
                data_policy: None,
                global_blocklist: vec![],
                data_policy_kill_allowlist: vec![],
            }),
        }];
        let json = build_server_manager_config_json(&profiles, Some("prod"), &cred_entries);
        let servers = json["servers"].as_array().unwrap();
        assert_eq!(servers[0]["policy"]["mcp_template"], "live");
    }

    #[test]
    fn policy_data_policy_block_serialized() {
        let profiles = vec![profile("prod")];
        let cred_entries = vec![ServerManagerCredentialEntry {
            server_name: "prod".to_string(),
            status: "resolved".to_string(),
            policy: Some(ConnectionPolicy {
                server_name: "prod".to_string(),
                allow: None,
                mcp_template: None,
                data_policy: Some(DataPolicy::Block),
                global_blocklist: vec![],
                data_policy_kill_allowlist: vec![],
            }),
        }];
        let json = build_server_manager_config_json(&profiles, Some("prod"), &cred_entries);
        let servers = json["servers"].as_array().unwrap();
        assert_eq!(servers[0]["policy"]["data_policy"], "block");
    }

    #[test]
    fn policy_data_policy_allow_serialized() {
        let profiles = vec![profile("dev")];
        let cred_entries = vec![ServerManagerCredentialEntry {
            server_name: "dev".to_string(),
            status: "resolved".to_string(),
            policy: Some(ConnectionPolicy {
                server_name: "dev".to_string(),
                allow: None,
                mcp_template: None,
                data_policy: Some(DataPolicy::Allow),
                global_blocklist: vec![],
                data_policy_kill_allowlist: vec![],
            }),
        }];
        let json = build_server_manager_config_json(&profiles, Some("dev"), &cred_entries);
        let servers = json["servers"].as_array().unwrap();
        assert_eq!(servers[0]["policy"]["data_policy"], "allow");
    }

    #[test]
    fn policy_data_policy_redact_serialized() {
        let profiles = vec![profile("staging")];
        let cred_entries = vec![ServerManagerCredentialEntry {
            server_name: "staging".to_string(),
            status: "resolved".to_string(),
            policy: Some(ConnectionPolicy {
                server_name: "staging".to_string(),
                allow: None,
                mcp_template: None,
                data_policy: Some(DataPolicy::Redact),
                global_blocklist: vec![],
                data_policy_kill_allowlist: vec![],
            }),
        }];
        let json = build_server_manager_config_json(&profiles, Some("staging"), &cred_entries);
        let servers = json["servers"].as_array().unwrap();
        assert_eq!(servers[0]["policy"]["data_policy"], "redact");
    }

    #[test]
    fn policy_all_fields_serialized_together() {
        let profiles = vec![profile("prod")];
        let cred_entries = vec![ServerManagerCredentialEntry {
            server_name: "prod".to_string(),
            status: "resolved".to_string(),
            policy: Some(ConnectionPolicy {
                server_name: "prod".to_string(),
                allow: Some(vec![ToolCategory::Query, ToolCategory::Docs]),
                mcp_template: Some(McpTemplate::Live),
                data_policy: Some(DataPolicy::Block),
                global_blocklist: vec![],
                data_policy_kill_allowlist: vec![],
            }),
        }];
        let json = build_server_manager_config_json(&profiles, Some("prod"), &cred_entries);
        let servers = json["servers"].as_array().unwrap();
        let policy = &servers[0]["policy"];
        assert_eq!(policy["mcp_template"], "live");
        assert_eq!(policy["data_policy"], "block");
        let allow = policy["allow"].as_array().unwrap();
        let cats: Vec<&str> = allow.iter().map(|v| v.as_str().unwrap()).collect();
        assert!(cats.contains(&"query"));
        assert!(cats.contains(&"docs"));
    }

    #[test]
    fn credential_status_not_configured_when_no_cred_entry() {
        let profiles = vec![profile("dev")];
        let json = build_server_manager_config_json(&profiles, None, &[]);
        let servers = json["servers"].as_array().unwrap();
        assert_eq!(servers[0]["credential_status"], "not_configured");
        assert_eq!(servers[0]["active"], false);
    }

    #[test]
    fn active_flag_set_for_active_server() {
        let profiles = vec![profile("dev"), profile("prod")];
        let json = build_server_manager_config_json(&profiles, Some("prod"), &[]);
        let servers = json["servers"].as_array().unwrap();
        let prod = servers.iter().find(|s| s["name"] == "prod").unwrap();
        let dev = servers.iter().find(|s| s["name"] == "dev").unwrap();
        assert_eq!(prod["active"], true);
        assert_eq!(dev["active"], false);
    }

    #[test]
    fn credential_status_consts_correct() {
        use iris_agentic_dev_core::iris::server_manager::CredentialStatus;
        assert_eq!(CredentialStatus::RESOLVED, "resolved");
        assert_eq!(CredentialStatus::NOT_CONFIGURED, "not_configured");
        assert_eq!(CredentialStatus::ERROR, "error");
    }

    // ── parse_sm_settings: flat dotted key format ─────────────────────────────

    #[test]
    fn parse_flat_dotted_key_format() {
        use iris_agentic_dev_core::iris::server_manager::parse_sm_settings;
        use std::io::Write;
        let dir = tempfile::TempDir::new().unwrap();
        let path = dir.path().join("settings.json");
        let json = r#"{
            "intersystems.servers": {
                "flat-server": {
                    "webServer": {"host": "flat-host", "port": 52773},
                    "username": "_SYSTEM"
                }
            }
        }"#;
        let mut f = std::fs::File::create(&path).unwrap();
        f.write_all(json.as_bytes()).unwrap();
        let profiles = parse_sm_settings(&path);
        assert_eq!(profiles.len(), 1, "flat dotted key format must be parsed");
        assert_eq!(profiles[0].name, "flat-server");
        assert_eq!(profiles[0].host, "flat-host");
    }

    #[test]
    fn parse_server_entry_with_missing_required_field_skipped() {
        use iris_agentic_dev_core::iris::server_manager::parse_sm_settings;
        use std::io::Write;
        let dir = tempfile::TempDir::new().unwrap();
        let path = dir.path().join("settings.json");
        // webServer.host is Some but empty — should skip; host-less server also skipped
        let json = r#"{
            "intersystems": { "servers": {
                "bad1": {"username": "_SYSTEM"},
                "good1": {"webServer": {"host": "good-host", "port": 52773}}
            }}
        }"#;
        let mut f = std::fs::File::create(&path).unwrap();
        f.write_all(json.as_bytes()).unwrap();
        let profiles = parse_sm_settings(&path);
        // bad1 has no webServer.host → skipped; good1 should parse
        assert_eq!(profiles.len(), 1);
        assert_eq!(profiles[0].name, "good1");
    }

    #[test]
    fn parse_invalid_json_returns_empty() {
        use iris_agentic_dev_core::iris::server_manager::parse_sm_settings;
        use std::io::Write;
        let dir = tempfile::TempDir::new().unwrap();
        let path = dir.path().join("settings.json");
        let mut f = std::fs::File::create(&path).unwrap();
        f.write_all(b"not json at all!!!").unwrap();
        let profiles = parse_sm_settings(&path);
        assert!(
            profiles.is_empty(),
            "invalid JSON must return empty profiles"
        );
    }

    // ── tool_to_category_pub: remaining categories ────────────────────────────

    #[test]
    fn tool_to_category_all_tool_names() {
        use iris_agentic_dev_core::iris::server_manager::tool_to_category_pub;
        use iris_agentic_dev_core::iris::workspace_config::ToolCategory;
        let cases: &[(&str, ToolCategory)] = &[
            ("iris_compile", ToolCategory::Compile),
            ("iris_execute", ToolCategory::Execute),
            ("iris_query", ToolCategory::Query),
            ("iris_search", ToolCategory::Search),
            ("iris_symbols", ToolCategory::Search),
            ("iris_symbols_local", ToolCategory::Search),
            ("docs_introspect", ToolCategory::Docs),
            ("iris_doc", ToolCategory::Docs),
            ("iris_source_control", ToolCategory::SourceControl),
            ("debug_capture_packet", ToolCategory::Debug),
            ("debug_map_int_to_cls", ToolCategory::Debug),
            ("debug_get_error_logs", ToolCategory::Debug),
            ("debug_source_map", ToolCategory::Debug),
            ("iris_debug", ToolCategory::Debug),
            ("iris_admin", ToolCategory::Admin),
            ("iris_info", ToolCategory::Admin),
            ("iris_containers", ToolCategory::Admin),
            ("skill_list", ToolCategory::Skill),
            ("skill_describe", ToolCategory::Skill),
            ("skill_search", ToolCategory::Skill),
            ("skill_forget", ToolCategory::Skill),
            ("skill_propose", ToolCategory::Skill),
            ("skill_optimize", ToolCategory::Skill),
            ("skill_share", ToolCategory::Skill),
            ("agent_history", ToolCategory::Skill),
            ("agent_stats", ToolCategory::Skill),
            ("kb_recall", ToolCategory::Kb),
            ("kb_index", ToolCategory::Kb),
        ];
        for (tool, expected) in cases {
            let got = tool_to_category_pub(tool)
                .unwrap_or_else(|| panic!("tool_to_category_pub({tool}) returned None"));
            assert_eq!(got, *expected, "wrong category for {tool}");
        }
    }

    #[test]
    fn tool_to_category_action_suffix_stripped() {
        use iris_agentic_dev_core::iris::server_manager::tool_to_category_pub;
        use iris_agentic_dev_core::iris::workspace_config::ToolCategory;
        let cat = tool_to_category_pub("iris_source_control:commit").unwrap();
        assert_eq!(cat, ToolCategory::SourceControl);
    }

    #[test]
    fn tool_to_category_unknown_returns_none() {
        use iris_agentic_dev_core::iris::server_manager::tool_to_category_pub;
        assert!(tool_to_category_pub("unknown_future_tool_xyz").is_none());
    }
}

// ── audit_log: AuditLogEntry struct construction + scrub_params non-object ────

mod audit_log_coverage {
    use iris_agentic_dev_core::iris::audit_log::{scrub_params, AuditLogEntry};

    #[test]
    fn scrub_params_non_object_passthrough() {
        // Non-object input (array, string, null) must pass through unchanged
        let arr = serde_json::json!([1, 2, 3]);
        let out = scrub_params(arr.clone());
        assert_eq!(out, arr, "non-object must be returned unchanged");

        let s = serde_json::json!("just a string");
        let out = scrub_params(s.clone());
        assert_eq!(out, s);

        let n = serde_json::Value::Null;
        let out = scrub_params(n.clone());
        assert_eq!(out, n);
    }

    #[test]
    fn audit_entry_clone_roundtrip() {
        // Exercises struct field access (Clone + all fields)
        let entry = AuditLogEntry {
            ts: "2026-06-29T00:00:00Z".to_string(),
            tool: "iris_compile".to_string(),
            connection: "prod".to_string(),
            namespace: "USER".to_string(),
            status: "blocked".to_string(),
            gate: Some("policy".to_string()),
            allowed_categories: Some(vec!["query".to_string()]),
            params: serde_json::json!({"target": "Foo.cls"}),
        };
        let json = serde_json::to_string(&entry).unwrap();
        let parsed: serde_json::Value = serde_json::from_str(&json).unwrap();
        assert_eq!(parsed["tool"], "iris_compile");
        assert_eq!(parsed["gate"], "policy");
        assert!(parsed["allowed_categories"].is_array());
    }

    #[test]
    fn audit_entry_no_gate_omitted_from_json() {
        let entry = AuditLogEntry {
            ts: "2026-06-29T00:00:00Z".to_string(),
            tool: "iris_query".to_string(),
            connection: "dev".to_string(),
            namespace: "USER".to_string(),
            status: "allowed".to_string(),
            gate: None,
            allowed_categories: None,
            params: serde_json::json!({}),
        };
        let json = serde_json::to_string(&entry).unwrap();
        // skip_serializing_if = Option::is_none — must NOT appear in JSON
        assert!(
            !json.contains("gate"),
            "gate must be absent when None: {json}"
        );
        assert!(
            !json.contains("allowed_categories"),
            "allowed_categories must be absent when None: {json}"
        );
    }
}

// ── build_workspace_config_json: operate mode ────────────────────────────────

mod workspace_config_json {
    use iris_agentic_dev_core::iris::workspace_config::build_workspace_config_json;
    use std::io::Write;

    fn write_toml(dir: &tempfile::TempDir, contents: &str) {
        let path = dir.path().join(".iris-agentic-dev.toml");
        let mut f = std::fs::File::create(&path).unwrap();
        f.write_all(contents.as_bytes()).unwrap();
    }

    #[test]
    fn develop_mode_returns_develop_shape() {
        let dir = tempfile::TempDir::new().unwrap();
        write_toml(&dir, "container = \"dev-iris\"\nnamespace = \"USER\"\n");
        let running = vec![];
        let json = build_workspace_config_json(Some(dir.path().to_str().unwrap()), &running);
        assert_eq!(json["found"], true);
        assert_eq!(json["container"], "dev-iris");
        assert_eq!(json["namespace"], "USER");
        assert_eq!(json["running"], false);
    }

    #[test]
    fn develop_mode_container_running_true() {
        let dir = tempfile::TempDir::new().unwrap();
        write_toml(&dir, "container = \"my-iris\"\n");
        let running = vec![serde_json::json!({"name": "my-iris"})];
        let json = build_workspace_config_json(Some(dir.path().to_str().unwrap()), &running);
        assert_eq!(json["running"], true);
    }

    #[test]
    fn no_config_file_returns_null() {
        let json = build_workspace_config_json(Some("/no/config/here"), &[]);
        assert!(json.is_null(), "missing config must return JSON null");
    }

    #[test]
    fn operate_mode_returns_instances_map() {
        let dir = tempfile::TempDir::new().unwrap();
        write_toml(
            &dir,
            r#"mode = "operate"
[instance.local]
container = "local-iris"
namespace = "USER"
role = "workspace"

[instance.subject]
host = "subject.example.com"
web_port = 52773
namespace = "MYNS"
role = "subject"
"#,
        );
        let running = vec![];
        let json = build_workspace_config_json(Some(dir.path().to_str().unwrap()), &running);
        assert_eq!(json["found"], true);
        assert_eq!(json["mode"], "operate");
        assert!(json["instances"].is_object());
        let instances = json["instances"].as_object().unwrap();
        assert!(instances.contains_key("local"));
        assert!(instances.contains_key("subject"));
        assert_eq!(instances["local"]["role"], "workspace");
        assert_eq!(instances["subject"]["role"], "subject");
    }

    #[test]
    fn operate_mode_instance_running_when_container_matches() {
        let dir = tempfile::TempDir::new().unwrap();
        write_toml(
            &dir,
            r#"mode = "operate"
[instance.local]
container = "running-iris"
namespace = "USER"
role = "workspace"
"#,
        );
        let running = vec![serde_json::json!({"name": "running-iris"})];
        let json = build_workspace_config_json(Some(dir.path().to_str().unwrap()), &running);
        let instances = json["instances"].as_object().unwrap();
        assert_eq!(instances["local"]["running"], true);
    }
}

// ── generate_toml_content / generate_operate_toml_content ─────────────────────

mod generate_toml {
    use iris_agentic_dev_core::iris::workspace_config::{
        generate_operate_toml_content, generate_toml_content,
    };

    #[test]
    fn generate_toml_content_contains_namespace() {
        let out = generate_toml_content("test-iris", "TESTNS");
        assert!(
            out.contains("TESTNS"),
            "generated TOML must contain namespace"
        );
        assert!(
            out.contains("test-iris"),
            "generated TOML must contain container name"
        );
    }

    #[test]
    fn generate_operate_toml_content_contains_mode_operate() {
        let out = generate_operate_toml_content("local-iris", "USER");
        assert!(
            out.contains("mode = \"operate\""),
            "must include operate mode"
        );
        assert!(out.contains("local-iris"), "must include container name");
        assert!(out.contains("USER"), "must include namespace");
    }
}
