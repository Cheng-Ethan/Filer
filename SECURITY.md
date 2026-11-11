# Security Policy

## Reporting a Vulnerability

Please do not open a public issue for security problems.

Report vulnerabilities privately through GitHub Security Advisories:

https://github.com/Cheng-Ethan/Filer/security/advisories/new

Include enough detail to reproduce the issue, such as affected versions or
commits, configuration, plugins installed, and steps to trigger it.

## Supported Versions

This is a small project maintained on a best-effort basis. Security fixes are
applied to the current release line (`0.1.x` at the time of writing). There
is no long-term support promise for older releases or forks.

## Known Security Boundaries

- HTTP Basic Auth is used, and credentials are not encrypted by the
  application itself. TLS must be provided by a reverse proxy or another
  transport layer.
- There is no rate limiting.
- There is no audit log.
- The application is single-user. There are no roles or per-directory
  permissions.
- The server is intended to bind to localhost and sit behind a trusted
  reverse proxy when exposed to a network.
- The shell endpoint executes arbitrary commands as the service user.
- Text editing can overwrite files. Backups under `cache/edit-backups/` are a
  convenience, not a backup system.
- Plugins are trusted code. They run in the server process with the service
  account's permissions and there is no sandbox. Only install plugins you
  trust, and review their dependencies.
- Office editing is not included in this release. A future plugin that edits
  Office documents will add parser and data-loss risk; treat it as trusted
  code.

See [docs/security-model.md](docs/security-model.md) for the complete threat
model and deployment checklist.

## What to Include in a Report

- Affected route, feature, or plugin API.
- Whether authentication was required.
- Whether plugins were enabled and which ones.
- Configuration relevant to the issue (`--bind`, `--dir`, reverse proxy,
  filesystem permissions).
- A minimal reproduction, with secrets, file contents, and private paths
  removed.

## Response Expectations

You can usually expect an initial response within one week. This is a
best-effort project; response and fix times depend on severity and
maintainer availability.
