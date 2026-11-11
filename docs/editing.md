# Editing

filer can edit text files in the browser. Editing is implemented by the
built-in text editor provider and is available unless the file is not
writable or exceeds the configured size limit.

## Where to find the editor

- In a directory listing, use the pencil action on an editable file.
- In a preview page, use the green **Edit** button in the top bar.
- Opening a text or Markdown file directly redirects to its preview page;
  use the **Edit** button there.

The edit button is only shown when the file is writable and an editor
provider can handle it. Read-only files, symbolic links, and files above the
size limit do not show it.

Some extensions (`.txt`, `.csv`, `.json`, `.js`, `.css`, `.map`) are
forced-download types when opened directly. Use the preview or edit action in
the directory listing, or open `/preview?dir=...&name=...` explicitly.

## Supported text formats

The built-in editor handles:

- Documents and notes: `.txt`, `.log`, `.md`, `.markdown`, `.rst`, `.tex`
- Data and configuration: `.csv`, `.tsv`, `.json`, `.xml`, `.yaml`, `.yml`,
  `.toml`, `.ini`, `.conf`, `.cfg`, `.properties`, `.env`
- Source and scripts: `.py`, `.js`, `.mjs`, `.cjs`, `.ts`, `.tsx`, `.jsx`,
  `.css`, `.sh`, `.bash`, `.bat`, `.cmd`, `.ps1`, `.sql`, `.java`, `.c`, `.h`,
  `.cpp`, `.hpp`, `.cs`, `.go`, `.rs`, `.php`, `.rb`, `.pl`, `.lua`, `.r`,
  `.kt`, `.swift`, `.scala`, `.vue`, `.svelte`
- HTML source: `.html`, `.htm`
- Common extensionless files and dotfiles: `Makefile`, `Dockerfile`,
  `README`, `LICENSE`, `CHANGELOG`, `.env`, `.gitignore`, `.gitattributes`,
  `.editorconfig`, `.bashrc`, `.zshrc`, `.npmrc`, `.prettierrc`, and similar
  names

Markdown preview remains rendered Markdown; the editor edits the raw Markdown
source.

## Unknown extensions

For an unknown extension, filer uses a conservative content check:

1. Reject the file if it contains NUL bytes.
2. Detect the encoding using the same rules as preview.
3. Reject the file if it cannot be decoded.
4. Reject the file if more than roughly 1% of characters are control
   characters other than tab, newline, carriage return, or form feed.

Files that fail this check are not offered for editing. Known binary formats
(images, audio, video, archives, PDF, `.docx`, `.xlsx`, `.pptx`, `.doc`,
`.rtf`, and similar) are never treated as text by the built-in editor.

## Encoding, BOM, and line endings

The editor detects the current encoding and displays it in the toolbar. The
detected encoding is used when saving. A user can choose another supported
encoding from the dropdown:

`utf-8`, `gb18030`, `big5`, `shift_jis`, `utf-16-le`, `utf-16-be`,
`utf-32-le`, `utf-32-be`, `cp1252`.

The editor preserves:

- the original BOM when the selected encoding matches the original
  encoding;
- the original line-ending style (`LF`, `CRLF`, or `CR`);
- the original file permissions;
- the original text when the save is rejected.

If the user explicitly selects a different encoding, the file is written in
that encoding. A UTF-8 BOM is added when `utf-8-sig` is selected.

## Limits

| Limit | Default |
|---|---:|
| Maximum editable text file size | `2 MiB` |
| Maximum edit request body | `16 MiB` |
| Backups retained per file | `20` |
| Maximum upload size (unchanged) | `256 MiB` |

Files larger than the text limit are not offered for editing. The preview may
still show the first 2 MiB.

## Backups

Before a successful save, the original file is copied to:

```text
cache/edit-backups/<sha256-of-absolute-path>/<timestamp>-<filename>
```

The newest 20 backups per file are retained. Backups are not a substitute for
a real backup system: `cache/` is a runtime directory and may be deleted.
Protect it with filesystem permissions if the served files contain sensitive
data.

## Conflict handling

The editor page includes the file's `mtime_ns` and `size`. On save, the core
compares them with the current file:

- If they match, the save proceeds.
- If either changed, the save is rejected with HTTP `409` and the submitted
  text remains in the editor so it can be copied or retried.

This prevents one editor tab from silently overwriting changes made by
another process.

## Symbolic links

Symbolic links are not editable. Reads may still follow links depending on
the service account's permissions, but edit actions are hidden and direct
edit requests are rejected. This avoids writing through a link to a path
outside the served root.

## Office documents

This release does **not** include Word or Excel editing. The core previews
Office documents but does not write to them.

Office editing is intended to be delivered as a plugin:

- `.xlsx` with `openpyxl` is the recommended first target.
- `.docx` with `python-docx` can support paragraph and table-cell text editing
  with documented fidelity limits.
- Legacy `.xls` and `.doc` files are not supported for writing in the first
  plugin iteration. They can remain preview-only or require LibreOffice
  conversion with lossy results.

See [writing-a-plugin.md](writing-a-plugin.md) for a concrete implementation
guide. The reserved example path is `examples/plugins/office-editor/`.

## Why editing is not implemented as a separate plugin only

The built-in text editor is a normal provider in the plugin architecture. It
ships in the core because text editing is a baseline file-browser feature,
and it serves as the reference implementation that third-party editors can
copy. External plugins use the same provider contract and the same core write
pipeline.
