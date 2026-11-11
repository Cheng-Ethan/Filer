# Plugins

**Status: implemented in this release for preview providers, editor
providers, namespaced routes, static assets, and plugin locales. Office
editing is not included.**

filer has a small, trusted plugin system. The goal is to let developers add
file formats and small features without patching the core, while keeping the
core standard-library-only and preserving the single-user security model.

## What plugins can do

| Extension point | API | Since |
|---|---|---|
| Preview a file format | `ctx.register_preview(provider)` | `api_version: 1` |
| Edit a file format | `ctx.register_editor(provider)` | `api_version: 1` |
| Add a namespaced HTTP route | `ctx.register_route(method, path, handler)` | `api_version: 1` |
| Serve namespaced static files | `ctx.register_static(prefix, directory)` | `api_version: 1` |
| Add translations | `ctx.register_locale(directory)` | `api_version: 1` |

The following are **not** implemented yet:

- list or toolbar action registration;
- upload/delete hooks;
- article parser or TTS provider registration;
- authentication or storage backends;
- hot reload;
- sandboxing;
- automatic plugin installation or download.

## Installation

The default plugin directory is `plugins/` next to `filer.py`:

```text
plugins/
  todo-editor/
    plugin.json
    plugin.py
    locales/
      en.json
      zh-CN.json
```

Start filer normally. Plugins are loaded once at startup:

```bash
python3 filer.py --dir /srv/files
```

Load plugins from one or more other directories:

```bash
python3 filer.py --dir /srv/files \
  --plugins-dir /opt/filer-plugins \
  --plugins-dir ./local-plugins
```

Disable plugin loading for troubleshooting:

```bash
python3 filer.py --dir /srv/files --no-plugins
```

A broken plugin is logged to stderr and skipped. It does not prevent the core
from starting.

## Trust model

Plugins are **trusted code**. They are imported into the server process and
run with the service account's permissions.

- There is no sandbox, seccomp profile, or separate process.
- A plugin can read and write the same files as the service user.
- A plugin can make network requests and start subprocesses.
- A plugin can serve its own HTTP routes under `/plugins/<id>/...`.
- Only install plugins whose code you have reviewed.
- The core does not download or install plugins automatically.

The core still owns path validation and the write pipeline. Plugins that use
the provided APIs get root confinement, conflict detection, backups, atomic
replacement, and permission preservation. A malicious plugin can bypass
those APIs because it is trusted code; that is why plugins must be reviewed.

See [security-model.md](security-model.md) for the full threat model.

## Plugin lifecycle

```mermaid
flowchart TD
    A[filer starts] --> B[Scan plugin directories]
    B --> C{plugin.json exists?}
    C -->|no| D[Ignore directory]
    C -->|yes| E[Validate manifest]
    E -->|invalid| F[Log and skip]
    E -->|valid| G{api_version == 1 and enabled?}
    G -->|no| F
    G -->|yes| H[Add plugin dir + vendor/ to sys.path]
    H --> I[Import entry module]
    I -->|failure| F
    I --> J[Call register(ctx)]
    J -->|failure| F
    J --> K[Providers/routes/static/locales registered]
    K --> L[Core continues startup]
    F --> L
```

## Manifest

Every plugin needs `plugin.json`:

```json
{
  "id": "todo-editor",
  "name": "Todo editor",
  "version": "0.1.0",
  "api_version": 1,
  "entry": "plugin.py",
  "enabled": true,
  "requires": {
    "python": ">=3.10",
    "packages": []
  }
}
```

Required fields:

- `id`: stable identifier matching `[A-Za-z0-9_.-]+`.
- `api_version`: must equal `1` in this release.
- `entry`: Python file inside the plugin directory. Defaults to `plugin.py`.

Optional fields:

- `name`, `version`, `enabled`, `requires`.

`requires` is declarative and informational in this release. The loader does
not install packages or enforce version constraints. Vendor plugin
dependencies inside the plugin directory or install them in the service
environment.

## Entry point

`plugin.py` must define `register(ctx)`:

```python
def register(ctx):
    ctx.register_editor(MyEditor())
    ctx.register_locale(os.path.join(ctx.dir, "locales"))
```

`ctx` exposes:

- `ctx.id`: plugin id
- `ctx.dir`: absolute plugin directory
- `ctx.manifest`: parsed manifest
- `ctx.version`: plugin version
- `ctx.api_version`: core API version (`1`)
- `ctx.t(key, **kwargs)`: translate a key
- `ctx.log(message)`: write a message to stderr with the plugin id
- `ctx.register_editor(provider)`
- `ctx.register_preview(provider)`
- `ctx.register_route(method, path, handler)`
- `ctx.register_static(prefix, directory)`
- `ctx.register_locale(directory)`

See [plugin-api.md](plugin-api.md) for exact signatures.

## Example plugin

[`examples/plugins/todo-editor`](../examples/plugins/todo-editor) is a
working plugin that edits `.todo` files as a checkbox list. It demonstrates:

- a manifest and `register(ctx)` entry point;
- an editor provider;
- plugin locale registration;
- safe writes through the core.

Install it locally to try it:

```bash
cp -r examples/plugins/todo-editor plugins/todo-editor
python3 filer.py --dir /tmp/files
```

## Routes and static assets

Plugin routes must be namespaced:

```text
/plugins/<plugin-id>/...
```

Static prefixes must be namespaced and point inside the plugin directory:

```text
/plugins/<plugin-id>/static/...
```

The core applies Basic Auth before calling a plugin route.

Route handlers receive a `PluginRequest` and return a `PluginResponse` (or a
string, bytes, dict, or list that the core converts). See
[plugin-api.md](plugin-api.md).

## Locales

Plugin locale files are merged under the `plugin.<plugin-id>.*` namespace:

```text
plugins/todo-editor/locales/en.json
```

```json
{
  "title": "Todo editor",
  "save": "Save todo list"
}
```

Keys become `plugin.todo-editor.title` and `plugin.todo-editor.save`. The
current locale and the English fallback are both merged.

## Versioning

- `api_version` is a hard compatibility gate.
- This release supports `api_version: 1`.
- Additive API changes may keep the same version.
- Removing or changing an existing API requires a new `api_version`.
- Plugins load at startup; restart the process after installing or updating
  a plugin.

## Office editing roadmap

This release does not include Word or Excel editing. The recommended path is
a third-party plugin under `examples/plugins/office-editor/`:

1. `.xlsx` editing with `openpyxl`.
2. `.docx` text-level editing with `python-docx`.
3. Legacy `.xls` / `.doc` remain preview-only initially.

See [writing-a-plugin.md](writing-a-plugin.md) for the design and
implementation guide.

## Contributing a plugin

- Keep plugin dependencies out of the core.
- Declare dependencies in `plugin.json` and document installation.
- Use the core write APIs rather than writing files directly.
- Add tests for happy paths and failure paths.
- Document format limitations and data-loss risks.
- Follow [SECURITY.md](../SECURITY.md) for security issues.
