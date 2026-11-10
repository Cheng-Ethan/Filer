import asyncio
import hashlib
import json
import os
import queue
import re
import sys
import threading
import time
import urllib.parse

from .config import _preview_kind
from .office import _office_text
from .textenc import _decode_bytes, _detect_encoding

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_VENDOR = os.path.join(_ROOT, 'vendor')
_CACHE_DIR = os.path.join(_ROOT, 'cache', 'tts')
_DICT_PATH = os.path.join(_ROOT, 'pronunciation.json')

_DEFAULT_VOICE = 'zh-CN-XiaoxiaoNeural'
_MAX_TTS_CHARS = 50000
_MAX_READ_BYTES = 4 * 1024 * 1024
_CHUNK_CHARS = 800
_OFFICE_KINDS = {'docx', 'xlsx', 'pptx', 'doc', 'rtf'}

_FALLBACK_VOICES = [
    {'id': 'zh-CN-XiaoxiaoNeural', 'name': '晓晓（女）', 'locale': 'zh-CN', 'gender': 'Female'},
    {'id': 'zh-CN-XiaoyiNeural', 'name': '晓伊（女）', 'locale': 'zh-CN', 'gender': 'Female'},
    {'id': 'zh-CN-YunxiNeural', 'name': '云希（男）', 'locale': 'zh-CN', 'gender': 'Male'},
    {'id': 'zh-CN-YunjianNeural', 'name': '云健（男）', 'locale': 'zh-CN', 'gender': 'Male'},
    {'id': 'zh-CN-YunxiaNeural', 'name': '云夏（男）', 'locale': 'zh-CN', 'gender': 'Male'},
]

_VOICES_LOCK = threading.Lock()
_VOICES = None
_DICT_LOCK = threading.Lock()
_DICT_STATE = {'mtime': None, 'map': {}}
_GEN_LOCKS = {}
_GEN_LOCKS_LOCK = threading.Lock()


class TtsError(Exception):
    pass


def _ensure_vendor():
    if _VENDOR not in sys.path:
        sys.path.insert(0, _VENDOR)


def _engine():
    _ensure_vendor()
    try:
        import edge_tts
    except Exception as e:
        raise TtsError('语音引擎未安装（vendor/edge-tts）：%s' % e)
    return edge_tts


def _gen_lock(cache_path):
    with _GEN_LOCKS_LOCK:
        return _GEN_LOCKS.setdefault(cache_path, threading.Lock())


def _load_dict():
    try:
        st = os.stat(_DICT_PATH)
    except OSError:
        return {}
    with _DICT_LOCK:
        if _DICT_STATE['mtime'] == st.st_mtime:
            return _DICT_STATE['map']
        try:
            with open(_DICT_PATH, encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            data = {}
        mapping = {str(k): str(v) for k, v in data.items()
                   if isinstance(k, str) and isinstance(v, str) and k and v}
        _DICT_STATE.update(mtime=st.st_mtime, map=mapping)
        return mapping


def _apply_dict(text):
    mapping = _load_dict()
    if not mapping:
        return text
    keys = sorted(mapping, key=len, reverse=True)
    pattern = re.compile('|'.join(re.escape(k) for k in keys))
    return pattern.sub(lambda m: mapping[m.group(0)], text)


def _markdown_to_text(text):
    text = re.sub(r'```.*?```', '', text, flags=re.S)
    text = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'^\s{0,3}#{1,6}\s*', '', text, flags=re.M)
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.M)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.M)
    text = re.sub(r'[`*_~>|#]', '', text)
    return re.sub(r'\n{3,}', '\n\n', text)


def _extract_text(path):
    kind = _preview_kind(os.path.basename(path))
    if kind in _OFFICE_KINDS:
        return _office_text(path, kind)
    with open(path, 'rb') as f:
        raw = f.read(_MAX_READ_BYTES)
    enc = _detect_encoding(raw) or 'utf-8'
    text = _decode_bytes(raw, enc)
    if kind == 'markdown':
        text = _markdown_to_text(text)
    return text


def _chunks(text, limit=_CHUNK_CHARS):
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n+', '\n', text)
    parts = re.split(r'(?<=[。！？!?；;：:\n])', text)
    out = []
    buf = ''
    for p in parts:
        p = p.strip()
        if not p:
            continue
        while len(p) > limit:
            if buf:
                out.append(buf)
                buf = ''
            out.append(p[:limit])
            p = p[limit:]
        if buf and len(buf) + len(p) > limit:
            out.append(buf)
            buf = ''
        buf += p
    if buf.strip():
        out.append(buf.strip())
    return [c for c in out if c.strip()]


def _rate_str(rate):
    pct = int(round((float(rate) - 1.0) * 100))
    return ('+%d%%' % pct) if pct >= 0 else ('%d%%' % pct)


def _strip_id3(data):
    if data.startswith(b'ID3') and len(data) >= 10:
        size = ((data[6] & 0x7F) << 21) | ((data[7] & 0x7F) << 14) \
            | ((data[8] & 0x7F) << 7) | (data[9] & 0x7F)
        return data[10 + size:]
    return data


def _prepare(path, voice, rate):
    text = _apply_dict(_extract_text(path)).strip()
    if not text:
        raise TtsError('没有可朗读的文字')
    if len(text) > _MAX_TTS_CHARS:
        raise TtsError('文本过长（%d 字），最多支持 %d 字' % (len(text), _MAX_TTS_CHARS))
    try:
        st = os.stat(path)
    except OSError as e:
        raise TtsError('读取文件失败：%s' % e)
    key = hashlib.sha256()
    key.update(('%s|%d|%d|%s|%.2f' % (os.path.abspath(path), st.st_mtime_ns,
                                      st.st_size, voice, rate)).encode('utf-8'))
    key.update(text.encode('utf-8'))
    return text, os.path.join(_CACHE_DIR, key.hexdigest() + '.mp3')


def _iter_audio(text, voice, rate, stop):
    q = queue.Queue()
    errors = []

    def worker():
        try:
            async def run():
                edge_tts = _engine()
                first = True
                chunks = _chunks(text)
                if chunks and len(chunks[0]) > 200:
                    chunks = [chunks[0][:200], chunks[0][200:]] + chunks[1:]
                for chunk in chunks:
                    if stop.is_set():
                        return
                    buf = bytearray()
                    comm = edge_tts.Communicate(chunk, voice, rate=_rate_str(rate))
                    async for item in comm.stream():
                        if stop.is_set():
                            return
                        if item.get('type') == 'audio' and item.get('data'):
                            buf.extend(item['data'])
                    data = bytes(buf)
                    if not data:
                        continue
                    if not first:
                        data = _strip_id3(data)
                    first = False
                    q.put(data)
            asyncio.run(run())
        except Exception as e:
            errors.append(e)
        finally:
            q.put(None)

    threading.Thread(target=worker, daemon=True).start()
    while True:
        item = q.get()
        if item is None:
            break
        yield item
    if errors:
        raise TtsError(str(errors[0]))


def synthesize_file(path, voice, rate):
    text, cache = _prepare(path, voice, rate)
    if os.path.isfile(cache) and os.path.getsize(cache) > 0:
        return cache
    os.makedirs(_CACHE_DIR, exist_ok=True)
    with _gen_lock(cache):
        if os.path.isfile(cache) and os.path.getsize(cache) > 0:
            return cache
        tmp = cache + '.part'
        stop = threading.Event()
        try:
            with open(tmp, 'wb') as f:
                for data in _iter_audio(text, voice, rate, stop):
                    f.write(data)
            if os.path.getsize(tmp) == 0:
                raise TtsError('语音合成无输出')
            os.replace(tmp, cache)
        finally:
            stop.set()
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass
    return cache


def list_voices():
    global _VOICES
    if _VOICES is not None:
        return _VOICES
    with _VOICES_LOCK:
        if _VOICES is not None:
            return _VOICES
        try:
            raw = asyncio.run(_engine().list_voices())
        except Exception:
            _VOICES = list(_FALLBACK_VOICES)
            return _VOICES
        out = []
        for v in raw:
            locale = v.get('Locale', '')
            if not locale.startswith('zh'):
                continue
            out.append({
                'id': v.get('ShortName', ''),
                'name': v.get('FriendlyName') or v.get('ShortName', ''),
                'locale': locale,
                'gender': v.get('Gender', ''),
            })
        out = [v for v in out if v['id']]
        out.sort(key=lambda x: (not x['locale'].startswith('zh-CN'), x['id']))
        _VOICES = out or list(_FALLBACK_VOICES)
        return _VOICES


def _normalize_voice(voice):
    if not voice:
        voice = _DEFAULT_VOICE
    try:
        available = {v['id'] for v in list_voices()}
    except Exception:
        return voice
    return voice if voice in available else _DEFAULT_VOICE


class TtsMixin:
    def _serve_tts_voices(self):
        try:
            voices = list_voices()
        except Exception as e:
            self._send_json({'ok': False, 'error': '语音服务不可用：%s' % e},
                            status=503)
            return
        self._send_json({'ok': True, 'default': _DEFAULT_VOICE,
                         'voices': voices})

    def _serve_tts(self):
        base = os.path.abspath(self.directory) if hasattr(self, 'directory') else os.getcwd()
        qs = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        target = qs.get('dir', ['/'])[0] or '/'
        if not target.startswith('/'):
            target = '/' + target
        target_dir = os.path.abspath(os.path.join(base, target.lstrip('/')))
        if not (target_dir == base or target_dir.startswith(base + os.sep)):
            self._send_json({'ok': False, 'error': 'forbidden'}, status=403)
            return
        name = qs.get('name', [''])[0]
        if not name or name in ('.', '..') or '/' in name or '\\' in name:
            self._send_json({'ok': False, 'error': 'bad name'}, status=400)
            return
        full = os.path.join(target_dir, name)
        if not os.path.isfile(full):
            self._send_json({'ok': False, 'error': 'not found'}, status=404)
            return

        try:
            rate = float(qs.get('rate', ['1'])[0])
        except (TypeError, ValueError):
            rate = 1.0
        rate = max(0.5, min(2.0, rate))
        voice = qs.get('voice', [_DEFAULT_VOICE])[0] or _DEFAULT_VOICE
        if qs.get('status'):
            self._tts_status_for_path(full, voice, rate)
            return
        self._tts_from_path(full, voice, rate)

    def _tts_status_for_path(self, full, voice, rate):
        voice = _normalize_voice(voice)
        try:
            _, cache = _prepare(full, voice, rate)
            ready = os.path.isfile(cache) and os.path.getsize(cache) > 0
        except TtsError as e:
            self._send_json({'ok': False, 'error': str(e)}, status=400)
            return
        except Exception as e:
            self._send_json({'ok': False, 'error': '无法读取正文：%s' % e},
                            status=400)
            return
        self._send_json({'ok': True, 'ready': ready})

    def _tts_from_path(self, full, voice, rate):
        voice = _normalize_voice(voice)
        try:
            text, cache = _prepare(full, voice, rate)
        except TtsError as e:
            self._send_json({'ok': False, 'error': str(e)}, status=400)
            return
        except Exception as e:
            self._send_json({'ok': False, 'error': '无法读取正文：%s' % e},
                            status=400)
            return
        if os.path.isfile(cache) and os.path.getsize(cache) > 0:
            self._stream_audio(cache)
            return
        self._stream_tts(text, voice, rate, cache)

    def _stream_tts(self, text, voice, rate, cache):
        os.makedirs(_CACHE_DIR, exist_ok=True)
        with _gen_lock(cache):
            if os.path.isfile(cache) and os.path.getsize(cache) > 0:
                self._stream_audio(cache)
                return
            tmp = cache + '.part'
            stop = threading.Event()
            self.protocol_version = 'HTTP/1.1'
            self.send_response(200)
            self.send_header('Content-Type', 'audio/mpeg')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Connection', 'close')
            self.send_header('Transfer-Encoding', 'chunked')
            self.end_headers()
            try:
                started = time.time()
                generated = 0.0
                with open(tmp, 'wb') as f:
                    for data in _iter_audio(text, voice, rate, stop):
                        f.write(data)
                        self.wfile.write(('%x\r\n' % len(data)).encode('ascii')
                                         + data + b'\r\n')
                        self.wfile.flush()
                        generated += len(data) * 8 / 48000.0
                        ahead = generated - (time.time() - started)
                        if ahead > 20:
                            time.sleep(min(ahead - 20, 2.0))
                self.wfile.write(b'0\r\n\r\n')
                self.wfile.flush()
                if os.path.getsize(tmp) > 0:
                    os.replace(tmp, cache)
                else:
                    raise TtsError('语音合成无输出')
            except (BrokenPipeError, ConnectionResetError):
                stop.set()
            except Exception:
                stop.set()
                try:
                    self.wfile.write(b'0\r\n\r\n')
                except Exception:
                    pass
            finally:
                stop.set()
                if os.path.exists(tmp):
                    try:
                        os.remove(tmp)
                    except OSError:
                        pass

    def _stream_audio(self, path):
        size = os.path.getsize(path)
        start, end, status = 0, size - 1, 200
        rng = self.headers.get('Range', '')
        m = re.match(r'bytes=(\d*)-(\d*)\s*$', rng.strip())
        if m:
            if m.group(1):
                start = int(m.group(1))
                end = int(m.group(2)) if m.group(2) else size - 1
            elif m.group(2):
                length = int(m.group(2))
                start = max(0, size - length)
                end = size - 1
            if start >= size or start > end:
                self.send_response(416)
                self.send_header('Content-Range', 'bytes */%d' % size)
                self.send_header('Content-Length', '0')
                self.end_headers()
                return
            end = min(end, size - 1)
            status = 206
        self.send_response(status)
        self.send_header('Content-Type', 'audio/mpeg')
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(end - start + 1))
        if status == 206:
            self.send_header('Content-Range', 'bytes %d-%d/%d' % (start, end, size))
        self.end_headers()
        try:
            with open(path, 'rb') as f:
                f.seek(start)
                left = end - start + 1
                while left > 0:
                    chunk = f.read(min(65536, left))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    left -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass
