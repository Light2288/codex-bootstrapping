# Security Policy

## Reporting a vulnerability

Please report potential security vulnerabilities privately to the repository
maintainer through GitHub's private vulnerability-reporting feature. Do not
include credentials, API keys, or other secrets in an issue, pull request, or
log.

Reports should describe the affected version, reproduction steps, and expected
impact. The maintainer will acknowledge a report, investigate it, and work
with the reporter on coordinated disclosure.

## Scope

This repository intentionally excludes user credentials, local Codex state,
and machine-local provider state. The provider configurator and its public
documentation are tracked, but generated provider configuration and stored
credentials are not. Treat any unexpected secret-like value in the repository
as a security issue.

Credential-only reconfiguration keeps input hidden, passes it to the bundled
Keychain helper over standard input, and skips the configuration merge/write
path; the transformer is invoked only to validate the provider ID.
Models-only reconfiguration never accesses Keychain or plugin caches. It
requires exact `personal-workflows` ownership markers, refuses symlinked or
malformed targets, and uses backups, atomic pathname exchange, verified
post-replacement identities, a persistent lock inode, and atomically replaced
checksummed transaction metadata. A later run rejects corrupt metadata or
recovers a stale interrupted transaction before applying new assignments;
coexisting legacy/new journals must agree, and final cleanup exchanges and
verifies complete journal records before atomically moving the live record off
its pathname. Every cleanup crash point therefore leaves either a valid
journal or no live journal. Unexpected external target or journal content is
preserved rather than overwritten.
