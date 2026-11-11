#!/usr/bin/env python3
"""filer: a small self-hosted file browser.

- Directory listing with upload, download, delete, preview, and edit actions.
- Text and Markdown preview, plus optional Office/PDF/image/audio/video preview.
- In-browser text editing with encoding, BOM, and line-ending preservation.
- Plugin loading for preview providers, editors, routes, static assets, and locales.
- Optional PTY-backed terminal, TTS, and article reader.
- All HTTP requests require Basic Auth.
"""

import argparse
import functools
import os
from http.server import ThreadingHTTPServer

from dls import __version__
from dls.handler import ForceDownloadHandler
from dls.plugins import load_plugins

_ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    parser = argparse.ArgumentParser(prog='filer',
                                     description='Self-hosted file browser with preview, editing, and optional terminal')
    parser.add_argument('--version', action='version',
                        version='%(prog)s ' + __version__)
    parser.add_argument('--port', type=int, default=9000)
    parser.add_argument('--dir', default='.', help='Directory to serve')
    parser.add_argument('--bind', default='127.0.0.1',
                        help='Bind address (default: localhost only). '
                             'Put an HTTPS reverse proxy in front before '
                             'exposing the service to a network.')
    parser.add_argument('--user',
                        help='Basic Auth credentials in username:password form. '
                             'FILER_AUTH (or DL_AUTH) is used as a fallback; '
                             '--user takes precedence.')
    parser.add_argument('--plugins-dir', action='append', default=None,
                        help='Plugin directory (repeatable; default: <repo>/plugins)')
    parser.add_argument('--no-plugins', action='store_true',
                        help='Disable plugin loading')
    args = parser.parse_args()

    auth = args.user if args.user is not None else (
        os.environ.get('FILER_AUTH') or os.environ.get('DL_AUTH'))
    if auth is None:
        parser.error("--user must be 'username:password', both non-empty "
                     "(or set FILER_AUTH / DL_AUTH)")
    user, _, password = auth.partition(':')
    if not user or not password:
        parser.error("--user must be 'username:password', both non-empty")

    plugin_dirs = args.plugins_dir or [os.path.join(_ROOT, 'plugins')]
    if not args.no_plugins:
        loaded = load_plugins([os.path.abspath(p) for p in plugin_dirs])
        if loaded:
            print('filer: plugins: ' + ', '.join(loaded))

    os.chdir(args.dir)
    handler = functools.partial(
        ForceDownloadHandler, user=user, password=password)
    server = ThreadingHTTPServer((args.bind, args.port), handler)
    print(f'filer: Serving {args.dir} on {args.bind}:{args.port} (auth: {user}:****)')
    if args.bind == '0.0.0.0':
        print('filer: WARNING: listening on all interfaces. Basic Auth is clear-text — use HTTPS.')
    server.serve_forever()


if __name__ == '__main__':
    main()