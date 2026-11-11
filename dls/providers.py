import hashlib
import os
import shutil
import tempfile
import threading
import time
from dataclasses import dataclass

from .config import MAX_EDIT_BACKUPS

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BACKUP_DIR = os.path.join(_ROOT, 'cache', 'edit-backups')
_WRITE_LOCK = threading.Lock()


class EditError(Exception):
    def __init__(self, key, status=400, **kwargs):
        super().__init__(key)
        self.key = key
        self.status = status
        self.kwargs = kwargs


class EditConflict(EditError):
    def __init__(self, **kwargs):
        super().__init__('edit.conflict', status=409, **kwargs)


@dataclass
class EditorPage:
    body: str
    head: str = ''


@dataclass
class SaveResult:
    redirect: str = ''
    message: str = ''


class EditContext:
    """Per-request context handed to editor providers.

    The core owns path validation, conflict detection, backups and atomic
    replacement. Providers only produce the bytes to write.
    """

    def __init__(self, handler, name, target, target_dir, full, form=None):
        self.handler = handler
        self.name = name
        self.target = target
        self.target_dir = target_dir
        self.path = full
        self.form = form or {}
        self.base = os.path.abspath(getattr(handler, 'directory', None) or os.getcwd())

    def t(self, key, **kwargs):
        return self.handler._t()(key, **kwargs)

    def read_bytes(self, limit=None):
        with open(self.path, 'rb') as f:
            if limit is None:
                return f.read()
            return f.read(limit + 1)

    def current_stat(self):
        return os.stat(self.path)

    def check_conflict(self):
        form = self.form or {}
        try:
            expected_mtime = int(form.get('mtime_ns', ''))
            expected_size = int(form.get('size', ''))
        except (TypeError, ValueError):
            return
        st = os.stat(self.path)
        if st.st_mtime_ns != expected_mtime or st.st_size != expected_size:
            raise EditConflict()

    def write_bytes(self, data, backup=True):
        self.check_conflict()
        with _WRITE_LOCK:
            st = os.stat(self.path)
            if os.path.islink(self.path):
                raise EditError('edit.symlink', status=403)
            if backup:
                _backup_file(self.path)
            directory = os.path.dirname(self.path)
            fd, tmp = tempfile.mkstemp(prefix='.filer-edit-', dir=directory)
            try:
                with os.fdopen(fd, 'wb') as f:
                    f.write(data)
                    f.flush()
                    os.fsync(f.fileno())
                os.chmod(tmp, st.st_mode & 0o777)
                os.replace(tmp, self.path)
            except Exception:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
                raise
        return os.stat(self.path)


def _backup_file(path):
    os.makedirs(_BACKUP_DIR, exist_ok=True)
    key = hashlib.sha256(os.path.abspath(path).encode('utf-8', 'replace')).hexdigest()
    folder = os.path.join(_BACKUP_DIR, key)
    os.makedirs(folder, exist_ok=True)
    stamp = time.strftime('%Y%m%d-%H%M%S')
    base = os.path.basename(path) or 'file'
    dest = os.path.join(folder, '%s-%s' % (stamp, base))
    try:
        shutil.copy2(path, dest)
    except OSError:
        return
    try:
        entries = sorted(os.listdir(folder))
        for old in entries[:-MAX_EDIT_BACKUPS]:
            try:
                os.unlink(os.path.join(folder, old))
            except OSError:
                pass
    except OSError:
        pass


class EditorProvider:
    id = ''
    priority = 0

    def matches(self, name, path):
        return False

    def can_edit(self, path):
        return True

    def render(self, ctx):
        raise NotImplementedError

    def save(self, ctx, files=None):
        raise NotImplementedError


class PreviewProvider:
    id = ''
    priority = 0

    def matches(self, name, path):
        return False

    def render(self, ctx):
        raise NotImplementedError


class ProviderRegistry:
    def __init__(self):
        self._editors = []
        self._previews = []
        self._routes = {}
        self._statics = []

    def add_editor(self, provider):
        if any(p.id == provider.id for p in self._editors):
            return
        self._editors.append(provider)
        self._editors.sort(key=lambda p: -p.priority)

    def add_preview(self, provider):
        if any(p.id == provider.id for p in self._previews):
            return
        self._previews.append(provider)
        self._previews.sort(key=lambda p: -p.priority)

    def add_route(self, method, path, handler, plugin_id):
        key = (method.upper(), path)
        if key in self._routes:
            raise ValueError('route already registered: %s %s' % key)
        self._routes[key] = (handler, plugin_id)

    def match_route(self, method, path):
        return self._routes.get((method.upper(), path))

    def add_static(self, prefix, directory, plugin_id):
        self._statics.append((prefix.rstrip('/') + '/', os.path.abspath(directory), plugin_id))
        self._statics.sort(key=lambda item: -len(item[0]))

    def match_static(self, path):
        for prefix, directory, plugin_id in self._statics:
            if path == prefix[:-1] or path.startswith(prefix):
                rel = path[len(prefix):]
                return directory, rel, plugin_id
        return None

    def find_editor(self, name, path):
        for provider in self._editors:
            try:
                if provider.matches(name, path):
                    return provider
            except Exception:
                continue
        return None

    def find_preview(self, name, path):
        for provider in self._previews:
            try:
                if provider.matches(name, path):
                    return provider
            except Exception:
                continue
        return None

    def editors(self):
        return list(self._editors)


REGISTRY = ProviderRegistry()
