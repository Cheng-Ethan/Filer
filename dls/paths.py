import os


class PathError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def base_dir(handler):
    return os.path.abspath(getattr(handler, 'directory', None) or os.getcwd())


def resolve_dir(handler, target):
    base = base_dir(handler)
    target = target or '/'
    if not target.startswith('/'):
        target = '/' + target
    target_dir = os.path.abspath(os.path.join(base, target.lstrip('/')))
    if not (target_dir == base or target_dir.startswith(base + os.sep)):
        raise PathError(403, 'Forbidden path')
    return base, target_dir


def resolve_file(handler, target, name):
    if not name or name in ('.', '..') or '/' in name or '\\' in name:
        raise PathError(400, 'Bad filename')
    base, target_dir = resolve_dir(handler, target)
    full = os.path.join(target_dir, name)
    real_base = os.path.realpath(base)
    real_full = os.path.realpath(full)
    if not (real_full == real_base or real_full.startswith(real_base + os.sep)):
        raise PathError(403, 'Forbidden path')
    return base, target_dir, full
