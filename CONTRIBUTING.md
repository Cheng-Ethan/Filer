# Contributing

Thanks for helping improve filer. Please keep changes focused and include
tests and documentation when behavior changes.

## Issues

Bug reports are welcome. Please include:

- Python version (`python3 --version`).
- Operating system and version.
- Clear reproduction steps.
- Expected behavior and actual behavior.
- Relevant error output or logs, with secrets removed.
- Whether plugins are enabled, and which plugin versions are installed if the
  problem involves a plugin.

For security issues, follow [SECURITY.md](SECURITY.md) instead of opening a
public issue.

## Development setup

```bash
git clone https://github.com/Cheng-Ethan/Filer.git filer
cd filer
export FILER_AUTH='admin:test'
python3 filer.py --dir /tmp/files --bind 127.0.0.1 --port 18080
```

There are no required third-party Python packages for the core. Optional
features need external tools; see [docs/development.md](docs/development.md).

## Tests

Run the checks from the repository root:

```bash
python3 -m compileall -q .
python3 -B -m unittest discover -s tests -v
python3 -B -m dls.i18n check
```

Please keep existing tests passing and add coverage for behavior changes.
Editing changes should cover success, permission failure, path traversal,
stale-write conflict, and encoding preservation. Plugin changes should cover
load failure isolation, provider registration, routes, and static assets.

## Documentation

User-facing behavior, routes, configuration, and security impact must be
documented:

- Update [docs/http-api.md](docs/http-api.md) for route or parameter changes.
- Update [docs/configuration.md](docs/configuration.md) for startup options.
- Update [docs/editing.md](docs/editing.md) for edit behavior or limits.
- Update [docs/plugins.md](docs/plugins.md) and
  [docs/plugin-api.md](docs/plugin-api.md) for plugin API changes.
- Update [docs/security-model.md](docs/security-model.md) for new trust
  boundaries or write operations.
- Update [CHANGELOG.md](CHANGELOG.md) for user-visible changes.

## Translations

filer uses JSON locale files under `dls/locales/`. See
[docs/i18n.md](docs/i18n.md) for how to add a language, translate keys, and
run the locale validator:

```bash
python3 -m dls.i18n check
```

Keep placeholders unchanged and do not add leading or trailing whitespace.
Plugin locale files use the `plugin.<plugin-id>.*` namespace.

## Plugins

- Plugins are trusted Python code; document their security implications.
- Do not add plugin-only dependencies to the core.
- Declare plugin dependencies in `plugin.json` and document installation.
- Use `ctx.write_bytes()` or `request.write_file()` for writes.
- Include stale-write (`mtime_ns` and `size`) checks.
- Add an example under `examples/plugins/` when it helps users.
- Do not ship a broken Office editor as a placeholder. A design guide is
  available in [docs/writing-a-plugin.md](docs/writing-a-plugin.md).

## Dependencies and licenses

- Keep the core dependency-free.
- New optional core dependencies must degrade gracefully, be documented in
  README and [docs/configuration.md](docs/configuration.md), and be added to
  [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
- Plugin dependencies belong to the plugin. Add their licenses to the
  plugin's own notices.
- Do not commit credentials, tokens, private paths, or vendor packages unless
  the repository policy explicitly allows it.

## Code style

- Public APIs, user-facing text, and documentation are written in English.
- Internal comments may be written in Chinese where it improves clarity.
- Keep the project dependency-free unless a new dependency is clearly
  justified.
- Prefer small, focused changes over broad rewrites.
- Use the core response helpers so i18n and headers stay consistent.
- Preserve graceful degradation: missing optional tools must not break core
  browsing.

## Pull requests

- Describe the problem, the change, and the tests you ran.
- Keep unrelated refactors out of the same pull request.
- Update documentation and locale keys in the same change.
- Mention security implications for auth, shell, upload, edit, SSRF, plugins,
  and file access.
- Use the pull request template as a checklist.

## Code of conduct

Participation is covered by
[.github/CODE_OF_CONDUCT.md](.github/CODE_OF_CONDUCT.md). Be respectful and
assume good intent while correcting problems directly.
