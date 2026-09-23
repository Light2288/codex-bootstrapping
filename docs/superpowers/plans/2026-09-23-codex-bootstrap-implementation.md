# Codex Bootstrapping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a public macOS bootstrap repository that distributes the existing personal Codex workflows and safely configures an optional custom model provider.

**Architecture:** Keep the copied Codex marketplace and plugin as immutable distribution content, then add small scripts around it: a provider-neutral zsh bootstrap, a zsh provider wizard backed by a testable Python TOML transformer, and independent verification/uninstall utilities. All installers operate against explicit or standard user paths only when invoked and provide check/dry-run paths for safe validation.

**Tech Stack:** zsh, Python 3 standard library, Codex plugin CLI, macOS Keychain, unittest, JSON/TOML configuration.

**Spec:** `docs/superpowers/specs/2026-09-23-codex-bootstrap-design.md`

## Global Constraints

- Never modify `/Users/davide/.agents/plugins/personal`, `~/.agents`, or `~/.codex` while building or testing this repository.
- Copy all 13 approved skills and five approved agents from the tracked source marketplace.
- Do not vendor or alter Superpowers; install it as a runtime dependency.
- Do not include or configure Figma.
- Never commit, print, log, or write an API key to TOML.
- All user-file replacement must be confirmed, backed up, and atomic where practical.
- Check and dry-run modes perform no writes.
- Default provider values exactly match the reviewed IBM ICA installer, with `supports_websockets = false`.

## Review Focus

- A machine with the ChatGPT-bundled Codex binary but no `codex` in `PATH` must be detected without attempting installation.
- An existing marketplace named `personal` that points elsewhere must fail clearly instead of being overwritten.
- Existing unrelated `config.toml` tables and comments must survive provider configuration.
- Provider IDs, URLs, TOML strings, and credential names containing unsafe input must be rejected before any mutation.
- Re-running bootstrap, profile installation, provider configuration, and uninstall must be idempotent and preserve unrelated files.

---

### Task 1: Public Plugin Distribution

**Files:**
- Create: `.agents/plugins/marketplace.json`
- Create: `plugins/personal-workflows/**`
- Create: `tests/test_distribution.py`
- Create: `README.md`
- Create: `LICENSE`
- Create: `SECURITY.md`
- Create: `CHANGELOG.md`
- Create: `CONTRIBUTING.md`
- Create: `docs/workflows.md`

**Interfaces:**
- Consumes: tracked files from `/Users/davide/.agents/plugins/personal` as read-only source material.
- Produces: a repo-local `personal` marketplace, the `personal-workflows` plugin, and distribution metadata used by later installers.

- [ ] **Step 1: Write distribution tests first**

Add `unittest` coverage that asserts the marketplace/manifest relationship, strict version and public metadata, exactly 13 expected skill directories, exactly five expected agent TOML files, the profile installer check mode against a temporary Codex home, no Figma declarations, and no likely credential files or values.

- [ ] **Step 2: Run the distribution tests and verify RED**

Run: `python3 -m unittest tests.test_distribution -v`

Expected: FAIL because the marketplace and plugin have not been copied into the repository.

- [ ] **Step 3: Copy the tracked plugin source and add public metadata**

Copy only tracked marketplace/plugin files from the source repository. Update the copied manifest for repository URL, author, license, keywords, and public interface metadata without changing skill behavior. Add the README, public project documents, and workflow guide. Do not copy `.git`, caches, backups, credentials, or `.superpowers` scratch data.

- [ ] **Step 4: Run tests and existing plugin validators**

Run: `python3 -m unittest discover -s tests -v`

Run the copied plugin's existing test suite and the Codex plugin validator. Expected: all tests and validation pass.

- [ ] **Step 5: Commit**

```bash
git add .agents plugins tests README.md LICENSE SECURITY.md CHANGELOG.md CONTRIBUTING.md docs/workflows.md
git commit -m "feat: publish personal workflows plugin"
```

### Task 2: Interactive Provider Configurator

**Files:**
- Create: `scripts/provider_config.py`
- Create: `scripts/configure-provider.zsh`
- Create: `tests/test_provider_config.py`
- Create: `docs/provider-configuration.md`

**Interfaces:**
- Consumes: an existing or empty Codex `config.toml`, interactive provider values, and a hidden credential.
- Produces: `ProviderSettings`, `merge_config(existing: str, settings: ProviderSettings) -> str`, a redacted preview, and a confirmed atomic update using Keychain or environment-variable authentication.

- [ ] **Step 1: Write provider transformer tests first**

Cover exact IBM defaults, preservation of unrelated root keys/tables/comments, replacement of an existing selected provider table, escaped TOML values, invalid provider IDs/URLs/reasoning values/environment variable names, WebSocket true/false rendering, Keychain versus environment auth exclusivity, malformed managed tables, and deterministic output.

- [ ] **Step 2: Run the provider tests and verify RED**

Run: `python3 -m unittest tests.test_provider_config -v`

Expected: FAIL because `scripts.provider_config` does not exist.

- [ ] **Step 3: Implement the minimal Python transformer**

Create an immutable settings model, validation functions, TOML string quoting, root-key replacement, selected-table replacement, preview serialization, atomic write/backup helpers, and a non-interactive CLI used by the zsh wrapper. No code path accepts or emits the API key.

- [ ] **Step 4: Implement the interactive zsh wrapper**

Prompt for every documented value with exact defaults, read the API key silently, offer Keychain as the default storage mode, show a redacted preview, request confirmation, store the secret only after confirmation, invoke the Python transformer, validate, and optionally smoke-test Codex. Implement `--check` and `--dry-run` without writes.

- [ ] **Step 5: Run provider tests and syntax checks**

Run: `python3 -m unittest tests.test_provider_config -v`

Run: `zsh -n scripts/configure-provider.zsh`

Expected: all pass with no output containing test secrets.

- [ ] **Step 6: Commit**

```bash
git add scripts/provider_config.py scripts/configure-provider.zsh tests/test_provider_config.py docs/provider-configuration.md
git commit -m "feat: add interactive provider configuration"
```

### Task 3: Bootstrap, Verification, and Uninstall

**Files:**
- Create: `scripts/bootstrap-macos.zsh`
- Create: `scripts/verify.zsh`
- Create: `scripts/uninstall-profile.py`
- Create: `tests/test_bootstrap.py`
- Create: `tests/test_uninstall_profile.py`
- Create: `docs/installation.md`
- Create: `docs/troubleshooting.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: the repository root, Codex CLI discovery candidates, Codex plugin JSON output, and a target Codex home.
- Produces: `resolve_codex`, check/dry-run/install modes, repository verification, and safe removal of only managed profile artifacts.

- [ ] **Step 1: Write bootstrap and uninstall tests first**

Use temporary homes and fake executables to cover bundled Codex discovery, missing Codex, check/dry-run no-write behavior, repository-root discovery, marketplace conflict handling, idempotent profile installation, safe managed-agent removal, refusal to remove unmanaged agents, and guidance-block removal.

- [ ] **Step 2: Run the new tests and verify RED**

Run: `python3 -m unittest tests.test_bootstrap tests.test_uninstall_profile -v`

Expected: FAIL because the bootstrap and uninstall utilities do not exist.

- [ ] **Step 3: Implement bootstrap and verification**

Implement macOS checks, Codex discovery, confirmed official installer download, dependency checks, Superpowers installation/verification, conflict-safe marketplace registration, plugin installation, profile install/check, `--check`, `--dry-run`, and a verification script that runs every repository test and static validation without touching live Codex state.

- [ ] **Step 4: Implement safe uninstall and finish documentation**

Remove only the marked guidance block and exact managed agent files, support check mode, refuse unmanaged collisions, and document manual Codex plugin/marketplace removal. Complete README installation, update, verification, security, troubleshooting, and new-task instructions.

- [ ] **Step 5: Run the full verification suite**

Run: `zsh scripts/verify.zsh`

Expected: all Python tests, zsh syntax checks, plugin contract tests, manifest validation, secret scanning, and no-Figma checks pass.

- [ ] **Step 6: Commit**

```bash
git add scripts tests docs README.md
git commit -m "feat: add macOS bootstrap and lifecycle tools"
```

