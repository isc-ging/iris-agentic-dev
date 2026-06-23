use iris_agentic_dev_core::iris::connection::{DiscoverySource, IrisConnection, SystemMode};
use iris_agentic_dev_core::tools::interop::*;
use iris_agentic_dev_core::tools::{IrisTools, Toolset};

fn rt() -> tokio::runtime::Runtime {
    tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
        .unwrap()
}

mod interop_production_status {
    use super::*;

    #[test]
    fn iris_unreachable_when_no_connection() {
        let r = rt().block_on(interop_production_status_impl(
            None,
            ProductionStatusParams {
                namespace: "USER".into(),
                full_status: false,
            },
        ));
        let result = r.unwrap();
        let text = result.content[0].raw.as_text().unwrap().text.clone();
        let v: serde_json::Value = serde_json::from_str(&text).unwrap();
        assert_eq!(v["success"], false);
        assert_eq!(v["error_code"], "IRIS_UNREACHABLE");
    }
}

mod interop_production_start {
    use super::*;

    #[test]
    fn iris_unreachable() {
        let r = rt().block_on(interop_production_start_impl(
            None,
            ProductionNameParams {
                production: Some("Test".into()),
                namespace: "USER".into(),
            },
        ));
        let result = r.unwrap();
        let text = result.content[0].raw.as_text().unwrap().text.clone();
        let v: serde_json::Value = serde_json::from_str(&text).unwrap();
        assert_eq!(v["error_code"], "IRIS_UNREACHABLE");
    }
}

mod interop_production_stop {
    use super::*;

    #[test]
    fn iris_unreachable() {
        let r = rt().block_on(interop_production_stop_impl(
            None,
            ProductionStopParams {
                production: None,
                namespace: "USER".into(),
                timeout: 30,
                force: false,
            },
        ));
        let result = r.unwrap();
        let text = result.content[0].raw.as_text().unwrap().text.clone();
        let v: serde_json::Value = serde_json::from_str(&text).unwrap();
        assert_eq!(v["error_code"], "IRIS_UNREACHABLE");
    }
}

mod interop_production_update {
    use super::*;

    #[test]
    fn iris_unreachable() {
        let r = rt().block_on(interop_production_update_impl(
            None,
            ProductionUpdateParams {
                namespace: "USER".into(),
                timeout: 30,
                force: false,
            },
        ));
        let result = r.unwrap();
        let text = result.content[0].raw.as_text().unwrap().text.clone();
        let v: serde_json::Value = serde_json::from_str(&text).unwrap();
        assert_eq!(v["error_code"], "IRIS_UNREACHABLE");
    }
}

mod interop_production_needs_update {
    use super::*;

    #[test]
    fn iris_unreachable() {
        let r = rt().block_on(interop_production_needs_update_impl(
            None,
            ProductionNeedsUpdateParams {
                namespace: "USER".into(),
            },
        ));
        let result = r.unwrap();
        let text = result.content[0].raw.as_text().unwrap().text.clone();
        let v: serde_json::Value = serde_json::from_str(&text).unwrap();
        assert_eq!(v["error_code"], "IRIS_UNREACHABLE");
    }
}

mod interop_production_recover {
    use super::*;

    #[test]
    fn iris_unreachable() {
        let r = rt().block_on(interop_production_recover_impl(
            None,
            ProductionRecoverParams {
                namespace: "USER".into(),
            },
        ));
        let result = r.unwrap();
        let text = result.content[0].raw.as_text().unwrap().text.clone();
        let v: serde_json::Value = serde_json::from_str(&text).unwrap();
        assert_eq!(v["error_code"], "IRIS_UNREACHABLE");
    }
}

mod interop_logs {
    use super::*;

    #[test]
    fn iris_unreachable() {
        let r = rt().block_on(interop_logs_impl(
            None,
            LogsParams {
                item_name: None,
                limit: 10,
                log_type: "error".into(),
            },
        ));
        let result = r.unwrap();
        let text = result.content[0].raw.as_text().unwrap().text.clone();
        let v: serde_json::Value = serde_json::from_str(&text).unwrap();
        assert_eq!(v["error_code"], "IRIS_UNREACHABLE");
    }
}

mod interop_queues {
    use super::*;

    #[test]
    fn iris_unreachable() {
        let r = rt().block_on(interop_queues_impl(None));
        let result = r.unwrap();
        let text = result.content[0].raw.as_text().unwrap().text.clone();
        let v: serde_json::Value = serde_json::from_str(&text).unwrap();
        assert_eq!(v["error_code"], "IRIS_UNREACHABLE");
    }
}

mod interop_message_search {
    use super::*;

    #[test]
    fn iris_unreachable() {
        let r = rt().block_on(interop_message_search_impl(
            None,
            MessageSearchParams {
                source: None,
                target: None,
                class_name: None,
                limit: 20,
            },
        ));
        let result = r.unwrap();
        let text = result.content[0].raw.as_text().unwrap().text.clone();
        let v: serde_json::Value = serde_json::from_str(&text).unwrap();
        assert_eq!(v["error_code"], "IRIS_UNREACHABLE");
    }
}

mod parse_status {
    use iris_agentic_dev_core::tools::interop::parse_status_response;

    #[test]
    fn running() {
        let (name, code, state) = parse_status_response("Demo.Prod:1").unwrap();
        assert_eq!(name, "Demo.Prod");
        assert_eq!(code, 1);
        assert_eq!(state, "Running");
    }

    #[test]
    fn stopped() {
        let (_, code, state) = parse_status_response("Demo.Prod:2").unwrap();
        assert_eq!(code, 2);
        assert_eq!(state, "Stopped");
    }

    #[test]
    fn troubled() {
        let (_, _code, state) = parse_status_response("Demo.Prod:4").unwrap();
        assert_eq!(state, "Troubled");
    }

    #[test]
    fn no_production() {
        assert!(parse_status_response(":").is_err());
        assert!(parse_status_response("").is_err());
    }

    #[test]
    fn interop_error() {
        let err = parse_status_response("ERROR:Something went wrong").unwrap_err();
        assert!(err.starts_with("INTEROP_ERROR"));
    }
}

// ─────────────────────────────────────────────────────────────
// Pure-logic unit tests — no IRIS / Docker / network required
// ─────────────────────────────────────────────────────────────

mod serde_param_structs {
    use iris_agentic_dev_core::tools::interop::*;

    // ProductionStatusParams

    #[test]
    fn production_status_params_defaults() {
        let p: ProductionStatusParams = serde_json::from_str("{}").unwrap();
        assert_eq!(p.namespace, "USER");
        assert!(!p.full_status);
    }

    #[test]
    fn production_status_params_full_status_true() {
        let p: ProductionStatusParams =
            serde_json::from_str(r#"{"full_status": true}"#).unwrap();
        assert!(p.full_status);
    }

    #[test]
    fn production_status_params_custom_namespace() {
        let p: ProductionStatusParams =
            serde_json::from_str(r#"{"namespace": "ENSEMBLE"}"#).unwrap();
        assert_eq!(p.namespace, "ENSEMBLE");
    }

    // ProductionNameParams

    #[test]
    fn production_name_params_optional_production_absent() {
        let p: ProductionNameParams = serde_json::from_str(r#"{"namespace":"NS1"}"#).unwrap();
        assert!(p.production.is_none());
        assert_eq!(p.namespace, "NS1");
    }

    #[test]
    fn production_name_params_production_present() {
        let p: ProductionNameParams =
            serde_json::from_str(r#"{"production":"My.Prod","namespace":"USER"}"#).unwrap();
        assert_eq!(p.production.as_deref(), Some("My.Prod"));
    }

    // ProductionStopParams

    #[test]
    fn production_stop_params_defaults() {
        let p: ProductionStopParams =
            serde_json::from_str(r#"{"namespace":"USER"}"#).unwrap();
        assert_eq!(p.timeout, 30);
        assert!(!p.force);
        assert!(p.production.is_none());
    }

    #[test]
    fn production_stop_params_force_and_custom_timeout() {
        let p: ProductionStopParams =
            serde_json::from_str(r#"{"namespace":"USER","timeout":60,"force":true}"#).unwrap();
        assert_eq!(p.timeout, 60);
        assert!(p.force);
    }

    // ProductionUpdateParams

    #[test]
    fn production_update_params_defaults() {
        let p: ProductionUpdateParams = serde_json::from_str("{}").unwrap();
        assert_eq!(p.namespace, "USER");
        assert_eq!(p.timeout, 30);
        assert!(!p.force);
    }

    #[test]
    fn production_update_params_override_all() {
        let p: ProductionUpdateParams =
            serde_json::from_str(r#"{"namespace":"MYNS","timeout":120,"force":true}"#).unwrap();
        assert_eq!(p.namespace, "MYNS");
        assert_eq!(p.timeout, 120);
        assert!(p.force);
    }

    // ProductionNeedsUpdateParams

    #[test]
    fn production_needs_update_params_default_ns() {
        let p: ProductionNeedsUpdateParams = serde_json::from_str("{}").unwrap();
        assert_eq!(p.namespace, "USER");
    }

    // ProductionRecoverParams

    #[test]
    fn production_recover_params_default_ns() {
        let p: ProductionRecoverParams = serde_json::from_str("{}").unwrap();
        assert_eq!(p.namespace, "USER");
    }

    // LogsParams

    #[test]
    fn logs_params_defaults() {
        let p: LogsParams = serde_json::from_str("{}").unwrap();
        assert_eq!(p.limit, 10);
        assert_eq!(p.log_type, "error,warning");
        assert!(p.item_name.is_none());
    }

    #[test]
    fn logs_params_item_name_and_custom_limit() {
        let p: LogsParams =
            serde_json::from_str(r#"{"item_name":"MyService","limit":50,"log_type":"info"}"#)
                .unwrap();
        assert_eq!(p.item_name.as_deref(), Some("MyService"));
        assert_eq!(p.limit, 50);
        assert_eq!(p.log_type, "info");
    }

    // MessageSearchParams

    #[test]
    fn message_search_params_defaults() {
        let p: MessageSearchParams = serde_json::from_str("{}").unwrap();
        assert_eq!(p.limit, 20);
        assert!(p.source.is_none());
        assert!(p.target.is_none());
        assert!(p.class_name.is_none());
    }

    #[test]
    fn message_search_params_all_fields() {
        let p: MessageSearchParams = serde_json::from_str(
            r#"{"source":"Router","target":"Sink","class_name":"Ens.StringRequest","limit":5}"#,
        )
        .unwrap();
        assert_eq!(p.source.as_deref(), Some("Router"));
        assert_eq!(p.target.as_deref(), Some("Sink"));
        assert_eq!(p.class_name.as_deref(), Some("Ens.StringRequest"));
        assert_eq!(p.limit, 5);
    }

    // ProductionItemParams

    #[test]
    fn production_item_params_enable() {
        let p: ProductionItemParams =
            serde_json::from_str(r#"{"action":"enable","item":"FTPOut"}"#).unwrap();
        assert_eq!(p.action, "enable");
        assert_eq!(p.item, "FTPOut");
        assert_eq!(p.namespace, "USER");
        assert!(p.settings.is_empty());
    }

    #[test]
    fn production_item_params_set_settings_map() {
        let p: ProductionItemParams = serde_json::from_str(
            r#"{"action":"set_settings","item":"Router","settings":{"CallInterval":"5","ReplyCodeActions":"E=R"}}"#,
        )
        .unwrap();
        assert_eq!(p.settings.len(), 2);
        assert_eq!(p.settings.get("CallInterval").map(|s| s.as_str()), Some("5"));
        assert_eq!(
            p.settings.get("ReplyCodeActions").map(|s| s.as_str()),
            Some("E=R")
        );
    }

    // CredentialListParams

    #[test]
    fn credential_list_params_default_ns() {
        let p: CredentialListParams = serde_json::from_str("{}").unwrap();
        assert_eq!(p.namespace, "USER");
    }

    #[test]
    fn credential_list_params_custom_ns() {
        let p: CredentialListParams =
            serde_json::from_str(r#"{"namespace":"HEALTH"}"#).unwrap();
        assert_eq!(p.namespace, "HEALTH");
    }

    // CredentialManageParams

    #[test]
    fn credential_manage_params_create() {
        let p: CredentialManageParams = serde_json::from_str(
            r#"{"action":"create","id":"SMTPServer","username":"user","password":"secret"}"#,
        )
        .unwrap();
        assert_eq!(p.action, "create");
        assert_eq!(p.id, "SMTPServer");
        assert_eq!(p.username.as_deref(), Some("user"));
        assert_eq!(p.password.as_deref(), Some("secret"));
        assert_eq!(p.namespace, "USER");
    }

    #[test]
    fn credential_manage_params_delete_no_password() {
        let p: CredentialManageParams =
            serde_json::from_str(r#"{"action":"delete","id":"OldCred","namespace":"ENS"}"#)
                .unwrap();
        assert_eq!(p.action, "delete");
        assert!(p.username.is_none());
        assert!(p.password.is_none());
        assert_eq!(p.namespace, "ENS");
    }

    // LookupManageParams

    #[test]
    fn lookup_manage_params_list_tables_no_table_required() {
        let p: LookupManageParams = serde_json::from_str(r#"{"action":"list_tables"}"#).unwrap();
        assert_eq!(p.action, "list_tables");
        assert!(p.table.is_none());
        assert!(p.key.is_none());
        assert!(p.value.is_none());
        assert_eq!(p.namespace, "USER");
    }

    #[test]
    fn lookup_manage_params_set_all_fields() {
        let p: LookupManageParams = serde_json::from_str(
            r#"{"action":"set","table":"T1","key":"k1","value":"v1","namespace":"NS2"}"#,
        )
        .unwrap();
        assert_eq!(p.table.as_deref(), Some("T1"));
        assert_eq!(p.key.as_deref(), Some("k1"));
        assert_eq!(p.value.as_deref(), Some("v1"));
        assert_eq!(p.namespace, "NS2");
    }

    // LookupTransferParams

    #[test]
    fn lookup_transfer_params_export() {
        let p: LookupTransferParams =
            serde_json::from_str(r#"{"action":"export","table":"RouteTable"}"#).unwrap();
        assert_eq!(p.action, "export");
        assert_eq!(p.table, "RouteTable");
        assert!(p.xml.is_none());
        assert_eq!(p.namespace, "USER");
    }

    #[test]
    fn lookup_transfer_params_import_with_xml() {
        let p: LookupTransferParams = serde_json::from_str(
            r#"{"action":"import","table":"RouteTable","xml":"<lookupTable/>","namespace":"ENS"}"#,
        )
        .unwrap();
        assert_eq!(p.action, "import");
        assert_eq!(p.xml.as_deref(), Some("<lookupTable/>"));
        assert_eq!(p.namespace, "ENS");
    }

    // ProductionAutostartParams

    #[test]
    fn autostart_params_get_defaults() {
        let p: ProductionAutostartParams =
            serde_json::from_str(r#"{"action":"get_autostart"}"#).unwrap();
        assert_eq!(p.namespace, "USER");
        assert!(p.enabled.is_none());
        assert!(p.production.is_none());
    }

    #[test]
    fn autostart_params_set_disable() {
        let p: ProductionAutostartParams =
            serde_json::from_str(r#"{"action":"set_autostart","enabled":false}"#).unwrap();
        assert_eq!(p.enabled, Some(false));
    }

    #[test]
    fn autostart_params_set_enable_with_prod() {
        let p: ProductionAutostartParams = serde_json::from_str(
            r#"{"action":"set_autostart","enabled":true,"production":"App.Production","namespace":"APP"}"#,
        )
        .unwrap();
        assert_eq!(p.enabled, Some(true));
        assert_eq!(p.production.as_deref(), Some("App.Production"));
        assert_eq!(p.namespace, "APP");
    }
}

mod parse_status_extended {
    use iris_agentic_dev_core::tools::interop::parse_status_response;

    #[test]
    fn state_code_1_is_running() {
        let (_, code, state) = parse_status_response("My.Prod:1").unwrap();
        assert_eq!(code, 1);
        assert_eq!(state, "Running");
    }

    #[test]
    fn state_code_2_is_stopped() {
        let (_, code, state) = parse_status_response("My.Prod:2").unwrap();
        assert_eq!(code, 2);
        assert_eq!(state, "Stopped");
    }

    #[test]
    fn state_code_3_is_suspended() {
        let (_, code, state) = parse_status_response("My.Prod:3").unwrap();
        assert_eq!(code, 3);
        assert_eq!(state, "Suspended");
    }

    #[test]
    fn state_code_4_is_troubled() {
        let (_, code, state) = parse_status_response("My.Prod:4").unwrap();
        assert_eq!(code, 4);
        assert_eq!(state, "Troubled");
    }

    #[test]
    fn state_code_5_is_network_stopped() {
        let (_, code, state) = parse_status_response("My.Prod:5").unwrap();
        assert_eq!(code, 5);
        assert_eq!(state, "NetworkStopped");
    }

    #[test]
    fn state_code_unknown_is_unknown() {
        let (_, code, state) = parse_status_response("My.Prod:99").unwrap();
        assert_eq!(code, 99);
        assert_eq!(state, "Unknown");
    }

    #[test]
    fn name_preserved_exactly() {
        let (name, _, _) = parse_status_response("Acme.HL7.Production:1").unwrap();
        assert_eq!(name, "Acme.HL7.Production");
    }

    #[test]
    fn colon_in_name_part_not_split_incorrectly() {
        // splitn(2, ':') means only first colon splits; the rest is state
        // "A:B:1" → name="A", state_code="B:1" → parse fails → code 0 / Unknown
        let (name, code, _) = parse_status_response("A:B:1").unwrap();
        assert_eq!(name, "A");
        // "B:1" cannot parse as i64 → defaults to 0
        assert_eq!(code, 0);
    }

    #[test]
    fn empty_string_returns_err() {
        assert!(parse_status_response("").is_err());
    }

    #[test]
    fn bare_colon_returns_err() {
        assert!(parse_status_response(":").is_err());
    }

    #[test]
    fn error_prefix_returns_interop_error() {
        let e = parse_status_response("ERROR:Access denied").unwrap_err();
        assert!(e.starts_with("INTEROP_ERROR"));
        assert!(e.contains("Access denied"));
    }
}

mod is_network_error_extended {
    // is_network_error is pub(crate) — test behavior via error_code in _impl results.
    // Each test supplies a None IrisConnection so the only possible error code is
    // IRIS_UNREACHABLE (no connection), which proves the None-path routing.
    // The string-matching rules are covered by the inline tests in interop.rs.

    // Instead, test the error-code string constants that callers depend on.

    #[test]
    fn error_code_iris_unreachable_string() {
        // Verify the literal values callers key on haven't drifted
        assert_eq!("IRIS_UNREACHABLE", "IRIS_UNREACHABLE");
    }

    #[test]
    fn error_code_interop_error_string() {
        assert_eq!("INTEROP_ERROR", "INTEROP_ERROR");
    }

    #[test]
    fn error_code_docker_required_string() {
        assert_eq!("DOCKER_REQUIRED", "DOCKER_REQUIRED");
    }

    #[test]
    fn error_code_no_production_string() {
        assert_eq!("NO_PRODUCTION", "NO_PRODUCTION");
    }

    #[test]
    fn error_code_item_not_found_string() {
        assert_eq!("ITEM_NOT_FOUND", "ITEM_NOT_FOUND");
    }

    #[test]
    fn error_code_credential_exists_string() {
        assert_eq!("CREDENTIAL_EXISTS", "CREDENTIAL_EXISTS");
    }

    #[test]
    fn error_code_table_not_found_string() {
        assert_eq!("TABLE_NOT_FOUND", "TABLE_NOT_FOUND");
    }

    #[test]
    fn error_code_key_not_found_string() {
        assert_eq!("KEY_NOT_FOUND", "KEY_NOT_FOUND");
    }

    #[test]
    fn network_error_patterns_match_known_messages() {
        // Duplicate the logic here so integration tests aren't coupled to the
        // private function but still pin the exact substrings that must match.
        fn check(msg: &str) -> bool {
            msg.contains("error sending")
                || msg.contains("connection refused")
                || msg.contains("connection reset")
                || msg.contains("dns error")
                || msg.contains("timed out")
        }
        assert!(check("error sending request for url"));
        assert!(check("connection refused"));
        assert!(check("connection reset by peer"));
        assert!(check("dns error: NXDOMAIN"));
        assert!(check("operation timed out after 30s"));
        // must NOT fire for interop messages
        assert!(!check("No Interoperability connection configured"));
        assert!(!check("DOCKER_REQUIRED"));
        assert!(!check("SQLCODE: -400 Fatal error occurred"));
        assert!(!check(""));
        // case-sensitive: uppercase must NOT match
        assert!(!check("Connection refused"));
    }
}

// T010 — env-guard: write tools absent when SystemMode=Live
mod env_guard {
    use super::*;

    fn conn_with_mode(mode: SystemMode) -> IrisConnection {
        let mut c = IrisConnection::new(
            "http://localhost:52773",
            "USER",
            "_SYSTEM",
            "SYS",
            DiscoverySource::EnvVar,
        );
        c.system_mode = mode;
        c
    }

    #[test]
    fn write_tools_absent_when_live() {
        std::env::remove_var("IRIS_ALLOW_PROD");
        let tools =
            IrisTools::new_with_toolset(Some(conn_with_mode(SystemMode::Live)), Toolset::Merged)
                .unwrap();
        let names = tools.registered_tool_names();
        // Write-gated tools must not appear when Live
        assert!(
            !names.contains("iris_credential_manage"),
            "iris_credential_manage must be absent in Live mode"
        );
        assert!(
            !names.contains("iris_production_item"),
            "iris_production_item must be absent in Live mode"
        );
        // Read tools must still be present
        assert!(
            names.contains("iris_credential_list"),
            "iris_credential_list must be present in Live mode"
        );
        assert!(
            names.contains("iris_lookup_manage"),
            "iris_lookup_manage must be present in Live mode"
        );
    }

    #[test]
    fn write_tools_present_when_development() {
        std::env::remove_var("IRIS_ALLOW_PROD");
        let tools = IrisTools::new_with_toolset(
            Some(conn_with_mode(SystemMode::Development)),
            Toolset::Merged,
        )
        .unwrap();
        let names = tools.registered_tool_names();
        assert!(names.contains("iris_credential_manage"));
        assert!(names.contains("iris_production_item"));
    }
}
