---
name: arch-map
description: Use when mapping a repository architecture, refreshing an existing architecture map, or checking whether docs/architecture/map.md is current.
---

# Architecture Map

Create or reuse a grounded snapshot of the current repository at
`docs/architecture/map.md`. This is a standalone capability, not a wrapper for
a Superpowers skill.

## Boundary and input

- Write only `docs/architecture/map.md` and create its parent directory when
  missing. Do not write elsewhere under `docs/architecture/` or change code.
- Treat only an exact `force` argument as forced regeneration. Similar words,
  capitalization, or surrounding arguments do not bypass reuse.
- Operate on the current workspace and current Git state.

## Decide freshness before scanning

Read the map when present. Resolve the current full HEAD SHA with
`git rev-parse HEAD`; use `not-a-git-worktree` outside Git. Parse the stored
`HEAD SHA`, `Key Paths`, generated timestamp, and generation method.

The map is stale when it is missing, its SHA differs, any missing referenced
key path is found, or generation metadata is absent or malformed. Without
`force`, reuse a current map without a repository scan or rewrite. With
`force`, regenerate even when it is current. A caller such as `$spec-plan` may
warn that a map is stale, but must not invoke regeneration implicitly.

## Scan once

Perform one compact read-only scan. When read-only delegation is available,
request one structured evidence digest covering:

- modules, responsibilities, entry points, and verified key paths;
- dependency direction, boundaries, and observed cycles;
- data stores and persistence mechanisms;
- external integrations and their configuration or call sites;
- tests, frameworks, layouts, and fixtures; and
- build and test commands supported by a manifest or project instructions.

Do not request raw file dumps or infer unsupported components. If delegation
is unavailable, perform the same scan in context with read-only search and
inspection tools and label the generation method `arch-map (in-context
fallback)`. Otherwise label it `arch-map (delegated scan)`.

## Replace safely

Build the complete map in memory before touching an existing file. Verify
every key path still exists. Include an ISO 8601 timestamp with timezone, the
current full HEAD SHA or sentinel, the generation method, and these sections:

1. Generation Metadata
2. Modules
3. Dependency Graph, including direction, boundaries, and observed cycles
4. Data Stores
5. External Integrations
6. Test Topology
7. Build and Test Commands with manifest or instruction sources

Use `None observed` rather than guessing. If the scan fails, evidence is
incomplete, or paths cannot be validated, retain the existing map and report
the blocker. Never replace it with partial content.

Report exactly which outcome occurred: created, stale-regenerated, forced, or
reused.
