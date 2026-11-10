# Architecture

## Modules

| Module | Responsibility |
| --- | --- |
| `config.py` | Shared constants and preview type mappings. |
| `auth.py` | HTTP Basic authentication. |
| `textenc.py` | Text encoding detection and decoding. |
| `templates.py` | HTML templates, icons, and embedded frontend helpers. |
| `files.py` | Directory listing, upload, delete, file info, and forced downloads. |
| `preview.py` | Preview rendering and inline file browsing. |
| `office.py` | Office document text extraction and conversion helpers. |
| `cfb.py` | OLE2 compound document parsing. |
| `shell.py` | Web terminal command execution, PTY handling, and streaming output. |
| `tts.py` | Text-to-speech synthesis and pronunciation dictionary handling. |
| `article.py` | Web article fetching, cleanup, and image proxying. |
| `response.py` | HTTP response helpers. |
| `util.py` | Size and formatting utilities. |
| `handler.py` | Mixin composition for the HTTP request handler. |

## Development Commands

```bash
python3 -m compileall -q .
python3 -m unittest discover -s tests
```

## Encoding Design

The project does not depend on `chardet` or another third-party detector. Detection is deterministic and cheap:

1. Check byte-order marks first (UTF-8, UTF-16, UTF-32).
2. Use a null-byte heuristic for UTF-16 without a BOM; reject binary data that contains null bytes.
3. Try strict decoding in a fixed order: UTF-8, GB18030, Big5, Shift_JIS.
4. If decoding fails only at the end of the buffer, keep the candidate.
5. Let the user override the detected encoding in the preview interface.

This keeps behavior predictable across machines and avoids shipping a large detection dependency.
