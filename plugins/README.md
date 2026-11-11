# Local plugins

filer loads plugins from this directory at startup. Each plugin is a
subdirectory with a `plugin.json` manifest and an entry file:

```text
plugins/
  my-plugin/
    plugin.json
    plugin.py
    vendor/       optional private Python dependencies
    static/       optional static assets under /plugins/my-plugin/
    locales/      optional translation files
```

Plugins are trusted Python code and run in the server process with the same
permissions as the service account. Only install plugins you trust.

See [docs/plugins.md](../docs/plugins.md) and
[docs/plugin-api.md](../docs/plugin-api.md) for the full API and security
model.
