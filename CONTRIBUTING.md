# Contributing

## Issues

Bug reports are welcome. Please include:

- Python version (`python3 --version`).
- Operating system and version.
- Clear reproduction steps.
- Expected behavior and actual behavior.
- Relevant error output or logs, with secrets removed.

For security issues, follow [SECURITY.md](SECURITY.md) instead of opening a public issue.

## Tests

Run the test suite from the repository root:

```bash
python3 -m unittest discover -s tests
```

Please keep existing tests passing and add coverage for behavior changes when practical.

## Code Style

- Public APIs, user-facing text, and documentation are written in English.
- Internal comments may be written in Chinese where it improves clarity.
- Keep the project dependency-free unless a new dependency is clearly justified.
- Prefer small, focused changes over broad rewrites.
