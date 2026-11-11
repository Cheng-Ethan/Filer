# Todo editor example plugin

This plugin is a small, working example of the filer editor plugin API. It
adds an editor for `.todo` files and renders them as a checkbox list.

## Install

```bash
cp -r examples/plugins/todo-editor plugins/todo-editor
python3 filer.py --dir /path/to/files
```

The default plugin directory is `plugins/` next to `filer.py`. You can also
keep the example in place and load it explicitly:

```bash
python3 filer.py --dir /path/to/files \
  --plugins-dir examples/plugins
```

Create a `.todo` file and open it through the web UI. The preview and list
views show an edit action because the plugin registers an editor for the
extension.

## What it demonstrates

- `plugin.json` manifest and `register(ctx)` entry point.
- `ctx.register_editor(...)` with an `EditorProvider`.
- `ctx.register_locale(...)` with namespaced translation keys.
- Safe writes through the core `EditContext`, including conflict detection
  and backups.

See [docs/plugin-api.md](../../../docs/plugin-api.md) and
[docs/writing-a-plugin.md](../../../docs/writing-a-plugin.md).
