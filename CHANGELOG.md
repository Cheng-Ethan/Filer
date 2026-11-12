# Changelog

All notable changes to this project are documented here. The format is
loosely based on Keep a Changelog, and versions follow semantic versioning
once tagged releases exist.

## [0.1.0] - 2026-11-11

Initial public release.

### Added

- In-browser text editing with encoding, BOM, and line-ending preservation.
- Atomic saves, `cache/edit-backups/`, and stale-write conflict detection
  (`409`).
- Built-in text editor provider and the `/edit` GET/POST routes.
- Plugin API for preview providers, editor providers, namespaced routes,
  static assets, and plugin locales.
- Plugin loader with `plugin.json` manifests, `api_version` validation,
  failure isolation, `--plugins-dir`, and `--no-plugins`.
- Working example plugin: `examples/plugins/todo-editor`.
- Documentation for editing, plugins, the plugin API, and plugin authoring.
- Architecture diagrams for request flow, write pipeline, and plugin
  lifecycle.
- CI test workflow for compilation, unit tests, and locale validation.
- `CHANGELOG.md`.

### Changed

- README now describes the actual core/plugin split and removes placeholder
  support links.
- Preview and list pages show an edit action when an editor provider is
  available; the preview edit action is labeled, not icon-only.
- Opening text, Markdown, or Office files directly now redirects to the
  preview page instead of nesting a second toolbar in an iframe.
- Fixed untranslated `{{i18n:...}}` placeholders in the media wrapper and a
  wrong preview-title translation key.
- Improved Markdown raw-view contrast and made the preview top bar wrap
  cleanly with consistent button heights.
- Directory listings now send `Cache-Control: no-store` so mobile browsers do
  not keep an old page without the edit action.
- Updated README screenshots for the new preview toolbar, text editor, and
  mobile layout, using an all-English UI.
- Fixed Markdown preview to resolve relative image and link URLs against the
  document directory; relative images now load through `?raw=1` instead of
  returning a 404.
- `docs/http-api.md` documents `/edit`, plugin routes, edit status codes, and
  the actual `/info` permission format.
- Security model now treats plugins as trusted code and includes editing and
  plugin data-loss risks.
- Development, configuration, deployment, i18n, contributing, and security
  documentation updated for editing and plugins.

### Not included

- Word or Excel editing. The plugin API and documentation provide the path
  for a third-party `office-editor` plugin.

[Unreleased]: https://github.com/Cheng-Ethan/Filer/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Cheng-Ethan/Filer/releases/tag/v0.1.0
