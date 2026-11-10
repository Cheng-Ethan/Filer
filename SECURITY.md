# Security Policy

## Reporting a Vulnerability

Please do not open a public issue for security problems.

Report vulnerabilities privately through GitHub Security Advisories for this repository. Include enough detail to reproduce the issue, such as affected versions, configuration, and steps to trigger it.

## Known Security Boundaries

- HTTP Basic Auth is used, and credentials are not encrypted by the application itself. TLS must be provided by a reverse proxy or another transport layer.
- There is no rate limiting.
- There is no audit log.
- The application is single-user. There are no roles or per-directory permissions.
- The server is intended to bind to localhost and sit behind a trusted reverse proxy when exposed to a network.

## Response Expectations

This is a small project maintained on a best-effort basis. You can usually expect an initial response within one week.
