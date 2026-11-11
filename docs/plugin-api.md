# Plugin API

This document is the developer reference for `api_version: 1`. It describes
the API implemented by this release. See [plugins.md](plugins.md) for
installation and trust model, and [writing-a-plugin.md](writing-a-plugin.md)
for a tutorial.

## Import surface

Plugins may import:

```python
from dls.providers import (
    EditContext, EditError, EditConflict, EditorPage, EditorProvider,
    PreviewProvider, ProviderRegistry, SaveResult,
)
from dls.plugins import PluginResponse
```

Plugins are trusted Python code and technically can import anything. The
imports above are the supported API surface.

## Manifest

`plugin.json`:

```json
{
  "id": "example.editor",
  "name": "Example editor",
  "version": "1.0.0",
  "api_version": 1,
  "entry": "plugin.py",
  "enabled": true,
  "requires": {
    "python": ">=3.10",
    "packages": ["openpyxl>=3.1"]
  }
}
```

| Field | Required | Meaning |
|---|---|---|
| `id` | recommended | Must match `[A-Za-z0-9_.-]+`. Defaults to the directory name. |
| `api_version` | yes | Must equal `1`. |
| `entry` | no | Python file inside the plugin directory. Defaults to `plugin.py`. |
| `enabled` | no | Defaults to `true`. Set to `false` to skip loading. |
| `name`, `version` | no | Informational. |
| `requires` | no | Declarative only. The loader does not install or enforce packages. |

The entry file must define `register(ctx)`.

## PluginContext

```python
def register(ctx):
    ...
```

| Member | Meaning |
|---|---|
| `ctx.id` | Plugin id. |
| `ctx.dir` | Absolute plugin directory. |
| `ctx.manifest` | Parsed manifest dictionary. |
| `ctx.version` | Manifest version string. |
| `ctx.api_version` | Always `1` in this release. |
| `ctx.t(key, **kwargs)` | Translate a key for the current request language. |
| `ctx.log(message)` | Write `filer: plugin <id>: <message>` to stderr. |
| `ctx.register_editor(provider)` | Register an `EditorProvider`. |
| `ctx.register_preview(provider)` | Register a `PreviewProvider`. |
| `ctx.register_route(method, path, handler)` | Register a GET or POST route. |
| `ctx.register_static(prefix, directory)` | Serve static files under a prefix. |
| `ctx.register_locale(directory)` | Merge JSON locale files under `plugin.<id>.*`. |

### `register_editor`

```python
ctx.register_editor(provider)
```

The provider is inserted into the global registry by descending `priority`.
The core text editor has priority `-100`. A plugin can override it by using a
higher priority and matching the same files.

Provider ids are prefixed with the plugin id, for example
`todo-editor:todo`.

### `register_preview`

```python
ctx.register_preview(provider)
```

Preview providers are checked before the built-in preview renderer. A
matching provider must return a complete HTML page as a string.

### `register_route`

```python
ctx.register_route("GET", "/plugins/my-plugin/status", handler)
```

Rules:

- Method must be `GET` or `POST`.
- Path must start with `/plugins/<plugin-id>/`.
- The path is matched exactly, without the query string.
- Basic Auth is checked by the core before the handler runs.
- Registering the same method and path twice raises an error and the plugin
  fails to load.

The handler signature is:

```python
def handler(request: PluginRequest) -> PluginResponse | str | bytes | dict | list | None
```

### `register_static`

```python
ctx.register_static("/plugins/my-plugin/static", os.path.join(ctx.dir, "static"))
```

Rules:

- Prefix must start with `/plugins/<plugin-id>/`.
- The directory must resolve inside the plugin directory.
- Requests are served with a content type based on the file extension.
- Directory traversal is rejected.

### `register_locale`

```python
ctx.register_locale(os.path.join(ctx.dir, "locales"))
```

Each `*.json` file is loaded and flattened. Keys are prefixed with
`plugin.<plugin-id>.` and merged for the current language and English
fallback.

Example `locales/en.json`:

```json
{
  "title": "Example editor",
  "save": "Save"
}
```

Use `ctx.t("plugin.example.editor.title")` after registration.

## EditorProvider

```python
class MyEditor(EditorProvider):
    id = "my-editor"
    priority = 100

    def matches(self, name, path):
        return name.endswith(".myext")

    def can_edit(self, path):
        return os.access(path, os.W_OK)

    def render(self, ctx):
        return EditorPage(body="<form ...>...</form>")

    def save(self, ctx, files=None):
        ctx.write_bytes(b"...")
        return SaveResult()
```

| Method | Meaning |
|---|---|
| `matches(name, path)` | Return `True` if this provider handles the file. Exceptions are treated as no match. |
| `can_edit(path)` | Return `True` if the edit action should be shown and saving is allowed. Called before rendering and before saving. |
| `render(ctx)` | Return an `EditorPage`. The body is inserted into the core edit page. |
| `save(ctx, files=None)` | Validate the submitted form, call `ctx.write_bytes()`, and return `SaveResult` or `None`. |

`EditorPage`:

```python
EditorPage(body="<form ...>...</form>", head="<style>...</style>")
```

- `body` is placed in the core edit wrapper.
- `head` is inserted into the edit page `<head>` after the core styles. Use
  it for provider-specific `<style>` or `<script>` blocks.

`SaveResult`:

```python
SaveResult(redirect="", message="")
```

- `redirect` overrides the default redirect to the preview page. It must be a
  local path.
- `message` is currently reserved.

If `save` returns `None`, the core redirects to the preview page.

### Form fields and conflict detection

The core edit page posts to `/edit`. For the built-in text editor, the form
contains `dir`, `name`, `text`, `enc`, `mtime_ns`, and `size`.

Plugins should include `dir`, `name`, `mtime_ns`, and `size` hidden fields so
the core can reject stale saves. `ctx.form` contains the submitted fields.

On a conflict, `ctx.write_bytes()` raises `EditConflict`, which becomes an
HTTP `409` response. The core calls `provider.render(ctx)` again so the
submitted content can be preserved in the editor.

### Errors

Raise `EditError` for user-facing errors:

```python
from dls.providers import EditError

raise EditError("edit.too_large", status=413)
```

The key is translated with the current locale. `status` is used for the HTTP
response. `EditConflict` is a subclass with status `409`.

## PreviewProvider

```python
class MyPreview(PreviewProvider):
    id = "my-preview"
    priority = 100

    def matches(self, name, path):
        return name.endswith(".myext")

    def render(self, ctx):
        return "<!DOCTYPE html><html>...</html>"
```

`render` returns a complete HTML page. The core sends it after language
resolution, so `{{i18n:key}}` placeholders are replaced and `window.I18N` is
injected.

The context is the same `EditContext` object. Use `ctx.read_bytes()`,
`ctx.path`, `ctx.name`, `ctx.target`, and `ctx.t()`.

## EditContext

`EditContext` is created per request by the core.

| Member | Meaning |
|---|---|
| `ctx.name` | File name. |
| `ctx.target` | Directory parameter as requested, for example `/docs`. |
| `ctx.target_dir` | Absolute directory path. |
| `ctx.path` | Absolute file path after root validation. |
| `ctx.base` | Absolute served root. |
| `ctx.form` | Submitted form fields (empty for GET). |
| `ctx.t(key, **kwargs)` | Translate a key. |
| `ctx.read_bytes(limit=None)` | Read the file. If `limit` is set, reads at most `limit + 1` bytes. |
| `ctx.current_stat()` | `os.stat()` of the file. |
| `ctx.check_conflict()` | Raise `EditConflict` if `mtime_ns` or `size` from the form no longer match. |
| `ctx.write_bytes(data, backup=True)` | Check conflict, back up, write atomically, preserve permissions. |

`ctx.write_bytes()` is the supported write path. It rejects symbolic links
and writes a temporary file in the same directory before `os.replace()`.

## PluginRequest

Routes receive a request wrapper instead of the raw HTTP handler.

| Member | Meaning |
|---|---|
| `request.method` | `GET` or `POST`. |
| `request.path` | Path without the query string. |
| `request.query` | Parsed query dictionary. |
| `request.headers` | Request headers. |
| `request.body(limit=...)` | Read the raw body. |
| `request.json(limit=...)` | Parse JSON, or return `None`. |
| `request.form(limit=...)` | Parse URL-encoded or multipart form fields. |
| `request.files(limit=...)` | Uploaded file contents from a multipart form. |
| `request.resolve_file(dir_param, name)` | Return `(target_dir, full_path)` after root validation. |
| `request.read_file(dir_param, name, limit=...)` | Read a served file. |
| `request.write_file(dir_param, name, data, expected_mtime=None, expected_size=None)` | Safe atomic write through the core. |

Only read or write files that the authenticated operator is allowed to
access. The plugin is trusted; the core still enforces root confinement.

## PluginResponse

```python
from dls.plugins import PluginResponse

return PluginResponse(
    body=b"ok",
    status=200,
    content_type="text/plain; charset=utf-8",
    headers={"X-Example": "1"},
)
```

The core adds `Cache-Control: no-store` and `Content-Length`. A returned
`dict` or `list` becomes JSON. A returned `str` becomes HTML. A returned
`bytes` becomes `application/octet-stream`.

Returning `None` sends `204 No Content`.

## Failure isolation

The loader catches exceptions from:

- manifest parsing and validation;
- entry import;
- `register(ctx)`;
- individual route handlers (the route returns `500`).

A load failure writes a line to stderr and skips that plugin. The core keeps
running. Runtime exceptions from providers are caught where the core calls
them, but a plugin can still crash the process with a fatal error because it
runs in-process. Treat plugins as trusted code.

## Compatibility rules

- `api_version` is a hard gate.
- Additive changes may keep version `1`.
- Removing or changing an API requires a new `api_version`.
- `requires` is not enforced in this release.
- No hot reload. Restart after changes.

## Not implemented

- list and toolbar actions;
- upload/delete hooks;
- article parser and TTS provider registries;
- theme packs;
- auth or storage backends;
- plugin marketplace or automatic installation;
- sandbox or process isolation.
