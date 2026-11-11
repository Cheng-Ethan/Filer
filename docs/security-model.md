# Security Model

This document describes what filer protects, what it does not protect, and
how to deploy it safely. It is a practical threat model for operators and
developers, not a guarantee.

## Intended use

filer is a **single-user, trusted-operator** file browser. It is designed for
a person who already has administrative access to a server and wants a
convenient browser UI for files and commands.

It is **not** a multi-tenant file-sharing service. Do not give accounts to
untrusted users.

## Trust boundaries

| Boundary | Trusted side | Untrusted side |
|---|---|---|
| Network | Reverse proxy / localhost | Public internet |
| Authentication | The single Basic Auth user | Everyone else |
| Files | Files under `--dir` | Files outside `--dir` |
| Plugins | Code reviewed and installed by the operator | Code from third parties |
| Plugin dependencies | Packages vendored or installed by the operator | Unreviewed supply chain |
| External tools | LibreOffice, poppler, Edge-TTS | Content they parse or fetch |

## Authentication

- HTTP Basic Auth with one username and one password.
- Credentials are checked with `hmac.compare_digest`.
- There is no session, token, role, permission, or user database.
- Basic Auth is sent in clear text unless TLS is terminated by a reverse
  proxy.
- A missing or invalid credential returns `401`.

## File access

- Only files under the configured `--dir` root are addressed through the
  browser.
- Paths are normalized and checked against the served root.
- Directory traversal with `..`, absolute paths, or malformed names is
  rejected where paths are constructed from request parameters.
- The service account's filesystem permissions are the effective access
  control. If the service can read a file, the authenticated user can read
  it through the browser.
- Symbolic links: reads may follow links according to the service account's
  permissions. Deletion removes the link itself and does not recurse into the
  link target. Editing rejects symbolic links.
- Uploads are written as the service user. There is a total request limit of
  `256 MiB`; there is no extension allowlist or antivirus scan.

Do not serve a directory that contains credentials, private keys, or other
secrets unless you intend the authenticated user to access them. The service
has a preview warning for known sensitive config files, but that is a
convenience, not an access control.

## Text editing

Text editing is a write operation and changes the risk profile of the
service.

- Only files writable by the service account can be edited.
- Unknown extensions are editable only after a conservative text check: no
  NUL bytes, low control-character ratio, and successful decoding.
- Known binary formats are not editable by the built-in text editor.
- The maximum editable text file is `2 MiB`; the maximum edit request body is
  `16 MiB`.
- Saves check `mtime_ns` and `size`. If the file changed after the editor
  opened, the save is rejected with `409`.
- Saves are atomic: a temporary file is written in the same directory and
  replaced with `os.replace()`. File permissions are preserved.
- A backup is written under `cache/edit-backups/` before each save. This is a
  convenience, not a backup system.
- Symbolic links cannot be edited.
- The service account must be able to write to the containing directory for
  atomic replacement, not only to the file.

Editing can destroy data if the operator makes a mistake or an attacker has
the authenticated credentials. Treat edit access as equivalent to write
access for the service account.

## Plugins

Plugins are a first-class feature in this release.

- Plugins are **trusted code** imported into the server process.
- They run with the same permissions as the service account.
- There is no sandbox, seccomp profile, separate process, or capability
  restriction.
- A plugin can read and write files, make network requests, and start
  subprocesses.
- Plugin routes are served under `/plugins/<id>/...` and still require Basic
  Auth.
- Plugin static assets are served from directories inside the plugin
  directory.
- Plugin locale files are merged under `plugin.<id>.*`.
- The loader validates `plugin.json`, checks `api_version`, confines the entry
  path to the plugin directory, and skips a plugin that fails to load.
- `requires` in the manifest is declarative and informational. The loader
  does not install or enforce package versions.

The core provides safe write helpers (`EditContext.write_bytes`) with path
confinement, conflict detection, backups, and atomic replacement. A plugin
that uses those helpers inherits those protections. A malicious or careless
plugin can bypass them because it is trusted code. Only install plugins you
have reviewed.

Plugin dependencies are part of the supply chain. Vendor them deliberately,
review their licenses, and keep them updated.

## Shell endpoint

`POST /cmd` executes arbitrary shell commands in a PTY as the service user.

- There is no command allowlist, sandbox, container, or seccomp profile.
- There is no execution timeout. A client can cancel with `/cmd/cancel`.
- `SIGINT` is sent first, then `SIGKILL` to the process group if needed.
- `FILER_AUTH` and `DL_AUTH` are removed from the child environment, but all
  other service environment variables are inherited.
- Output can reveal files, process information, and environment details.

Treat shell access as equivalent to shell access for the service account.
Do not expose this service to untrusted users.

## Preview and conversion

- Text and Markdown are rendered by filer. User content is escaped where it
  is inserted into HTML; HTML/SVG previews run in a sandboxed iframe or are
  served as raw files.
- `.docx` is parsed in-process for text, tables, and embedded images.
- `.doc`, `.xlsx`, `.pptx`, and `.rtf` are converted by LibreOffice in a
  headless subprocess.
- PDF.js assets and poppler tools are optional and loaded from local files.
- Office/PDF parsing is complex. A malicious document may exploit bugs in
  LibreOffice, poppler, PDF.js, or the browser. Keep these dependencies
  updated and do not preview untrusted documents on a sensitive host.
- A future Office editor plugin will add write access to Office files. Treat
  it with more care than preview: document formats are complex, round-trips
  may be lossy, and a malicious document may target the plugin's parser.

## Article fetching and SSRF

`/read`, `/article/img`, and `/article/tts` fetch remote content. The fetcher
is intended to reduce SSRF risk:

- Only `http` and `https` URLs are accepted.
- Only ports 80 and 443 are accepted.
- Hostnames must resolve to public addresses; private, loopback, link-local,
  reserved, multicast, and unspecified addresses are rejected.
- Redirects are validated again.
- Requests have a timeout and a maximum response size (`8 MiB` by default).
- Article images are proxied only when the response is an image type and the
  size limit is respected.

These controls reduce risk but cannot cover every DNS-rebinding or
proxy-chain scenario. Do not treat the article fetcher as a general-purpose
proxy.

## TTS

- Text-to-speech uses Edge-TTS and an online Microsoft service.
- Extracted file text is sent to the TTS service.
- Generated audio is cached under `cache/tts/`.
- Cached audio may contain sensitive file contents. Protect the cache
  directory with filesystem permissions and clean it when decommissioning a
  host.
- If Edge-TTS is unavailable, the TTS endpoints return `503`; the rest of the
  application continues to work.

## CSRF and browser behavior

- POST endpoints do not implement CSRF tokens. This includes `/edit`, upload,
  delete, and plugin POST routes.
- Basic Auth credentials may be cached by the browser for the origin.
- Do not expose the service to sites or users you do not trust.
- For network deployments, use an HTTPS reverse proxy and restrict access
  with a firewall, VPN, or an additional authentication layer.

## Network deployment

- The default bind address is `127.0.0.1`.
- Public exposure requires an HTTPS reverse proxy (nginx, Caddy, or similar).
- Set `client_max_body_size` at least as high as the upload limit if uploads
  are needed, and at least `16 MiB` for edit requests.
- Disable proxy buffering for streaming endpoints such as TTS and terminal
  output.
- Keep the backend bound to localhost or a private network.

## Logging and audit

- The HTTP server writes access logs to stderr, normally collected by
  systemd/journald.
- Plugin load failures and plugin log messages are written to stderr with the
  plugin id.
- There is no application-level audit log for file access, downloads,
  uploads, edits, deletes, plugin routes, or shell commands.
- Logs may contain file names and request paths. Do not put secrets in file
  names.

## Known gaps

- Single user only; no roles or per-directory permissions.
- No rate limiting or brute-force protection.
- No CSRF tokens.
- No audit log.
- No sandbox for shell commands, document converters, or plugins.
- No built-in TLS.
- No plugin process isolation.
- No antivirus or content scanning for uploads.
- No Office editing in this release.
- No multi-server or clustered session model.

## Deployment checklist

1. Run as a dedicated non-root user.
2. Serve only the intended directory with `--dir`.
3. Keep the credential file mode `600`, owner `root:root`.
4. Bind to `127.0.0.1` and put HTTPS in front.
5. Restrict network access with a firewall or VPN.
6. Give the service write access only to directories that should be edited.
7. Back up the served directory independently of `cache/edit-backups/`.
8. Review every plugin and plugin dependency before installing it.
9. Use `--no-plugins` during incident response if a plugin is suspect.
10. Keep LibreOffice, poppler, Edge-TTS, plugin packages, and the browser
    updated.
11. Protect or clean `cache/` if it may contain sensitive text or audio.
12. Do not enable shell access for untrusted users.
13. Monitor systemd logs and resource usage.
14. Rotate the Basic Auth password if it may have been exposed.

## Reporting vulnerabilities

Please follow [SECURITY.md](../SECURITY.md). Do not open a public issue for a
security problem.
