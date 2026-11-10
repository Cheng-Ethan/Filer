import hashlib
import html
import ipaddress
import json
import mimetypes
import os
import re
import socket
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser

from .templates import _ARTICLE_TEMPLATE

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CACHE = os.path.join(_ROOT, 'cache', 'articles')
_IMG_CACHE = os.path.join(_CACHE, 'img')
_TTL = 3600
_MAX_BYTES = 8 * 1024 * 1024
_MAX_IMG = 8 * 1024 * 1024
_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
       '(KHTML, like Gecko) Chrome/122.0 Safari/537.36')
_ALLOWED = {
    'p', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li',
    'blockquote', 'pre', 'code', 'table', 'thead', 'tbody', 'tr', 'td', 'th',
    'strong', 'b', 'em', 'i', 'span', 'section', 'div', 'img', 'a', 'hr',
    'figure', 'figcaption',
}
_VOID = {'br', 'img', 'hr'}


def _validate_url(url):
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ('http', 'https') or not parts.hostname:
        raise ValueError('只支持 http/https 公开链接')
    if parts.port and parts.port not in (80, 443):
        raise ValueError('只支持 80/443 端口')
    try:
        infos = socket.getaddrinfo(parts.hostname, parts.port or 443)
    except OSError:
        raise ValueError('域名无法解析')
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            raise ValueError('不允许访问内网地址')
    return url


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _fetch(url, referer=None, max_bytes=_MAX_BYTES, timeout=20):
    _validate_url(url)
    headers = {'User-Agent': _UA,
               'Accept': 'text/html,application/xhtml+xml,image/*,*/*;q=0.8'}
    if referer:
        headers['Referer'] = referer
    req = urllib.request.Request(url, headers=headers)
    opener = urllib.request.build_opener(_SafeRedirect)
    with opener.open(req, timeout=timeout) as resp:
        data = resp.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ValueError('内容过大')
        return data, resp.headers.get('Content-Type', ''), resp.geturl()


class _ContentParser(HTMLParser):
    def __init__(self, base_url, fragment=False):
        super().__init__(convert_charrefs=True)
        self.base = base_url
        self.active = fragment
        self.found = fragment
        self.target = None
        self.depth = 0
        self.skip = 0
        self.parts = []
        self.texts = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        a = dict(attrs)
        if not self.active:
            if ((tag == 'div' and a.get('id') == 'js_content')
                    or tag in ('article', 'main')):
                self.active = True
                self.found = True
                self.target = tag
                self.depth = 1
            return
        if tag in ('script', 'style', 'noscript', 'template'):
            self.skip += 1
            return
        if self.skip:
            return
        if tag == self.target:
            self.depth += 1
        if tag in _ALLOWED:
            self.parts.append(self._render_start(tag, a))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if not self.active:
            return
        if tag in ('script', 'style', 'noscript', 'template') and self.skip:
            self.skip -= 1
            return
        if self.skip:
            return
        if tag == self.target:
            self.depth -= 1
            if self.depth <= 0:
                self.active = False
                return
        if tag in _ALLOWED and tag not in _VOID:
            self.parts.append('</%s>' % tag)

    def handle_data(self, data):
        if self.active and not self.skip:
            self.parts.append(html.escape(data, quote=False))
            self.texts.append(data)

    def _render_start(self, tag, a):
        if tag == 'img':
            src = a.get('data-src') or a.get('src') or ''
            if src.startswith('//'):
                src = 'https:' + src
            elif src and not src.startswith(('http://', 'https://')):
                src = urllib.parse.urljoin(self.base, src)
            if not src:
                return ''
            proxy = '/article/img?' + urllib.parse.urlencode({'u': src})
            alt = html.escape(a.get('alt', ''), quote=True)
            return '<img src="%s" alt="%s" loading="lazy">' % (
                html.escape(proxy, quote=True), alt)
        if tag == 'a':
            href = a.get('href', '')
            if href.startswith(('http://', 'https://')):
                return '<a href="%s" target="_blank" rel="noopener">' % html.escape(
                    href, quote=True)
            return '<a>'
        if tag in ('td', 'th'):
            extra = ''
            for key in ('colspan', 'rowspan'):
                val = a.get(key)
                if val and val.isdigit():
                    extra += ' %s="%s"' % (key, val)
            return '<%s%s>' % (tag, extra)
        if tag in _VOID:
            return '<%s>' % tag
        return '<%s>' % tag


def _clean_text(value):
    value = re.sub(r'<[^>]+>', ' ', value or '')
    return re.sub(r'\s+', ' ', html.unescape(value)).strip()


def _meta(page, name):
    for m in re.finditer(r'<meta\b[^>]*>', page, re.I):
        tag = m.group(0)
        if re.search(r'(?:property|name)=["\']%s["\']' % re.escape(name), tag, re.I):
            cm = re.search(r'content=["\']([^"\']*)', tag, re.I)
            if cm:
                return html.unescape(cm.group(1)).strip()
    return ''


def _extract_title(page):
    for value in (
            _meta(page, 'og:title'),
            _meta(page, 'twitter:title')):
        if value:
            return value
    for pat in (r'<h1[^>]*id=["\']activity-name["\'][^>]*>(.*?)</h1>',
                r'<title[^>]*>(.*?)</title>'):
        m = re.search(pat, page, re.I | re.S)
        if m:
            value = _clean_text(m.group(1))
            if value:
                return value
    return ''


def _extract_author(page):
    for value in (
            _meta(page, 'og:article:author'),
            _meta(page, 'author')):
        if value:
            return value
    for pat in (r'<a[^>]+id=["\']js_name["\'][^>]*>(.*?)</a>',
                r'<span[^>]+id=["\']js_author_name["\'][^>]*>(.*?)</span>'):
        m = re.search(pat, page, re.I | re.S)
        if m:
            value = _clean_text(m.group(1))
            if value:
                return value
    return ''


def _extract_globol_detail(page):
    """提取同花顺页面内嵌的 GLOBOL_INFO.detailContent（正文常在此 JSON 中）。"""
    m = re.search(r'detailContent\s*:\s*\{', page)
    if not m:
        return None
    start = page.find('{', m.start())
    if start < 0:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(page)):
        ch = page[i]
        if in_str:
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(page[start:i + 1])
                except Exception:
                    return None
    return None


def fetch_article(url):
    url = (url or '').strip()
    if not url:
        raise ValueError('请输入文章链接')
    if len(url) > 2000:
        raise ValueError('链接过长')
    _validate_url(url)
    os.makedirs(_CACHE, exist_ok=True)
    key = hashlib.sha256(url.encode('utf-8')).hexdigest()
    path = os.path.join(_CACHE, key + '.json')
    if os.path.isfile(path):
        try:
            with open(path, encoding='utf-8') as f:
                cached = json.load(f)
            if time.time() - cached.get('ts', 0) < _TTL:
                return cached
        except Exception:
            pass
    try:
        data, ctype, final = _fetch(url)
    except Exception:
        if os.path.isfile(path):
            with open(path, encoding='utf-8') as f:
                return json.load(f)
        raise
    if 'html' not in (ctype or '').lower() and b'<html' not in data[:4096].lower():
        raise ValueError('目标不是网页')
    page = data.decode('utf-8', 'replace')
    detail = _extract_globol_detail(page)
    embed_html = ''
    if isinstance(detail, dict) and isinstance(detail.get('content'), str):
        embed_html = detail['content'].strip()
    parser = _ContentParser(final, fragment=bool(embed_html))
    if embed_html:
        parser.feed(embed_html)
    else:
        parser.feed(page)
    text = re.sub(r'\s+', ' ', ''.join(parser.texts)).strip()
    if not parser.found or not text:
        raise ValueError('未能识别文章正文（可能需要登录，或页面结构不支持）')
    detail_title = detail.get('title') if isinstance(detail, dict) else ''
    detail_source = detail.get('source') if isinstance(detail, dict) else ''
    article = {
        'url': url,
        'final': final,
        'title': _clean_text(detail_title) or _extract_title(page) or final,
        'author': _extract_author(page) or _clean_text(detail_source),
        'html': ''.join(parser.parts),
        'text': text,
        'ts': time.time(),
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(article, f, ensure_ascii=False)
    return article


def article_text_file(article):
    os.makedirs(_CACHE, exist_ok=True)
    key = hashlib.sha256(article['url'].encode('utf-8')).hexdigest()
    path = os.path.join(_CACHE, key + '.txt')
    text = article.get('text', '')
    try:
        with open(path, encoding='utf-8') as f:
            if f.read() == text:
                return path
    except OSError:
        pass
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
    return path


def fetch_image(url):
    _validate_url(url)
    key = hashlib.sha256(url.encode('utf-8')).hexdigest()
    for name in os.listdir(_IMG_CACHE) if os.path.isdir(_IMG_CACHE) else []:
        if name.startswith(key + '.'):
            path = os.path.join(_IMG_CACHE, name)
            ctype = mimetypes.guess_type(path)[0] or 'image/jpeg'
            return path, ctype
    try:
        data, ctype, _ = _fetch(url, referer='https://mp.weixin.qq.com/',
                                max_bytes=_MAX_IMG, timeout=20)
    except Exception:
        data, ctype, _ = _fetch(url, max_bytes=_MAX_IMG, timeout=20)
    main = (ctype or '').split(';')[0].lower()
    if not main.startswith('image/'):
        raise ValueError('目标不是图片')
    ext = {'image/jpeg': '.jpg', 'image/png': '.png', 'image/gif': '.gif',
           'image/webp': '.webp', 'image/bmp': '.bmp'}.get(main, '.img')
    os.makedirs(_IMG_CACHE, exist_ok=True)
    path = os.path.join(_IMG_CACHE, key + ext)
    with open(path, 'wb') as f:
        f.write(data)
    return path, main


class ArticleMixin:
    def _serve_read(self):
        qs = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        url = qs.get('url', [''])[0].strip()
        if not url:
            self._send_html(
                '<!DOCTYPE html><meta charset="utf-8"><meta name="viewport" '
                'content="width=device-width,initial-scale=1">'
                '<body style="font-family:system-ui,sans-serif;padding:24px">'
                '<h2>读文章</h2><form action="/read" method="get">'
                '<input name="url" type="url" style="width:70%;height:38px" '
                'placeholder="粘贴公众号或网页文章链接" required> '
                '<button type="submit">读取</button></form>'
                '<p><a href="/">返回文件列表</a></p></body>')
            return
        try:
            article = fetch_article(url)
        except Exception as e:
            self._send_html(
                '<!DOCTYPE html><meta charset="utf-8"><meta name="viewport" '
                'content="width=device-width,initial-scale=1">'
                '<body style="font-family:system-ui,sans-serif;padding:24px">'
                '<h2>读取失败</h2><p>%s</p><p><a href="/read?url=%s">重试</a> · '
                '<a href="/">返回文件列表</a></p></body>'
                % (html.escape(str(e)), html.escape(urllib.parse.quote(url))))
            return
        title = html.escape(article.get('title') or '未命名文章')
        author = html.escape(article.get('author') or '')
        meta = ' · '.join(x for x in (author, '来源：' + html.escape(article.get('final', ''))) if x)
        body = ('<h1 class="atitle">%s</h1><div class="ameta">%s</div>'
                '<div class="acontent">%s</div>' % (title, meta, article.get('html', '')))
        tts_url = '/article/tts?' + urllib.parse.urlencode({'url': url})
        page = (_ARTICLE_TEMPLATE
                .replace('{{FILENAME}}', title)
                .replace('{{BACK}}', '/')
                .replace('{{DL}}', html.escape(url, quote=True))
                .replace('{{NOTE}}', '')
                .replace('{{BODY}}', body))
        page = page.replace('</body>', '<script>window.TTS_URL=%s;</script></body>'
                            % json.dumps(tts_url))
        self._send_text_page(page)

    def _serve_article_img(self):
        qs = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        url = qs.get('u', [''])[0]
        if not url:
            self.send_error(400, 'Bad image url')
            return
        try:
            path, ctype = fetch_image(url)
        except Exception:
            self.send_error(404, 'Image fetch failed')
            return
        try:
            with open(path, 'rb') as f:
                data = f.read()
        except OSError:
            self.send_error(404, 'Image not found')
            return
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'private, max-age=3600')
        self.end_headers()
        self.wfile.write(data)

    def _serve_article_tts(self):
        qs = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        url = qs.get('url', [''])[0]
        if not url:
            self._send_json({'ok': False, 'error': '缺少文章链接'}, status=400)
            return
        try:
            article = fetch_article(url)
            path = article_text_file(article)
        except Exception as e:
            self._send_json({'ok': False, 'error': str(e)}, status=400)
            return
        try:
            rate = float(qs.get('rate', ['1'])[0])
        except (TypeError, ValueError):
            rate = 1.0
        rate = max(0.5, min(2.0, rate))
        voice = qs.get('voice', [''])[0]
        if qs.get('status'):
            self._tts_status_for_path(path, voice, rate)
            return
        self._tts_from_path(path, voice, rate)
