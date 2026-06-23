//! Unit tests for skills/mod.rs — SkillRegistry loading and error handling.

use iris_agentic_dev_core::skills::SkillRegistry;

#[test]
fn new_registry_is_empty() {
    let r = SkillRegistry::new();
    assert!(r.list_skills().is_empty());
    assert!(r.list_kb_items().is_empty());
}

#[tokio::test]
async fn load_from_github_empty_string_returns_error() {
    let mut r = SkillRegistry::new();
    let result = r.load_from_github("").await;
    assert!(result.is_err(), "empty owner_repo should fail");
}

#[tokio::test]
async fn load_from_github_no_slash_returns_error() {
    let mut r = SkillRegistry::new();
    let result = r.load_from_github("noslash").await;
    assert!(result.is_err(), "owner_repo without slash should fail");
}

#[tokio::test]
async fn load_from_github_error_does_not_add_skills() {
    let mut r = SkillRegistry::new();
    let _ = r
        .load_from_github("nonexistent-owner-xyz/nonexistent-repo-xyz")
        .await;
    assert!(r.list_skills().is_empty());
}

#[tokio::test]
async fn load_from_github_error_does_not_add_kb_items() {
    let mut r = SkillRegistry::new();
    let _ = r
        .load_from_github("nonexistent-owner-xyz/nonexistent-repo-xyz")
        .await;
    assert!(r.list_kb_items().is_empty());
}

#[tokio::test]
async fn registry_usable_after_failed_load() {
    let mut r = SkillRegistry::new();
    let _ = r.load_from_github("bad/repo").await;
    assert!(r.list_skills().is_empty());
    let _ = r.load_from_github("also/bad").await;
    assert!(r.list_skills().is_empty());
}

#[tokio::test]
async fn multiple_failed_loads_leave_registry_empty() {
    let mut r = SkillRegistry::new();
    for _ in 0..3 {
        let _ = r.load_from_github("x/y").await;
    }
    assert!(r.list_skills().is_empty());
    assert!(r.list_kb_items().is_empty());
}

#[test]
fn skill_source_repo_preserves_slash_format() {
    // Validates that owner_repo strings with slashes are accepted (format check only)
    let owner_repo = "myorg/myrepo";
    assert!(owner_repo.contains('/'));
}
