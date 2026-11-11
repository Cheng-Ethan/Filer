import importlib.util
import json
import mimetypes
import os
import re
import sys
import urllib.parse
from dataclasses import dataclass, field

from .config import MAX_EDIT_REQUEST_BYTES
from .i18n import register_plugin_locale, translate
from .paths import PathError, resolve_file
from .providers import REGISTRY, EditContext

API_VERSION = 1


class PluginError(Exception):
    pass


@dataclass
class PluginResponse:
    body: bytes = b''
    status: int = 200
    content_type: str = 'text/html; charset=utf-8'
    headers: dict = field(default_factory=dict)


class PluginContext:
    def __init__(self, plugin_id, plugin_dir, manifest, registry):
        self.id = plugin_id
        self.dir = plugin_dir
        self.manifest = manifest
        self.version = manifest.get('version', '')
        self.api_version = API_VERSION
        self._registry = registry

    def t(self, key, **kwargs):
        return translate(key, **kwargs)

    def log(self, message):
        sys.stderr.write('filer: plugin %s: %s\n' % (self.id, message))

    def _inside(self, path):
        root = os.path.realpath(self.dir)
        real = os.path.realpath(path)
        if real != root and not real.startswith(root + os.sep):
            raise PluginError('path is outside the plugin directory')
        return real

    def register_editor(self, provider):
        provider.id = '%s:%s' % (
            self.id, getattr(provider, 'id', '') or provider.__class__.__name__)
        self._registry.add_editor(provider)
        return provider

    def register_preview(self, provider):
        provider.id = '%s:%s' % (
            self.id, getattr(provider, 'id', '') or provider.__class__.__name__)
        self._registry.add_preview(provider)
        return provider

    def register_route(self, method, path, handler):
        method = method.upper()
        if method not in ('GET', 'POST'):
            raise PluginError('only GET and POST plugin routes are supported')
        prefix = '/plugins/%s/' % self.id
        if not path.startswith(prefix):
            raise PluginError('plugin routes must start with %s' % prefix)
        self._registry.add_route(method, path, handler, self.id)

    def register_static(self, prefix, directory):
        prefix = prefix.rstrip('/') + '/'
        if not prefix.startswith('/plugins/%s/' % self.id):
            raise PluginError('static prefix must start with /plugins/%s/' % self.id)
        directory = self._inside(directory)
        if not os.path.isdir(directory):
            raise PluginError('static directory does not exist')
        self._registry.add_static(prefix, directory, self.id)

    def register_locale(self, directory):
        directory = self._inside(directory)
        if not os.path.isdir(directory):
            raise PluginError('locale directory does not exist')
        register_plugin_locale(self.id, directory)


class PluginRequest:
    def __init__(self, handler, plugin_id, path):
        self.handler = handler
        self.plugin_id = plugin_id
        self.method = handler.command
        self.path = path
        self.query = urllib.parse.parse_qs(
            urllib.parse.urlsplit(handler.path).query)
        self.headers = handler.headers
        self._body = None
        self._form = None
        self._files = None

    def body(self, limit=MAX_EDIT_REQUEST_BYTES):
        if self._body is None:
            length = int(self.headers.get('Content-Length', 0) or 0)
            if length <= 0 or length > limit:
                self._body = b''
            else:
                self._body = self.handler.rfile.read(length)
        return self._body

    def json(self, limit=MAX_EDIT_REQUEST_BYTES):
        raw = self.body(limit)
        try:
            return json.loads(raw.decode('utf-8', 'replace'))
        except (ValueError, UnicodeDecodeError):
            return None

    def form(self, limit=MAX_EDIT_REQUEST_BYTES):
        if self._form is None:
            ctype = (self.headers.get('Content-Type') or '').lower()
            if 'multipart/form-data' in ctype:
                fields = self.handler._parse_multipart(limit=limit)
                self._form = {}
                self._files = {}
                for key, item in (fields or {}).items():
                    if item.get('filename'):
                        self._files[key] = item['content']
                    else:
                        self._form[key] = item['content'].decode('utf-8', 'replace')
            else:
                self._form = self.handler._parse_urlencoded(limit=limit) or {}
                self._files = {}
        return self._form

    def files(self, limit=MAX_EDIT_REQUEST_BYTES):
        self.form(limit)
        return self._files or {}

    def resolve_file(self, dir_param='/', name=''):
        _, target_dir, full = resolve_file(self.handler, dir_param, name)
        return target_dir, full

    def read_file(self, dir_param='/', name='', limit=MAX_EDIT_REQUEST_BYTES):
        _, full = self.resolve_file(dir_param, name)
        with open(full, 'rb') as f:
            data = f.read(limit + 1)
        if len(data) > limit:
            raise PluginError('file is too large')
        return data

    def write_file(self, dir_param, name, data, expected_mtime=None,
                   expected_size=None):
        _, target_dir, full = resolve_file(self.handler, dir_param, name)
        form = {}
        if expected_mtime is not None:
            form['mtime_ns'] = str(expected_mtime)
        if expected_size is not None:
            form['size'] = str(expected_size)
        ctx = EditContext(self.handler, name, dir_param, target_dir, full,
                          form=form)
        return ctx.write_bytes(data)


class PluginsMixin:
    def _serve_plugin_static(self, match):
        directory, rel, _plugin_id = match
        rel = urllib.parse.unquote(rel)
        if not rel or '..' in rel.split('/'):
            self.send_error(404, 'Not found')
            return
        full = os.path.realpath(os.path.join(directory, rel))
        root = os.path.realpath(directory)
        if not (full == root or full.startswith(root + os.sep)):
            self.send_error(403, 'Forbidden path')
            return
        if not os.path.isfile(full):
            self.send_error(404, 'Not found')
            return
        try:
            with open(full, 'rb') as f:
                data = f.read()
        except OSError:
            self.send_error(404, 'Not found')
            return
        ctype = mimetypes.guess_type(full)[0] or 'application/octet-stream'
        if full.endswith(('.js', '.mjs')):
            ctype = 'text/javascript; charset=utf-8'
        elif ctype.startswith('text/') or ctype in (
                'application/json', 'image/svg+xml'):
            ctype += '; charset=utf-8'
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'public, max-age=300')
        self.end_headers()
        self.wfile.write(data)

    def _serve_plugin_route(self, match):
        handler, _plugin_id = match
        path = urllib.parse.urlsplit(self.path).path
        request = PluginRequest(self, _plugin_id, path)
        try:
            result = handler(request)
        except PathError as e:
            self.send_error(e.status, e.message)
            return
        except Exception as e:
            self._send_plugin_response(PluginResponse(
                body=('plugin error: %s' % e).encode('utf-8'),
                status=500, content_type='text/plain; charset=utf-8'))
            return
        if result is None:
            self.send_response(204)
            self.end_headers()
            return
        if not isinstance(result, PluginResponse):
            if isinstance(result, (dict, list)):
                body = json.dumps(result, ensure_ascii=False).encode('utf-8')
                result = PluginResponse(body=body, content_type='application/json; charset=utf-8')
            elif isinstance(result, bytes):
                result = PluginResponse(body=result, content_type='application/octet-stream')
            else:
                result = PluginResponse(body=str(result).encode('utf-8'))
        self._send_plugin_response(result)

    def _send_plugin_response(self, response):
        self.send_response(response.status)
        self.send_header('Content-Type', response.content_type)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(response.body)))
        for key, value in response.headers.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(response.body)


def _validate_manifest(manifest, fallback_id):
    if not isinstance(manifest, dict):
        raise PluginError('plugin.json must contain an object')
    plugin_id = str(manifest.get('id') or fallback_id)
    if not re.match(r'^[A-Za-z0-9_.-]+$', plugin_id):
        raise PluginError('invalid plugin id: %r' % plugin_id)
    try:
        api_version = int(manifest.get('api_version', 0))
    except (TypeError, ValueError):
        raise PluginError('api_version must be an integer')
    if api_version != API_VERSION:
        raise PluginError('unsupported api_version %s (core supports %s)'
                          % (api_version, API_VERSION))
    entry = str(manifest.get('entry') or 'plugin.py')
    return plugin_id, entry


def load_plugins(plugin_dirs=None, registry=REGISTRY, stream=None):
    stream = stream or sys.stderr
    loaded = []
    for root in plugin_dirs or []:
        root = os.path.abspath(root)
        if not os.path.isdir(root):
            continue
        try:
            names = sorted(os.listdir(root))
        except OSError:
            continue
        for name in names:
            if name.startswith(('.', '_')):
                continue
            plugin_dir = os.path.join(root, name)
            manifest_path = os.path.join(plugin_dir, 'plugin.json')
            if not os.path.isdir(plugin_dir) or not os.path.isfile(manifest_path):
                continue
            try:
                with open(manifest_path, encoding='utf-8') as f:
                    manifest = json.load(f)
                plugin_id, entry = _validate_manifest(manifest, name)
                if not manifest.get('enabled', True):
                    continue
                root_real = os.path.realpath(plugin_dir)
                entry_path = os.path.realpath(os.path.join(plugin_dir, entry))
                if not entry_path.startswith(root_real + os.sep):
                    raise PluginError('entry is outside the plugin directory')
                if not os.path.isfile(entry_path):
                    raise PluginError('entry file not found: %s' % entry)
                for extra in (os.path.join(plugin_dir, 'vendor'), plugin_dir):
                    if os.path.isdir(extra) and extra not in sys.path:
                        sys.path.insert(0, extra)
                module_name = 'filer_plugin_' + re.sub(r'\W+', '_', plugin_id)
                spec = importlib.util.spec_from_file_location(module_name, entry_path)
                if spec is None or spec.loader is None:
                    raise PluginError('cannot create import spec')
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                register = getattr(module, 'register', None)
                if not callable(register):
                    raise PluginError('entry must define register(ctx)')
                ctx = PluginContext(plugin_id, plugin_dir, manifest, registry)
                register(ctx)
                loaded.append(plugin_id)
            except Exception as e:
                stream.write('filer: plugin %s skipped: %s\n' % (name, e))
    return loaded
