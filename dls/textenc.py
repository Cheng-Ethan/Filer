import locale
import sys

from .config import _MAX_PREVIEW_CHARS, _TEXT_ENCODINGS

_BOMS = (
    (b'\xef\xbb\xbf', 'utf-8-sig'),
    (b'\xff\xfe\x00\x00', 'utf-32-le'),
    (b'\x00\x00\xfe\xff', 'utf-32-be'),
    (b'\xff\xfe', 'utf-16-le'),
    (b'\xfe\xff', 'utf-16-be'),
)


def _charset_for(enc):
    return 'utf-8' if enc in (None, '', 'utf-8-sig') else enc


def _decode_console(raw):
    if sys.platform == 'win32':
        for enc in ('utf-8', locale.getpreferredencoding(False), 'gb18030'):
            try:
                return raw.decode(enc)
            except (LookupError, UnicodeDecodeError):
                continue
    return raw.decode('utf-8', 'replace')


def _detect_encoding(raw):
    if not raw:
        return 'utf-8'
    for bom, enc in _BOMS:
        if raw.startswith(bom):
            return enc
    if len(raw) % 2 == 0 and raw.count(b'\x00') >= max(1, len(raw) // 3):
        for enc in ('utf-16-le', 'utf-16-be'):
            try:
                text = raw.decode(enc)
            except UnicodeDecodeError:
                continue
            ctrl = sum(1 for ch in text if ord(ch) < 32 and ch not in '\r\n\t\f')
            if ctrl <= max(1, len(text) // 20):
                return enc
    if b'\x00' in raw:
        return None
    for enc in _TEXT_ENCODINGS:
        try:
            raw.decode(enc)
            return enc
        except UnicodeDecodeError as e:
            if e.start >= len(raw) - 4:
                return enc
    return None


def _detect_file_encoding(fpath, probe=65536):
    try:
        with open(fpath, 'rb') as f:
            return _detect_encoding(f.read(probe))
    except OSError:
        return None


def _looks_text(fpath, probe=8192):
    return _detect_file_encoding(fpath, probe) is not None


def _decode_bytes(raw, enc):
    try:
        text = raw.decode(enc)
    except (LookupError, UnicodeDecodeError):
        try:
            text = raw.decode(enc or 'utf-8', 'replace')
        except LookupError:
            text = raw.decode('utf-8', 'replace')
    return text[1:] if text.startswith('\ufeff') else text


def _clip_text(text, limit=_MAX_PREVIEW_CHARS):
    if len(text) > limit:
        return text[:limit] + '\n\n…[内容过大，已截断]'
    return text
