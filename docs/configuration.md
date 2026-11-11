# Configuration

filer is configured with command-line arguments and environment variables.
There is no configuration file loaded at runtime.

## Requirements

- Python 3.10+ (developed and tested on Python 3.10).
- The core server uses only the Python standard library.
- Optional features are provided by external tools or plugins; see
  [Optional dependencies](#optional-dependencies).

## Command-line options

```text
python3 filer.py [--version] [--port PORT] [--dir DIR] [--bind BIND]
                 [--user USER:PASSWORD] [--plugins-dir DIR] [--no-plugins]
```

| Option | Default | Description |
|---|---:|---|
| `--version` | — | Print the filer version and exit. |
| `--port` | `9000` | TCP port to listen on. |
| `--dir` | `.` | Root directory exposed by the file browser. |
| `--bind` | `127.0.0.1` | Bind address. The default is local-only. |
| `--user` | unset | Basic Auth credentials in `username:password` form. Optional if an environment variable is set. |
| `--plugins-dir` | `<repo>/plugins` | Plugin directory. Can be repeated to load multiple directories. |
| `--no-plugins` | off | Disable plugin loading for troubleshooting. |

`--user` is validated after parsing. Both the username and password must be
non-empty. A value without a colon, an empty username, or an empty password
is rejected with an argparse error.

Examples:

```bash
# Local-only, credentials from an environment variable
export FILER_AUTH='admin:change-me'
python3 filer.py --dir /srv/files

# Explicit credentials, local-only
python3 filer.py --dir /srv/files --user 'admin:change-me'

# Load plugins from two directories
python3 filer.py --dir /srv/files \
  --plugins-dir /opt/filer-plugins \
  --plugins-dir ./local-plugins

# Expose to a network only behind an HTTPS reverse proxy
export FILER_AUTH='admin:change-me'
python3 filer.py --dir /srv/files --bind 0.0.0.0 --port 9000
```

## Environment variables

| Variable | Format | Description |
|---|---|---|
| `FILER_AUTH` | `username:password` | Preferred credentials source. |
| `DL_AUTH` | `username:password` | Legacy fallback, still accepted. |

Precedence:

```text
--user  >  FILER_AUTH  >  DL_AUTH
```

If no credentials are supplied, startup fails with an argparse error. The
server never starts with an empty or default password.

The service also removes `FILER_AUTH` and `DL_AUTH` from child process
environments, so shell commands and Office subprocesses cannot see the
credentials via `env`.

## systemd environment file

For systemd deployments, keep credentials out of the unit file:

```bash
sudo install -m 600 /dev/null /etc/filer.env
echo "FILER_AUTH='admin:change-me'" | sudo tee /etc/filer.env >/dev/null
```

```ini
[Service]
EnvironmentFile=/etc/filer.env
ExecStart=/usr/bin/python3 /path/to/filer/filer.py --dir /path/to/files --bind 127.0.0.1 --port 9000
```

The environment file should be owned by `root:root` and mode `600`. systemd
reads it as the service manager before dropping privileges.

## Runtime language selection

Language is not a startup option. At request time the server resolves:

```text
cookie filer_lang  >  query lang  >  Accept-Language  >  en
```

The language selector writes the `filer_lang` cookie, scoped to `/`, with a
one-year lifetime and `SameSite=Lax`. The `lang` query parameter can be used
for one-off requests:

```text
http://127.0.0.1:9000/?lang=zh-CN
```

Supported locales are auto-discovered from `dls/locales/*.json`. See
[docs/i18n.md](i18n.md). Plugin locales are loaded from each plugin's
`locales/` directory under the `plugin.<plugin-id>.*` namespace.

## Paths and writable directories

- Served root: `--dir`.
- Plugin directories: `--plugins-dir`, default `<repo>/plugins/`.
- TTS cache: `cache/tts/`.
- Office cache: `cache/office/`.
- Article cache: `cache/articles/`.
- Edit backups: `cache/edit-backups/`.
- Optional PDF.js assets: `static/pdfjs/`.
- Optional Edge-TTS package: `vendor/`.

The cache directories are created on demand and may be deleted while the
service is stopped. They are not required for startup. `cache/edit-backups/`
contains pre-edit copies of files and should be protected like the served
files.

## Editing limits

| Setting | Value | Notes |
|---|---:|---|
| Maximum editable text file | `2 MiB` | Controlled by `_MAX_EDIT_BYTES` in `dls/config.py`. |
| Maximum edit request body | `16 MiB` | Controlled by `MAX_EDIT_REQUEST_BYTES`. |
| Backups per file | `20` | Controlled by `MAX_EDIT_BACKUPS`. |
| Maximum upload | `256 MiB` | Unchanged from upload behavior. |

These are code constants in this release, not CLI options. Plugins may apply
their own smaller format-specific limits.

Editing is refused when:

- the file is not writable by the service user;
- the file is a symbolic link;
- the file exceeds the text limit;
- the unknown-extension content check fails;
- the file changed on disk after the editor was opened (`409` conflict).

## Plugins

Plugins are trusted Python code loaded at startup. Each plugin directory
contains `plugin.json` and an entry file. Plugin routes and static assets are
namespaced under `/plugins/<plugin-id>/...`.

A plugin load failure is logged to stderr and skipped. Use `--no-plugins` to
disable all plugins during incident response.

See [docs/plugins.md](plugins.md), [docs/plugin-api.md](plugin-api.md), and
[docs/writing-a-plugin.md](writing-a-plugin.md).

## Optional dependencies

| Dependency | Enables | If missing |
|---|---|---|
| `libreoffice` / `soffice` | `.doc`, `.xlsx`, `.pptx`, `.rtf` preview via PDF | Falls back to text extraction; service keeps working. |
| `poppler-utils` (`pdfinfo`, `pdftoppm`) | PDF page counting and page images | Falls back to browser-native PDF or text extraction. |
| `edge-tts` | `/tts` and `/article/tts` | TTS endpoints return `503`; the rest of the app works. |
| `static/pdfjs/` | PDF.js viewer | Falls back to page images or browser-native PDF. |
| Plugin packages | Format-specific preview or editing | Plugin reports failure or is skipped; core keeps working. |

`static/pdfjs/` and `vendor/` are not tracked by this repository. Install them
from their upstream projects if you need those features.

Office editing is not included. A future `office-editor` plugin may require
`openpyxl` and/or `python-docx`; those packages belong to the plugin and are
not core dependencies.

## `config.example.json`

`config.example.json` is an illustrative example only. The current server
does **not** read it at runtime. Use command-line arguments and environment
variables for actual configuration. If a runtime config file is added later,
this document should be updated with its precedence rules.

## Security summary

- The default bind address is `127.0.0.1`.
- HTTP Basic Auth is clear text without TLS.
- The server is single-user and has no rate limiting or audit log.
- The shell endpoint executes arbitrary commands as the service user.
- Plugins are trusted code with no sandbox.
- Text editing can overwrite files; backups live in `cache/edit-backups/`.
- Do not expose the service directly to the public internet.

See [docs/security-model.md](security-model.md) and
[docs/deployment.md](deployment.md) for deployment guidance.
