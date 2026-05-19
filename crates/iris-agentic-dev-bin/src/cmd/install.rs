use anyhow::{Context, Result};
use clap::Args;
use iris_agentic_dev_core::manifest::{parse_manifest, Resolve};

#[derive(Args)]
pub struct InstallCommand {
    #[arg(long)]
    pub locked: bool,
    #[arg(long)]
    pub dry_run: bool,
}

impl InstallCommand {
    pub async fn run(self) -> Result<()> {
        let manifest_path = std::path::PathBuf::from("iris-agentic-dev.toml");
        let manifest = parse_manifest(&manifest_path).context(
            "could not read iris-agentic-dev.toml — run this command in a directory with an iris-agentic-dev.toml",
        )?;

        println!("Resolving {} dependencies...", manifest.dependencies.len());

        let resolve = Resolve::from_manifest(&manifest).context("dependency resolution failed")?;

        let lock = resolve.to_lock();

        if self.dry_run {
            println!("Would install {} packages:", lock.packages.len());
            for pkg in &lock.packages {
                println!("  {} v{} ({})", pkg.name, pkg.version, pkg.repository);
            }
            return Ok(());
        }

        let lock_content = lock.to_toml();
        std::fs::write("iris-agentic-dev.lock", &lock_content)
            .context("failed to write iris-agentic-dev.lock")?;

        println!(
            "Wrote iris-agentic-dev.lock with {} packages",
            lock.packages.len()
        );
        for pkg in &lock.packages {
            println!("  ✓ {} v{}", pkg.name, pkg.version);
        }

        Ok(())
    }
}
