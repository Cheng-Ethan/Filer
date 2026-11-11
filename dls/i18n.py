import contextvars
import json
import os
import re

_LOCALES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'locales')
_DEFAULT_LANG = 'en'
_CURRENT_LANG = contextvars.ContextVar('filer_lang', default=_DEFAULT_LANG)
_CACHE = {}
_SUPPORTED = None
_PLUGIN_LOCALES = {}


def _locale_path(code):
    return os.path.join(_LOCALES_DIR, code + '.json')


def _load_locale(code):
    if code in _CACHE:
        return _CACHE[code]
    try:
        with open(_locale_path(code), encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {}
    _CACHE[code] = data
    return data


def set_current_lang(lang):
    _CURRENT_LANG.set(lang)


def current_lang():
    return _CURRENT_LANG.get()


def translate(key, **kwargs):
    return get_translator(_CURRENT_LANG.get())(key, **kwargs)


def available_locales():
    global _SUPPORTED
    if _SUPPORTED is not None:
        return list(_SUPPORTED)
    found = []
    try:
        names = sorted(os.listdir(_LOCALES_DIR))
    except OSError:
        names = []
    for name in names:
        if not name.endswith('.json'):
            continue
        code = name[:-5]
        meta = _load_locale(code).get('_meta') or {}
        if not meta.get('code'):
            meta = dict(meta, code=code)
        found.append({
            'code': meta.get('code', code),
            'name': meta.get('name', code),
            'dir': meta.get('dir', 'ltr'),
        })
    found.sort(key=lambda x: (x['code'] != _DEFAULT_LANG, x['code']))
    _SUPPORTED = found
    return list(found)


def flatten(data, prefix=''):
    out = {}
    for key, value in data.items():
        if key == '_meta':
            continue
        name = (prefix + '.' + key) if prefix else key
        if isinstance(value, dict):
            out.update(flatten(value, name))
        elif isinstance(value, str):
            out[name] = value
    return out


def register_plugin_locale(plugin_id, directory):
    """Merge a plugin locale directory under the ``plugin.<id>.*`` namespace."""
    try:
        names = sorted(os.listdir(directory))
    except OSError:
        return
    for name in names:
        if not name.endswith('.json'):
            continue
        code = name[:-5]
        try:
            with open(os.path.join(directory, name), encoding='utf-8') as f:
                data = json.load(f)
        except (OSError, ValueError):
            continue
        target = _PLUGIN_LOCALES.setdefault(code, {})
        for key, value in flatten(data).items():
            target['plugin.%s.%s' % (plugin_id, key)] = value


def get_translator(lang):
    base = flatten(_load_locale(_DEFAULT_LANG))
    data = flatten(_load_locale(lang))
    extra = _PLUGIN_LOCALES.get(lang, {})
    extra_base = _PLUGIN_LOCALES.get(_DEFAULT_LANG, {})

    def t(key, **kwargs):
        value = data.get(key)
        if value is None:
            value = extra.get(key)
        if value is None:
            value = base.get(key)
        if value is None:
            value = extra_base.get(key)
        if value is None:
            return key
        if kwargs:
            try:
                return value.format(**kwargs)
            except Exception:
                return value
        return value

    return t


def _parse_accept_language(header):
    items = []
    for part in (header or '').split(','):
        part = part.strip()
        if not part:
            continue
        bits = part.split(';')
        tag = bits[0].strip().lower()
        q = 1.0
        for bit in bits[1:]:
            bit = bit.strip()
            if bit.startswith('q='):
                try:
                    q = float(bit[2:])
                except ValueError:
                    q = 0.0
        if tag:
            items.append((tag, q))
    items.sort(key=lambda x: -x[1])
    return [tag for tag, _q in items]


def negotiate_lang(header, available=None):
    codes = [item['code'] for item in (available or available_locales())]
    if not codes:
        return _DEFAULT_LANG
    wanted = _parse_accept_language(header)
    for tag in wanted:
        if tag in codes:
            return tag
        primary = tag.split('-', 1)[0]
        for code in codes:
            if code == primary or code.split('-', 1)[0] == primary:
                return code
    return _DEFAULT_LANG


def _cookie_lang(handler):
    raw = ''
    try:
        raw = handler.headers.get('Cookie', '') or ''
    except Exception:
        return ''
    for part in raw.split(';'):
        part = part.strip()
        if part.startswith('filer_lang='):
            return part[len('filer_lang='):].strip()
    return ''


def _query_lang(handler):
    try:
        from urllib.parse import parse_qs, urlsplit
        qs = parse_qs(urlsplit(handler.path).query)
        return (qs.get('lang', [''])[0] or '').strip()
    except Exception:
        return ''


def resolve_lang(handler):
    codes = [item['code'] for item in available_locales()]
    for candidate in (_cookie_lang(handler), _query_lang(handler)):
        if candidate in codes:
            return candidate
        primary = candidate.split('-', 1)[0]
        for code in codes:
            if code.split('-', 1)[0] == primary:
                return code
    try:
        header = handler.headers.get('Accept-Language', '') or ''
    except Exception:
        header = ''
    return negotiate_lang(header, available_locales())


def lang_selector(current):
    locales = available_locales()
    if len(locales) <= 1:
        return ''
    opts = []
    for item in locales:
        code = item['code']
        selected = ' selected' if code == current else ''
        opts.append('<option value="%s"%s>%s</option>' % (
            _attr(code), selected, _text(item.get('name') or code)))
    onchange = ('document.cookie="filer_lang="+encodeURIComponent(this.value)'
                ' + ";path=/;max-age=31536000;SameSite=Lax";location.reload()')
    return ('<select class="tsel" id="langsel" onchange="' + _attr(onchange)
            + '">' + ''.join(opts) + '</select>')


def _attr(value):
    from html import escape
    return escape(str(value), quote=True)


def _text(value):
    from html import escape
    return escape(str(value), quote=False)


def render_page(page, lang):
    t = get_translator(lang)

    def repl(match):
        return t(match.group(1))

    page = re.sub(r'\{\{i18n:([A-Za-z0-9_.]+)\}\}', repl, page)
    page = page.replace('{{LANGSEL}}', lang_selector(lang))
    messages = flatten(_load_locale(lang))
    messages.update(_PLUGIN_LOCALES.get(lang, {}))
    payload = json.dumps(messages, ensure_ascii=False)
    script = '<script>window.I18N=' + payload + ';</script>'
    if 'window.I18N=' not in page:
        if '</head>' in page:
            page = page.replace('</head>', script + '</head>', 1)
        elif '<body' in page:
            page = page.replace('<body', script + '<body', 1)
        else:
            page = script + page
    try:
        page = re.sub(r'<html([^>]*?)\blang="[^"]*"',
                      lambda m: '<html' + m.group(1) + 'lang="' + _attr(lang) + '"',
                      page, count=1)
    except Exception:
        pass
    return page


_PLACEHOLDER_RE = re.compile(r'\{(\w+)\}')


def validate_locales():
    """Return a list of human-readable locale validation errors."""
    errors = []
    en = _load_locale(_DEFAULT_LANG)
    en_keys = flatten(en)
    if not en_keys:
        return ['en.json: no translation keys found']
    try:
        names = sorted(os.listdir(_LOCALES_DIR))
    except OSError as exc:
        return ['locales directory: %s' % exc]
    for name in names:
        if not name.endswith('.json'):
            continue
        code = name[:-5]
        path = os.path.join(_LOCALES_DIR, name)
        try:
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
        except (OSError, ValueError) as exc:
            errors.append('%s: invalid JSON: %s' % (name, exc))
            continue
        meta = data.get('_meta') or {}
        for field in ('name', 'code', 'dir'):
            if not meta.get(field):
                errors.append('%s: _meta.%s is missing' % (name, field))
        if meta.get('code') and meta.get('code') != code:
            errors.append('%s: _meta.code is %r, expected %r'
                          % (name, meta.get('code'), code))
        keys = flatten(data)
        for key in sorted(set(en_keys) - set(keys)):
            errors.append('%s: missing key %s' % (name, key))
        for key in sorted(set(keys) - set(en_keys)):
            errors.append('%s: extra key %s' % (name, key))
        for key in sorted(set(en_keys) & set(keys)):
            value = keys[key]
            if not value:
                errors.append('%s: empty value for %s' % (name, key))
                continue
            if value != value.strip():
                errors.append('%s: leading/trailing whitespace for %s'
                              % (name, key))
            expected = set(_PLACEHOLDER_RE.findall(en_keys[key]))
            actual = set(_PLACEHOLDER_RE.findall(value))
            if expected != actual:
                errors.append('%s: placeholder mismatch for %s (%r != %r)'
                              % (name, key, sorted(actual), sorted(expected)))
    return errors


def _main(argv):
    if len(argv) != 1 or argv[0] != 'check':
        print('usage: python3 -m dls.i18n check')
        return 2
    errors = validate_locales()
    if errors:
        for error in errors:
            print(error)
        return 1
    locales = available_locales()
    print('OK: %d locales, %d keys'
          % (len(locales), len(flatten(_load_locale(_DEFAULT_LANG)))))
    return 0


if __name__ == '__main__':
    import sys
    raise SystemExit(_main(sys.argv[1:]))
