# Development

This guide is for developers working on filer itself. For plugin authors,
see [plugins.md](plugins.md), [plugin-api.md](plugin-api.md), and
[writing-a-plugin.md](writing-a-plugin.md).

## Requirements

- Python 3.10+ (developed and tested on Python 3.10).
- The core server has no third-party Python dependencies.
- Optional features require external tools; see
  [Optional dependencies](#optional-dependencies).

## Repository layout

```text
filer.py                    entry point: argparse + HTTP server + plugin loading
dls/
  handler.py                ForceDownloadHandler composition and routing
  auth.py                   HTTP Basic Auth
  paths.py                  root confinement and filename validation
  files.py                  directory listing, upload, delete, info
  preview.py                preview routing, built-in renderers, provider dispatch
  editor.py                 /edit GET and POST routing
  editors/text.py           built-in text editor provider
  providers.py              provider registry, edit context, atomic writes, backups
  plugins.py                plugin loader, context, request/response, routes/static
  office.py                 Office text extraction / conversion helpers
  cfb.py                    OLE2 compound document parsing
  tts.py                    Edge-TTS integration and audio streaming
  article.py                article fetching, cleanup, image proxy
  shell.py                  PTY command execution and streaming
  templates.py              HTML templates and frontend helpers
  response.py               response helpers and i18n rendering hook
  textenc.py                encoding detection, decoding, BOM/newline helpers
  i18n.py                   locale loading, negotiation, validation, plugin locales
  ui.py                     shared BASE_CSS and font stack
  config.py                 constants, preview type map, edit allowlist and limits
tests/                      unittest suite
docs/                       deployment, API, i18n, plugins, security docs
plugins/                    local plugin directory (loaded by default)
examples/plugins/           example plugins (not loaded by default)
cache/                      runtime caches (ignored)
static/pdfjs/               optional PDF.js assets (ignored)
vendor/                     optional Python dependencies (ignored)
```

See [ARCHITECTURE.md](../ARCHITECTURE.md) for module responsibilities, request
flow, plugin lifecycle, and the write pipeline.

## Running locally

```bash
export FILER_AUTH='admin:test'
python3 filer.py --dir /tmp/files --bind 127.0.0.1 --port 18080
```

Open `http://127.0.0.1:18080/` and log in with `admin:test`.

For a quick temporary directory:

```bash
mkdir -p /tmp/filer-demo
printf 'hello\n' > /tmp/filer-demo/hello.txt
```

Load an example plugin:

```bash
python3 filer.py --dir /tmp/filer-demo \
  --plugins-dir examples/plugins --bind 127.0.0.1 --port 18080
```

## Tests

```bash
python3 -m compileall -q .
python3 -B -m unittest discover -s tests -v
python3 -B -m dls.i18n check
```

The test suite uses temporary directories and an ephemeral local HTTP server.
It should not require network access or real credentials. Editing tests cover
encoding preservation, BOM/newline handling, path traversal, stale-write
conflicts, plugin loading, plugin routes, and plugin editor save flows.

## Optional dependencies

```bash
# Debian/Ubuntu examples
sudo apt install libreoffice poppler-utils

# Edge-TTS as a vendored dependency
pip install --target vendor edge-tts
```

- **LibreOffice** enables `.doc`, `.xlsx`, `.pptx`, and `.rtf` conversion.
- **poppler-utils** enables PDF page counting and page images.
- **edge-tts** enables `/tts` and `/article/tts`.
- **`static/pdfjs/`** enables the PDF.js viewer. If absent, Office PDFs fall
  back to page images or browser-native PDF rendering.
- **Plugin dependencies** such as `openpyxl` or `python-docx` belong to the
  plugin, not the core. Vendor them inside the plugin directory or install
  them in the service environment.

All optional features must degrade gracefully. Do not make core browsing
depend on an optional tool.

## Runtime caches

These directories are created on demand and are safe to delete while the
service is stopped:

```text
cache/tts/
cache/office/
cache/articles/
cache/edit-backups/
```

They may contain file text, audio, PDFs, images, and pre-edit copies of
files. Treat them as sensitive on a multi-user host and protect them with
filesystem permissions. `cache/edit-backups/` is not a replacement for a
real backup system.

## Adding a preview type

Core preview types are still added in code:

1. Add the extension to `_PREVIEW_KINDS` in `dls/config.py`.
2. Handle the new `kind` in `dls/preview.py` (`_serve_preview`).
3. Reuse an existing template or add one in `dls/templates.py`.
4. If the preview needs a new asset or endpoint, add it to
   `dls/handler.py` and document it in [docs/http-api.md](http-api.md).
5. Add tests for the happy path and the fallback/error path.

For third-party formats, prefer a plugin preview provider instead of changing
the core. See [plugin-api.md](plugin-api.md).

## Adding an editor provider

The built-in text editor is the reference implementation in
`dls/editors/text.py`.

1. Create a provider with `matches`, `can_edit`, `render`, and `save`.
2. Use `ctx.write_bytes()` for writes. Do not replace the target file
   directly.
3. Include `dir`, `name`, `mtime_ns`, and `size` hidden fields so stale saves
   are rejected.
4. Raise `EditError` for user-facing errors.
5. Add tests for success, conflict, invalid input, and permission failures.

External editors should be plugins, not core changes.

## Adding an HTTP route

1. Add core routing in `dls/handler.py` (`do_GET` or `do_POST`).
2. Put implementation in the relevant mixin (`files.py`, `preview.py`,
   `editor.py`, `tts.py`, `article.py`, `shell.py`).
3. Use `self._send_html()`/`self._send_json()` so i18n and response headers
   are handled consistently.
4. Add tests and update [docs/http-api.md](http-api.md).

Plugin routes use `ctx.register_route(method, path, handler)` and must be
namespaced under `/plugins/<id>/`.

## Adding a mixin

`ForceDownloadHandler` is assembled from mixins in `dls/handler.py`. A mixin
should:

- Have a narrow responsibility.
- Use response helpers rather than writing headers directly where possible.
- Avoid module-level mutable state unless protected by a lock.
- Degrade gracefully when optional tools are missing.
- Not assume a specific language; use `t()` or `{{i18n:key}}` placeholders.

## Adding a language

Locales are JSON files in `dls/locales/`. See
[docs/i18n.md](i18n.md) for the complete workflow. The key points:

- Copy `en.json` (authoritative source).
- Set `_meta.name`, `_meta.code`, and `_meta.dir`.
- Keep placeholders unchanged.
- Run `python3 -m dls.i18n check` and the test suite.
- Restart the service.

The language selector and locale discovery are automatic. Plugin locales use
the `plugin.<plugin-id>.*` namespace and are loaded from the plugin's
`locales/` directory.

## Plugin development

1. Create a plugin directory under `plugins/` or another configured
   `--plugins-dir`.
2. Add `plugin.json` and `plugin.py`.
3. Implement `register(ctx)` and register providers, routes, static assets,
   or locales.
4. Restart filer. Plugin failures are logged and skipped.
5. Test with `--no-plugins` to confirm the core still works without plugins.

Plugins are trusted code in the server process. There is no sandbox. See
[plugins.md](plugins.md) and [security-model.md](security-model.md).

## Code style

- Public APIs, user-facing text, and documentation are written in English.
- Internal comments may be written in Chinese where it improves clarity.
- Keep the core dependency-free unless a new dependency is clearly
  justified.
- Prefer small, focused changes over broad rewrites.
- Preserve graceful degradation: missing optional tools must not break core
  browsing.
- Plugins must declare their dependencies and must not add them to the core.

## Debugging tips

- Run the server in the foreground to see request and plugin logs on stderr.
- Use `journalctl -u filer.service -n 100 --no-pager` for systemd deployments.
- If previews fail, check service-account read permissions on the file.
- If editing fails, check write permission, file size, symbolic-link status,
  and `cache/edit-backups/` permissions.
- If a save returns `409`, the file changed on disk after the editor opened.
- If Office previews fail, check `soffice`, `pdfinfo`, and `pdftoppm` on
  `PATH`.
- If TTS fails, check `/tts/voices` and the Edge-TTS installation.
- If a plugin is skipped, read the `filer: plugin ... skipped` line on stderr.
- If a locale file is broken, `python3 -m dls.i18n check` reports the exact
  key and problem.

## Release checklist

1. Run `python3 -m compileall -q .`.
2. Run `python3 -B -m unittest discover -s tests -v`.
3. Run `python3 -B -m dls.i18n check`.
4. Bump `__version__` in `dls/__init__.py`.
5. Update the version badge in `README.md`.
6. Move the changelog entries from `[Unreleased]` to the new version in
   [CHANGELOG.md](../CHANGELOG.md) and add comparison links.
7. Verify README and docs links.
8. Verify the example plugin loads and edits a `.todo` file.
9. Confirm `python3 filer.py --version` prints the new version.
10. Tag the release, for example `git tag -a v0.1.0 -m 'filer 0.1.0'`.
