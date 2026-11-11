# Office editor plugin (reserved)

**Status: not implemented in this release.**

This directory is reserved for a future official example plugin that edits
Office documents through the filer plugin API. The core repository stays
dependency-free; any Office editor dependencies belong to the plugin.

Recommended scope:

1. `.xlsx` editing with `openpyxl`.
2. `.docx` text-level editing with `python-docx`.
3. Legacy `.xls` and `.doc` remain preview-only initially.

Do not add a partial implementation here. A plugin that can save a corrupted
file is worse than no plugin. Follow the safety and testing guidance in:

- [docs/writing-a-plugin.md](../../../docs/writing-a-plugin.md)
- [docs/plugin-api.md](../../../docs/plugin-api.md)
- [docs/editing.md](../../../docs/editing.md)

The working example for the editor API is
[`../todo-editor`](../todo-editor).
