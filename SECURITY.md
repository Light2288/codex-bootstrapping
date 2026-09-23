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
