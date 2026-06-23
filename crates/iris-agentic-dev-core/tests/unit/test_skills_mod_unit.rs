// Unit tests for skills/mod.rs — SkillRegistry public API, struct field access,
// and error paths that do not require a network connection.

use iris_agentic_dev_core::skills::{KbItem, Skill, SkillRegistry};

// ── SkillRegistry::new ────────────────────────────────────────────────────────

#[test]
fn registry_new_has_no_skills() {
    let registry = SkillRegistry::new();
    assert_eq!(registry.list_skills().len(), 0);
}

#[test]
fn registry_new_has_no_kb_items() {
    let registry = SkillRegistry::new();
    assert_eq!(registry.list_kb_items().len(), 0);
}

// ── SkillRegistry::default ────────────────────────────────────────────────────

#[test]
fn registry_default_equals_new() {
    let a = SkillRegistry::new();
    let b = SkillRegistry::default();
    assert_eq!(a.list_skills().len(), b.list_skills().len());
    assert_eq!(a.list_kb_items().len(), b.list_kb_items().len());
}

// ── list_skills / list_kb_items return slice references ──────────────────────

#[test]
fn list_skills_returns_empty_slice_not_panic() {
    let r = SkillRegistry::new();
    let skills: &[Skill] = r.list_skills();
    assert!(skills.is_empty());
}

#[test]
fn list_kb_items_returns_empty_slice_not_panic() {
    let r = SkillRegistry::new();
    let items: &[KbItem] = r.list_kb_items();
    assert!(items.is_empty());
}

// ── Skill struct field access ─────────────────────────────────────────────────

#[test]
fn skill_fields_are_accessible() {
    let s = Skill {
        name: "my-skill".to_string(),
        description: "does something".to_string(),
        content: "---\nname: my-skill\n---\n# Title".to_string(),
        source_repo: "owner/repo".to_string(),
    };
    assert_eq!(s.name, "my-skill");
    assert_eq!(s.description, "does something");
    assert!(s.content.contains("my-skill"));
    assert_eq!(s.source_repo, "owner/repo");
}

#[test]
fn skill_name_can_be_empty_string() {
    let s = Skill {
        name: String::new(),
        description: String::new(),
        content: String::new(),
        source_repo: String::new(),
    };
    assert!(s.name.is_empty());
}

// ── KbItem struct field access ────────────────────────────────────────────────

#[test]
fn kb_item_fields_are_accessible() {
    let item = KbItem {
        title: "IRIS Vector Patterns".to_string(),
        content: "# IRIS Vector Patterns\n\nContent here.".to_string(),
        source_repo: "intersystems-community/iris-vector-rag".to_string(),
    };
    assert_eq!(item.title, "IRIS Vector Patterns");
    assert!(item.content.starts_with("# IRIS Vector Patterns"));
    assert_eq!(item.source_repo, "intersystems-community/iris-vector-rag");
}

#[test]
fn kb_item_content_can_be_multiline() {
    let item = KbItem {
        title: "t".to_string(),
        content: "line1\nline2\nline3".to_string(),
        source_repo: "o/r".to_string(),
    };
    assert_eq!(item.content.lines().count(), 3);
}

// ── load_from_github error path: missing '/' in owner_repo ───────────────────

#[tokio::test]
async fn load_from_github_no_slash_returns_error() {
    let mut registry = SkillRegistry::new();
    let result = registry.load_from_github("nodash").await;
    assert!(result.is_err(), "should fail when owner/repo has no slash");
    let msg = format!("{:?}", result.unwrap_err());
    assert!(
        msg.contains("invalid owner/repo"),
        "error message should mention 'invalid owner/repo', got: {msg}"
    );
}

#[tokio::test]
async fn load_from_github_empty_string_returns_error() {
    let mut registry = SkillRegistry::new();
    let result = registry.load_from_github("").await;
    assert!(result.is_err(), "empty string should fail");
}

#[tokio::test]
async fn load_from_github_error_does_not_add_skills() {
    let mut registry = SkillRegistry::new();
    let _ = registry.load_from_github("no-slash-here").await;
    assert_eq!(
        registry.list_skills().len(),
        0,
        "failed load must not add partial skills"
    );
}

#[tokio::test]
async fn load_from_github_error_does_not_add_kb_items() {
    let mut registry = SkillRegistry::new();
    let _ = registry.load_from_github("no-slash-here").await;
    assert_eq!(
        registry.list_kb_items().len(),
        0,
        "failed load must not add partial kb items"
    );
}

// ── Registry is mutable and reusable after an error ──────────────────────────

#[tokio::test]
async fn registry_usable_after_failed_load() {
    let mut registry = SkillRegistry::new();
    let _ = registry.load_from_github("bad-input").await;
    // Registry should still be in a valid, queryable state.
    assert_eq!(registry.list_skills().len(), 0);
    assert_eq!(registry.list_kb_items().len(), 0);
}

#[tokio::test]
async fn multiple_failed_loads_leave_registry_empty() {
    let mut registry = SkillRegistry::new();
    for _ in 0..3 {
        let _ = registry.load_from_github("no-slash").await;
    }
    assert_eq!(registry.list_skills().len(), 0);
    assert_eq!(registry.list_kb_items().len(), 0);
}

// ── Skill and KbItem source_repo carries the original owner/repo string ───────

#[test]
fn skill_source_repo_preserves_slash_format() {
    let s = Skill {
        name: "n".to_string(),
        description: "d".to_string(),
        content: String::new(),
        source_repo: "acme/my-skills".to_string(),
    };
    assert!(s.source_repo.contains('/'));
    let parts: Vec<&str> = s.source_repo.splitn(2, '/').collect();
    assert_eq!(parts[0], "acme");
    assert_eq!(parts[1], "my-skills");
}

#[test]
fn kb_item_source_repo_preserves_slash_format() {
    let item = KbItem {
        title: "t".to_string(),
        content: String::new(),
        source_repo: "acme/my-skills".to_string(),
    };
    assert_eq!(item.source_repo, "acme/my-skills");
}
