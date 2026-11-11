# Pull request

## Summary

What does this change do, and why?

## Testing

- [ ] `python3 -m compileall -q .`
- [ ] `python3 -B -m unittest discover -s tests -v`
- [ ] `python3 -B -m dls.i18n check` (if locales changed)
- [ ] Manual check of the affected page or endpoint
- [ ] If a plugin changed: loaded it and tested preview/edit/route/static behavior
- [ ] If editing changed: tested success, permission failure, and stale-write conflict

Describe the tests or manual checks you ran:

```text

```

## Documentation

- [ ] Updated relevant docs under `docs/`
- [ ] Updated `docs/http-api.md` if routes or parameters changed
- [ ] Updated `docs/configuration.md` if startup options changed
- [ ] Updated `docs/editing.md` if edit behavior or limits changed
- [ ] Updated `docs/plugins.md` and `docs/plugin-api.md` if the plugin API changed
- [ ] Updated `CHANGELOG.md`
- [ ] Updated locale files for new UI text

## Compatibility and safety

- [ ] Core remains dependency-free
- [ ] Optional tools still degrade gracefully
- [ ] Plugin-only dependencies are kept out of the core
- [ ] Plugin permissions and trusted-code implications are documented
- [ ] No credentials, tokens, private paths, or secrets are committed
- [ ] Security implications considered (auth, shell, upload, edit, SSRF, plugins, file access)

## Checklist

- [ ] The change is focused and does not include unrelated refactors
- [ ] I have read `CONTRIBUTING.md`
