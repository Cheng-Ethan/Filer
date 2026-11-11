# HTTP API

filer is a single-user HTTP file browser. All endpoints require HTTP Basic
Authentication. This document describes the routes implemented by the
current code; it is intended for developers extending the server or writing
integrations.

Base URL in the examples:

```text
http://127.0.0.1:9000
```

Replace credentials as needed:

```bash
curl -u 'admin:secret' http://127.0.0.1:9000/
```

## Authentication

- Every route requires `Authorization: Basic ...`.
- Missing or invalid credentials return `401` with `WWW-Authenticate: Basic`.
- There is no session, token, role, or per-directory permission model.
- Basic Auth is clear text unless TLS is terminated by a reverse proxy.

## Status codes

| Code | Meaning |
|---:|---|
| 200 | Success |
| 204 | Plugin route returned no content |
| 206 | Partial content (TTS audio with `Range`) |
| 301 | Directory redirect to a trailing slash |
| 302 | Editable/preview file opened directly; redirect to `/preview` |
| 303 | Successful form action; redirect back to the directory or preview |
| 400 | Bad request, bad filename, or missing parameter |
| 401 | Authentication required |
| 403 | Path outside the served root, permission denied, or editing not allowed |
| 404 | File or route not found |
| 409 | Edit conflict: the file changed on disk after the editor opened |
| 413 | Edit or media payload too large |
| 415 | File cannot be edited as text, or unsupported media type |
| 416 | Invalid TTS audio `Range` |
| 500 | Plugin or internal error |
| 503 | Optional service unavailable (for example TTS or Office conversion) |

Error bodies are usually HTML for browser routes and JSON for API routes.
Unless stated otherwise, JSON errors have this shape:

```json
{ "ok": false, "error": "message" }
```

## Routes

### `GET /`

Directory listing for the current path.

- `GET /path/` lists a directory.
- `GET /path/file` redirects to `/preview` for text, Markdown, and Office
  formats so the preview page's own toolbar is used.
- `GET /path/file` renders an inline wrapper for media formats that need the
  outer file toolbar.
- `GET /path/file?dl=1` forces a download.
- `.txt`, `.csv`, `.json`, `.js`, `.css`, and `.map` are forced-download
  types when opened directly. Use `/preview` or the listing's edit action to
  edit them.
- `GET /path/file?raw=1` bypasses the wrapper and serves the raw file.
- `GET /path` for a directory redirects to `/path/` with `301`.
- `GET /path/file` for `.html`/`.htm` serves the file directly without the
  file-browser toolbar.

### `GET /preview`

Renders a preview page for one file.

| Parameter | Required | Meaning |
|---|---|---|
| `dir` | no | Directory containing the file. Default `/`. |
| `name` | yes | File name. Must not contain `/`, `\`, `.` or `..`. |
| `enc` | no | Text encoding override. One of `utf-8`, `gb18030`, `big5`, `shift_jis`, `utf-16-le`, `utf-16-be`, `utf-32-le`, `utf-32-be`, `cp1252`. |

Example:

```bash
curl -u 'admin:secret' \
  'http://127.0.0.1:9000/preview?dir=%2Fdocs&name=README.md'
```

Preview behavior depends on the file type:

- A registered plugin preview provider is checked first.
- Markdown is rendered to HTML.
- Text is decoded with encoding detection and can be overridden.
- `.docx` is rendered as HTML with images and tables.
- `.doc`, `.xlsx`, `.pptx`, and `.rtf` use LibreOffice and PDF.js/page images.
- PDF, images, audio, video, SVG, and HTML use browser-native renderers or
  sandboxed previews.
- Unsupported types return a preview message page.

If the file is editable, the preview page includes an edit action.

### `GET /edit`

Renders the editor page for one file.

| Parameter | Required | Meaning |
|---|---|---|
| `dir` | no | Directory containing the file. Default `/`. |
| `name` | yes | File name. Must not contain `/`, `\`, `.` or `..`. |

The editor is selected from the provider registry. The built-in text editor
handles text formats. A plugin editor handles its registered extensions.

The page includes the file name, a link back to the preview, a download link,
and the provider's editor form.

Editing is refused when the file is not writable, is a symbolic link, exceeds
the text limit, or fails the text-content check.

### `POST /edit`

Saves an edited file.

The body is `application/x-www-form-urlencoded` by default. Plugins may also
accept `multipart/form-data`.

Common fields used by the built-in text editor:

| Form field | Required | Meaning |
|---|---|---|
| `dir` | yes | Directory containing the file. |
| `name` | yes | File name. |
| `text` | yes | Full new file text. |
| `enc` | no | Desired encoding. Defaults to the detected encoding. |
| `mtime_ns` | yes | File modification time when the editor opened. |
| `size` | yes | File size when the editor opened. |

Behavior:

- On success, returns `303` to the preview page.
- If `mtime_ns` or `size` no longer matches, returns `409` and keeps the
  submitted content in the editor.
- If the new content exceeds the text limit, returns `413`.
- If the file cannot be treated as text, returns `415`.
- If the file is a symbolic link or not writable, returns `403`.
- A backup of the original is written under `cache/edit-backups/` before a
  successful replacement.

Example:

```bash
curl -u 'admin:secret' -X POST \
  --data-urlencode 'dir=/' \
  --data-urlencode 'name=notes.txt' \
  --data-urlencode 'text=hello' \
  --data-urlencode 'enc=utf-8' \
  --data-urlencode 'mtime_ns=1700000000000000000' \
  --data-urlencode 'size=5' \
  'http://127.0.0.1:9000/edit'
```

`mtime_ns` and `size` must match the current file or the save is rejected.
Read them from `GET /edit`, `GET /info`, or `stat` before posting.

### `GET /info`

Returns file or directory metadata as JSON.

| Parameter | Required | Meaning |
|---|---|---|
| `dir` | no | Directory containing the entry. Default `/`. |
| `name` | yes | File or directory name. |

Example response:

```json
{
  "ok": true,
  "name": "README.md",
  "dir": "/",
  "type": "File (MD)",
  "is_dir": false,
  "size": 1234,
  "size_human": "1.2 KB",
  "mtime": "2026-01-01 09:00:00",
  "ctime": "2026-01-01 09:00:00",
  "perm": "0644",
  "perm_str": "rw-r--r--",
  "readable": true,
  "writable": false
}
```

`perm` is an octal permission string; `perm_str` is the symbolic form.

### `POST /upload`

Multipart upload into the current directory.

| Form field | Required | Meaning |
|---|---|---|
| `dir` | yes | Target directory, relative to the served root. |
| `file` | yes | One or more uploaded files. |

The maximum upload size is `256 MiB` per request. Files are written into the
target directory as the service user. There is no extension filtering.

Successful uploads redirect back with `303`.

### `POST /delete`

Deletes a file, empty directory, or non-empty directory.

| Form field | Required | Meaning |
|---|---|---|
| `dir` | yes | Directory containing the entry. |
| `name` | yes | File or directory name. |

Successful deletes redirect back with `303`. Deleting a non-empty directory
recursively removes its contents. Symbolic links are removed as links; the
link target is not followed during deletion.

### `POST /cmd`

Runs a shell command in a PTY as the service user.

Request body: JSON.

| Field | Required | Meaning |
|---|---|---|
| `cmd` | yes | Command line. Executed with the system shell. |
| `dir` | no | Working directory relative to the served root. |
| `stream` | no | If truthy, return chunked streaming output. |
| `id` | no | Client-generated task id used by `/cmd/cancel`. |

Non-streaming response:

```json
{ "code": 0, "out": "command output\n" }
```

Streaming response: `200` with `Transfer-Encoding: chunked`; chunks contain
the command output. The stream ends with a zero-length chunk.

`cd`, `go`, and `jump` are handled specially and return a JSON response with
a `nav` field for the new directory.

There is no execution timeout. The client can cancel with `/cmd/cancel`.

### `POST /cmd/cancel`

Cancels a running `/cmd` task.

```json
{ "id": "task-id" }
```

The server sends `SIGINT` to the process group first, then `SIGKILL` after a
short delay if the process is still alive.

Response:

```json
{ "ok": true, "cancelled": true }
```

### `GET /tts/voices`

Returns available Edge-TTS voices as JSON.

```json
{
  "ok": true,
  "default": "zh-CN-XiaoxiaoNeural",
  "voices": [
    { "id": "zh-CN-XiaoxiaoNeural", "name": "Xiaoxiao", "locale": "zh-CN", "gender": "Female" }
  ]
}
```

If Edge-TTS is unavailable, returns `503`.

### `GET /tts`

Streams synthesized MP3 audio for a file.

| Parameter | Required | Meaning |
|---|---|---|
| `dir` | no | Directory containing the file. Default `/`. |
| `name` | yes | File name. |
| `voice` | no | Edge-TTS voice id. |
| `rate` | no | Speech rate, clamped to `0.5`–`2.0`. |
| `status` | no | If present, return JSON synthesis status instead of audio. |

The response is `audio/mpeg`, generated incrementally. Completed audio is
cached under `cache/tts/`. Cached files support `Range` requests and `206`
responses. The first request for new text may take a few seconds while the
first Edge-TTS chunk is generated.

### `GET /read`

Article reader form, or article fetching when `url` is present.

| Parameter | Required | Meaning |
|---|---|---|
| `url` | no | Article URL. Without it, renders the input form. |

Fetches public `http`/`https` pages only, on ports 80/443, with SSRF
protections. The result is cleaned HTML with proxied images.

### `GET /article/img`

Image proxy for article reading.

| Parameter | Required | Meaning |
|---|---|---|
| `u` | yes | Public image URL. |

Only image content types are returned, with a maximum response size of
`8 MiB`.

### `GET /article/tts`

Streams synthesized audio for an article.

| Parameter | Required | Meaning |
|---|---|---|
| `url` | yes | Article URL. |
| `voice` | no | Edge-TTS voice id. |
| `rate` | no | Speech rate, clamped to `0.5`–`2.0`. |
| `status` | no | If present, return JSON synthesis status. |

Shares the Edge-TTS engine, pronunciation dictionary, and cache with `/tts`.

### `GET /officepdf`

Returns a converted PDF for an Office file.

| Parameter | Required | Meaning |
|---|---|---|
| `dir` | no | Directory containing the file. |
| `name` | yes | Office file name. |

Uses LibreOffice and caches converted PDFs under `cache/office/`.

### `GET /officepage`

Returns one Office PDF page as a JPEG image.

| Parameter | Required | Meaning |
|---|---|---|
| `dir` | no | Directory containing the file. |
| `name` | yes | Office file name. |
| `page` | no | 1-based page number. Default `1`. |

Uses `pdftoppm` and caches page images under `cache/office/`.

### `GET /docmedia`

Returns an embedded image from a `.docx`.

| Parameter | Required | Meaning |
|---|---|---|
| `dir` | no | Directory containing the file. |
| `name` | yes | `.docx` file name. |
| `part` | yes | ZIP part name, for example `word/media/image1.png`. |

### `GET /pdfjs/*`

Serves files from `static/pdfjs/` for the PDF.js viewer. If PDF.js is not
installed, this route returns `404`; the application falls back to page
images or browser-native PDF rendering.

## Plugin routes

Plugins can register exact GET or POST routes:

```text
/plugins/<plugin-id>/...
```

Rules:

- `GET` and `POST` are supported.
- The path is matched without the query string.
- Basic Auth is checked before the plugin handler runs.
- The path must start with `/plugins/<plugin-id>/`.
- Duplicate routes cause the plugin to fail loading.
- Plugin static files are served under a registered prefix such as
  `/plugins/<plugin-id>/static/...`.
- Static files must resolve inside the plugin directory.

Plugin route handlers return a `PluginResponse` or a value that the core
converts. See [plugin-api.md](plugin-api.md).

## Developer notes

- Query and form values use `urllib.parse`. Decode first, then quote once.
- File paths are constrained to the configured `--dir` root.
- The server is single-user. There is no authorization layer beyond Basic
  Auth.
- The shell endpoint executes arbitrary commands as the service user. Do not
  expose it to untrusted users.
- JSON routes return `Cache-Control: no-store`.
- When adding a core route, update `dls/handler.py` and this document.
- When adding a plugin route, use `ctx.register_route()` and document it in
  the plugin's README.
