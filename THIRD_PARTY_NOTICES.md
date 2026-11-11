# Third-Party Notices

filer itself is licensed under the MIT License. See [LICENSE](LICENSE).

The core server uses only the Python standard library. Optional features and
plugins rely on external tools or packages that are **not bundled** with the
core repository. If you install or redistribute them, review and comply with
their upstream licenses.

## Python

- Component: Python standard library
- License: Python Software Foundation License
- Notes: Provided by the Python interpreter, not bundled here.

## LibreOffice

- Component: LibreOffice / `soffice`
- Used for: converting `.doc`, `.xlsx`, `.pptx`, and `.rtf` files to PDF
- License: Mozilla Public License 2.0 (MPL-2.0); some components may carry
  other compatible licenses. Check the upstream distribution.
- Notes: Optional. Not bundled.

## poppler-utils

- Component: poppler-utils (`pdfinfo`, `pdftoppm`)
- Used for: PDF page counting and page image rendering
- License: GPL-2.0-or-later (check the upstream package for your
  distribution)
- Notes: Optional. Not bundled.

## edge-tts

- Component: edge-tts Python package
- Used for: text-to-speech via Microsoft Edge's online service
- License: GPL-3.0 (check the upstream package)
- Notes: Optional. Not bundled. The `vendor/` directory is intentionally
  excluded from this repository. Use of the online service is also subject
  to the service provider's terms.

## PDF.js

- Component: PDF.js viewer assets under `static/pdfjs/`
- Used for: displaying converted Office PDFs
- License: Apache License 2.0
- Notes: Optional. `static/pdfjs/` is intentionally excluded from this
  repository.

## python-docx

- Component: `python-docx`
- Used for: an optional future `.docx` editor plugin
- License: MIT
- Notes: Not bundled and not a core dependency. The official example plugin
  in this release does not use it.

## openpyxl

- Component: `openpyxl`
- Used for: an optional future `.xlsx` editor plugin
- License: MIT
- Notes: Not bundled and not a core dependency. The official example plugin
  in this release does not use it.

## Plugin dependencies

Plugins may require additional Python packages. Those packages:

- belong to the plugin, not the core;
- are not installed automatically by filer;
- may be vendored inside the plugin directory;
- must have their licenses documented by the plugin author.

Do not assume that a plugin's dependency licenses are compatible with your
distribution. Review them before deploying.

## Fonts

The UI uses the operating system's font stack, including `system-ui`,
`Segoe UI`, `PingFang SC`, `Hiragino Sans GB`, `Microsoft YaHei`,
`Noto Sans CJK SC`, `Malgun Gothic`, `Apple SD Gothic Neo`, and
`Noto Sans KR` where available. These fonts are not bundled.

## Adding dependencies

The project intentionally keeps the core dependency-free. New optional core
dependencies should:

- degrade gracefully when missing;
- be documented in README and `docs/configuration.md`;
- be added to this file with their license and purpose;
- not be committed into the repository unless there is a clear reason.

Plugin-only dependencies should follow the same review discipline but belong
in the plugin's documentation and notices.
