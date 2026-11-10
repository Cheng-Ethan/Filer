# pyfilebrowser

A zero-dependency, self-hosted file browser with built-in preview and terminal. One Python file to start — no pip install, no Docker required.

![pyfilebrowser main screenshot](docs/screenshots/main.png)

<!-- TODO: replace docs/screenshots/main.png with the final screenshot. -->

## Why this exists

Sometimes you only need to look at a file on a server, but the available tools assume you want a full remote session. Opening an SSH connection to run `cat`, remember an exact path, and scroll through terminal output is much more work than the task deserves.

This project is intentionally constrained. It uses only the Python standard library: no Flask, no FastAPI, no frontend build step, and no container runtime. Clone the repository, start the process, and browse the files you already have.

## Features

### Core

- Directory browsing with type-aware icons.
- Upload, download, and delete files or directories.
- In-browser preview for Markdown, images, PDF, Office documents, and plain text.
- Automatic text encoding detection for UTF-8, GBK, Big5, and UTF-16.
- Built-in terminal with PTY-backed streaming output.

### Optional

- Text-to-speech reading with Edge-TTS; no API key required.
- Web article fetching and reading, including proxied images.
- Office preview through LibreOffice.

## Quick Start

```bash
git clone https://github.com/<your-name>/pyfilebrowser.git
cd pyfilebrowser
export DL_AUTH='yourname:yourpassword'
python3 dl_server.py --dir /your/path
```

`DL_AUTH` is required and uses the `username:password` format.

## Security

> **Important: read this before exposing the service.**

- HTTP Basic Auth is used. Credentials are transmitted in clear text unless the connection is protected by TLS.
- The server binds to `127.0.0.1` by default and is only reachable from the local machine.
- If you expose it to a network, put it behind an HTTPS reverse proxy such as nginx or Caddy.
- There is currently no multi-user support, no rate limiting, and no audit log.

## Optional Dependencies

- **LibreOffice (`soffice`)** enables preview for `.doc`, `.xlsx`, `.pptx`, and `.rtf` files. If it is missing, the server falls back to text extraction where possible; otherwise the preview may be limited, but the service keeps working.
- **poppler-utils (`pdfinfo`, `pdftoppm`)** enables PDF page inspection and image fallback rendering. If it is missing, PDFs still open with the browser's native viewer or fall back to text extraction.
- **edge-tts** enables text-to-speech. If it is missing, the TTS endpoints report that the feature is unavailable and the rest of the application continues to work.

## Deployment

See [docs/deployment.md](docs/deployment.md) for a systemd unit and reverse-proxy examples.

## Roadmap

- Multi-user support and permissions (Pro)
- Audit logging (Pro)
- Multi-server management (Pro)

## Support

If this project saves you time, please star the repository.

You can also support development at `https://ko-fi.com/<your-name>`.

## License

MIT. See [LICENSE](LICENSE).
