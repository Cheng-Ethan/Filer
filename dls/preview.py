import getpass
import html
import json
import mimetypes
import os
import posixpath
import urllib.parse
import zipfile

from .config import (_ALLOWED_ENCODINGS, _MAX_TEXT_PREVIEW_BYTES,
                     _preview_kind)
from .office import (_office_text, docx_blocks, office_pdf,
                     office_pdf_page, office_pdf_page_count)
from .providers import REGISTRY, EditContext
from .templates import (_BROWSE_TEMPLATE, _ICON_DEL, _ICON_DL, _ICON_INFO,
                        _ICON_PREVIEW, _INFO_JS, _INFO_MODAL,
                        _DOC_PREVIEW_TEMPLATE, _PAGES_PREVIEW_TEMPLATE, _PDF_PREVIEW_TEMPLATE,
                        _PREVIEW_TEMPLATE, _TEXT_PREVIEW_TEMPLATE, _TTS_JS,
                        _WRAP_TEMPLATE)
from .textenc import (_clip_text, _decode_bytes, _detect_encoding,
                      _detect_file_encoding)
from .ui import BASE_CSS, FONT_STACK

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PDFJS_VIEWER = os.path.join(_ROOT, 'static', 'pdfjs', 'web', 'viewer.html')


class PreviewMixin:
    def _serve_preview(self):
        t = self._t()
        base = os.path.abspath(self.directory) if hasattr(self, 'directory') else os.getcwd()
        qs = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        target = qs.get('dir', ['/'])[0] or '/'
        if not target.startswith('/'):
            target = '/' + target
        target_dir = os.path.abspath(os.path.join(base, target.lstrip('/')))
        if not target_dir.startswith(base + os.sep) and target_dir != base:
            self.send_error(403, 'Forbidden path')
            return
        name = qs.get('name', [''])[0]
        if not name or name in ('.', '..') or '/' in name or '\\' in name:
            self.send_error(400, 'Bad filename')
            return
        full = os.path.join(target_dir, name)
        if not os.path.isfile(full):
            self.send_error(404, 'Not found')
            return
        if not os.access(full, os.R_OK):
            self._send_file_forbidden(full, name, target)
            return

        edit = self._edit_link(name, target, full)
        provider = REGISTRY.find_preview(name, full)
        if provider:
            try:
                page = provider.render(EditContext(
                    self, name, target, target_dir, full))
            except Exception as e:
                self._preview_message(str(e), name, target)
                return
            self._send_html(page)
            return
        kind = _preview_kind(name)
        if kind is None and _detect_file_encoding(full):
            kind = 'text'
        if kind is None:
            self._preview_message(t('preview.unsupported'), name, target)
            return

        enc = qs.get('enc', [''])[0].lower()
        if enc not in _ALLOWED_ENCODINGS:
            enc = ''
        rel = (target.rstrip('/') + '/' + name) if target != '/' else '/' + name
        url_path = urllib.parse.quote(urllib.parse.unquote(rel), safe='/')
        dl = url_path + '?dl=1'
        back = html.escape(target or '/', quote=True)

        if kind == 'markdown':
            try:
                with open(full, 'rb') as f:
                    raw = f.read(_MAX_TEXT_PREVIEW_BYTES + 1)
            except OSError:
                self.send_error(404, 'Read failed')
                return
            detected = enc or _detect_encoding(raw) or 'utf-8'
            text = _clip_text(_decode_bytes(raw, detected))
            payload = json.dumps(text).replace('</', '<\\/')
            md_base = urllib.parse.quote(target, safe='/')
            if not md_base.endswith('/'):
                md_base += '/'
            base_payload = json.dumps(md_base).replace('</', '<\\/')
            page = _PREVIEW_TEMPLATE.replace('{{MD_TEXT}}', payload) \
                .replace('{{MD_BASE}}', base_payload) \
                .replace('{{FILENAME}}', html.escape(name)) \
                .replace('{{BACK}}', back) \
                .replace('{{DL}}', html.escape(dl, quote=True)) \
                .replace('{{EDIT}}', edit)
            self._send_text_page(page)
            return

        if kind == 'text':
            try:
                with open(full, 'rb') as f:
                    raw = f.read(_MAX_TEXT_PREVIEW_BYTES + 1)
            except OSError:
                self.send_error(404, 'Read failed')
                return
            truncated = len(raw) > _MAX_TEXT_PREVIEW_BYTES
            if truncated:
                raw = raw[:_MAX_TEXT_PREVIEW_BYTES]
            detected = enc or _detect_encoding(raw) or 'utf-8'
            text = _clip_text(_decode_bytes(raw, detected))
            if truncated:
                text += '\n\n' + t('preview.too_large')
            links = ''.join(
                '<a class="%s" href="/preview?%s">%s</a>' % (
                    'on' if e == detected else '',
                    urllib.parse.urlencode({'dir': target, 'name': name, 'enc': e}), e)
                for e in ('utf-8', 'gb18030', 'big5', 'utf-16-le')
            )
            page = (_TEXT_PREVIEW_TEMPLATE
                    .replace('{{FILENAME}}', html.escape(name))
                    .replace('{{ENC_LINKS}}', links)
                    .replace('{{BACK}}', back)
                    .replace('{{DL}}', html.escape(dl, quote=True))
                    .replace('{{EDIT}}', edit)
                    .replace('{{NOTE}}', '')
                    .replace('{{TEXT}}', html.escape(text, quote=False)))
            self._send_text_page(page)
            return

        if kind in ('xlsx', 'pptx', 'doc', 'rtf'):
            pdf = office_pdf(full)
            if pdf:
                if os.path.isfile(_PDFJS_VIEWER):
                    pdf_url = '/officepdf?' + urllib.parse.urlencode(
                        {'dir': target, 'name': name})
                    viewer = ('/pdfjs/web/viewer.html?file='
                              + urllib.parse.quote(pdf_url, safe=''))
                    note = '<div class="note">' + t('preview.pdf_note') + '</div>'
                    page = (_PDF_PREVIEW_TEMPLATE
                            .replace('{{FILENAME}}', html.escape(name))
                            .replace('{{BACK}}', back)
                            .replace('{{DL}}', html.escape(dl, quote=True))
                            .replace('{{EDIT}}', edit)
                            .replace('{{NOTE}}', note)
                            .replace('{{PDFURL}}', html.escape(viewer, quote=True)))
                    self._send_text_page(page)
                    return
                count = office_pdf_page_count(pdf)
                if count:
                    limit = min(count, 100)
                    pages = ''.join(
                        '<img loading="lazy" src="/officepage?%s" alt="%s">' % (
                            html.escape(urllib.parse.urlencode(
                                {'dir': target, 'name': name, 'page': i}),
                                quote=True), t('preview.page_alt', page=i))
                        for i in range(1, limit + 1))
                    more = (' ' + t('preview.pages_more', limit=100)) if count > limit else ''
                    note = '<div class="note">' + t('preview.pages_note', count=count, more=more) + '</div>'
                    page = (_PAGES_PREVIEW_TEMPLATE
                            .replace('{{FILENAME}}', html.escape(name))
                            .replace('{{BACK}}', back)
                            .replace('{{DL}}', html.escape(dl, quote=True))
                            .replace('{{EDIT}}', edit)
                            .replace('{{NOTE}}', note)
                            .replace('{{PAGES}}', pages))
                    self._send_text_page(page)
                    return
                pdf_url = '/officepdf?' + urllib.parse.urlencode(
                    {'dir': target, 'name': name})
                note = '<div class="note">' + t('preview.pdf_note2') + '</div>'
                page = (_PDF_PREVIEW_TEMPLATE
                        .replace('{{FILENAME}}', html.escape(name))
                        .replace('{{BACK}}', back)
                        .replace('{{DL}}', html.escape(dl, quote=True))
                        .replace('{{EDIT}}', edit)
                        .replace('{{NOTE}}', note)
                        .replace('{{PDFURL}}', html.escape(pdf_url, quote=True)))
                self._send_text_page(page)
                return

        if kind == 'docx':
            try:
                blocks = docx_blocks(full)
            except Exception as e:
                self._preview_message(t('preview.parse_failed', error=e), name, target)
                return
            def media_url(part):
                q = urllib.parse.urlencode(
                    {'dir': target, 'name': name, 'part': part})
                return html.escape(q, quote=True)

            def cell_html(cell_blocks):
                out = []
                for ctype, cval in cell_blocks:
                    if ctype == 'text':
                        out.append(html.escape(cval, quote=False).replace('\n', '<br>'))
                    elif ctype == 'image':
                        out.append('<img src="/docmedia?' + media_url(cval) + '" alt="">')
                return ''.join(out)

            body = []
            for typ, val in blocks:
                if typ == 'text':
                    body.append('<p>' + html.escape(val, quote=False).replace('\n', '<br>') + '</p>')
                elif typ == 'image':
                    body.append('<img src="/docmedia?' + media_url(val) + '" alt="">')
                elif typ == 'table':
                    rows_html = []
                    for row in val:
                        tds = []
                        for colspan, cell_blocks in row:
                            attr = ' colspan="%d"' % colspan if colspan > 1 else ''
                            tds.append('<td%s>%s</td>' % (attr, cell_html(cell_blocks)))
                        rows_html.append('<tr>' + ''.join(tds) + '</tr>')
                    body.append('<table>' + ''.join(rows_html) + '</table>')
            note = '<div class="note">' + t('preview.docx_note') + '</div>'
            page = (_DOC_PREVIEW_TEMPLATE
                    .replace('{{FILENAME}}', html.escape(name))
                    .replace('{{BACK}}', back)
                    .replace('{{DL}}', html.escape(dl, quote=True))
                    .replace('{{EDIT}}', edit)
                    .replace('{{ENC_LINKS}}', '')
                    .replace('{{NOTE}}', note)
                    .replace('{{BODY}}', ''.join(body) or ('<p>' + t('preview.empty_body') + '</p>')))
            self._send_text_page(page)
            return

        if kind in ('docx', 'xlsx', 'pptx', 'doc', 'rtf'):
            try:
                text = _clip_text(_office_text(full, kind))
            except Exception as e:
                self._preview_message(t('preview.parse_failed', error=e), name, target)
                return
            note = '<div class="note">' + t('preview.text_note') + '</div>'
            page = (_TEXT_PREVIEW_TEMPLATE
                    .replace('{{FILENAME}}', html.escape(name))
                    .replace('{{ENC_LINKS}}', '')
                    .replace('{{BACK}}', back)
                    .replace('{{DL}}', html.escape(dl, quote=True))
                    .replace('{{EDIT}}', edit)
                    .replace('{{NOTE}}', note)
                    .replace('{{TEXT}}', html.escape(text, quote=False)))
            self._send_text_page(page)
            return

        raw_url = html.escape(url_path + '?raw=1', quote=True)
        if kind == 'svg':
            self._send_wrap(name, back, dl, '<img src="%s" alt="">' % raw_url, edit)
            return
        if kind == 'html':
            self._send_wrap(name, back, dl,
                            '<iframe sandbox src="%s" title="preview"></iframe>' % raw_url, edit)
            return
        if kind == 'audio':
            self._send_wrap(name, back, dl,
                            '<audio controls src="%s"></audio>' % raw_url, edit)
            return
        if kind == 'video':
            self._send_wrap(name, back, dl,
                            '<video controls src="%s"></video>' % raw_url, edit)
            return
        if kind == 'image':
            ctype = mimetypes.guess_type(full)[0] or 'application/octet-stream'
            self._send_file_bytes(full, ctype, name)
            return
        if kind == 'pdf':
            self._send_file_bytes(full, 'application/pdf', name)
            return

        self._preview_message(t('preview.unsupported'), name, target)
    def _send_text_page(self, page):
        page = page.replace('</body>', '<script>' + _TTS_JS + '</script></body>')
        self._send_html(page)
    def _send_wrap(self, name, back, dl, body, edit=''):
        page = (_WRAP_TEMPLATE
                .replace('{{FILENAME}}', html.escape(name))
                .replace('{{BACK}}', back)
                .replace('{{DL}}', html.escape(dl, quote=True))
                .replace('{{EDIT}}', edit)
                .replace('{{BODY}}', body))
        self._send_html(page)
    def _serve_pdfjs(self):
        base = os.path.join(_ROOT, 'static', 'pdfjs')
        rel = urllib.parse.unquote(
            urllib.parse.urlsplit(self.path).path[len('/pdfjs/'):])
        if not rel or '..' in rel.split('/') or rel.startswith('/'):
            self.send_error(404, 'Not found')
            return
        full = os.path.abspath(os.path.join(base, rel))
        if not (full == base or full.startswith(base + os.sep)):
            self.send_error(403, 'Forbidden path')
            return
        if not os.path.isfile(full):
            self.send_error(404, 'Not found')
            return
        ctype = mimetypes.guess_type(full)[0] or 'application/octet-stream'
        if full.endswith(('.js', '.mjs')):
            ctype = 'text/javascript; charset=utf-8'
        try:
            with open(full, 'rb') as f:
                data = f.read()
        except OSError:
            self.send_error(404, 'Not found')
            return
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'public, max-age=86400')
        self.end_headers()
        self.wfile.write(data)

    def _serve_officepage(self):
        base = os.path.abspath(self.directory) if hasattr(self, 'directory') else os.getcwd()
        qs = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        target = qs.get('dir', ['/'])[0] or '/'
        if not target.startswith('/'):
            target = '/' + target
        target_dir = os.path.abspath(os.path.join(base, target.lstrip('/')))
        if not (target_dir == base or target_dir.startswith(base + os.sep)):
            self.send_error(403, 'Forbidden path')
            return
        name = qs.get('name', [''])[0]
        if not name or name in ('.', '..') or '/' in name or '\\' in name:
            self.send_error(400, 'Bad filename')
            return
        full = os.path.join(target_dir, name)
        if not os.path.isfile(full):
            self.send_error(404, 'Not found')
            return
        pdf = office_pdf(full)
        if not pdf:
            self.send_error(503, 'PDF conversion unavailable')
            return
        try:
            page = int(qs.get('page', ['1'])[0])
        except (TypeError, ValueError):
            page = 1
        count = office_pdf_page_count(pdf)
        if page < 1 or page > count:
            self.send_error(404, 'Page not found')
            return
        img = office_pdf_page(pdf, page)
        if not img:
            self.send_error(503, 'Page render unavailable')
            return
        try:
            with open(img, 'rb') as f:
                data = f.read()
        except OSError:
            self.send_error(404, 'Page not found')
            return
        self.send_response(200)
        self.send_header('Content-Type', 'image/jpeg')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'private, max-age=3600')
        self.end_headers()
        self.wfile.write(data)

    def _serve_office_pdf(self):
        base = os.path.abspath(self.directory) if hasattr(self, 'directory') else os.getcwd()
        qs = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        target = qs.get('dir', ['/'])[0] or '/'
        if not target.startswith('/'):
            target = '/' + target
        target_dir = os.path.abspath(os.path.join(base, target.lstrip('/')))
        if not (target_dir == base or target_dir.startswith(base + os.sep)):
            self.send_error(403, 'Forbidden path')
            return
        name = qs.get('name', [''])[0]
        if not name or name in ('.', '..') or '/' in name or '\\' in name:
            self.send_error(400, 'Bad filename')
            return
        full = os.path.join(target_dir, name)
        if not os.path.isfile(full):
            self.send_error(404, 'Not found')
            return
        pdf = office_pdf(full)
        if not pdf:
            self.send_error(503, 'PDF conversion unavailable')
            return
        size = os.path.getsize(pdf)
        self.send_response(200)
        self.send_header('Content-Type', 'application/pdf')
        self.send_header('Content-Length', str(size))
        self.send_header('Content-Disposition', 'inline; filename="document.pdf"')
        self.send_header('Cache-Control', 'private, max-age=3600')
        self.end_headers()
        try:
            with open(pdf, 'rb') as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _send_file_forbidden(self, full, name, target):
        t = self._t()
        try:
            st = os.stat(full)
            mode = oct(st.st_mode & 0o777)[2:]
            try:
                import pwd
                owner = pwd.getpwuid(st.st_uid).pw_name
            except Exception:
                owner = str(st.st_uid)
        except OSError:
            mode, owner = '?', '?'
        try:
            user = getpass.getuser()
        except Exception:
            user = '?'
        msg = t('preview.permission_message', user=user, owner=owner, mode=mode)
        hint = t('preview.permission_hint')
        perm_title = t('preview.permission_title')
        page = ('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                '<title>' + perm_title + '</title><style>'
                'body{font-family:' + FONT_STACK + ';'
                'background:#f1f5f9;color:#1e293b;padding:24px;}'
                '.box{max-width:760px;margin:40px auto;background:#fff;'
                'border-radius:12px;padding:24px;box-shadow:0 2px 10px rgba(0,0,0,.08);}'
                'a{color:#2563eb;}'
                '</style></head><body><div class="box">'
                '<h2>' + perm_title + '</h2>'
                '<p>%s</p><p>%s</p>'
                '<p><a href="%s">' + t('preview.back_dir') + '</a></p>'
                '</div></body></html>') % (
                    html.escape(msg), html.escape(hint),
                    html.escape(target or '/', quote=True))
        page = page.replace('<style>', '<style>' + BASE_CSS, 1)
        body = page.encode('utf-8')
        self.send_response(403)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_docmedia(self):
        base = os.path.abspath(self.directory) if hasattr(self, 'directory') else os.getcwd()
        qs = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        target = qs.get('dir', ['/'])[0] or '/'
        if not target.startswith('/'):
            target = '/' + target
        target_dir = os.path.abspath(os.path.join(base, target.lstrip('/')))
        if not (target_dir == base or target_dir.startswith(base + os.sep)):
            self.send_error(403, 'Forbidden path')
            return
        name = qs.get('name', [''])[0]
        if not name or name in ('.', '..') or '/' in name or '\\' in name:
            self.send_error(400, 'Bad filename')
            return
        part = qs.get('part', [''])[0]
        if (not part.startswith('word/media/') or '..' in part.split('/')
                or part.startswith('/')):
            self.send_error(400, 'Bad media part')
            return
        ctype = {
            '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
            '.gif': 'image/gif', '.bmp': 'image/bmp', '.webp': 'image/webp',
            '.svg': 'image/svg+xml',
        }.get(os.path.splitext(part)[1].lower())
        if not ctype:
            self.send_error(415, 'Unsupported media')
            return
        full = os.path.join(target_dir, name)
        if not os.path.isfile(full):
            self.send_error(404, 'Not found')
            return
        try:
            with zipfile.ZipFile(full) as z:
                info = z.getinfo(part)
                if info.file_size > 20 * 1024 * 1024:
                    self.send_error(413, 'Media too large')
                    return
                data = z.read(part)
        except (KeyError, OSError, zipfile.BadZipFile):
            self.send_error(404, 'Media not found')
            return
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'private, max-age=3600')
        self.end_headers()
        self.wfile.write(data)

    def _preview_message(self, msg, name, target):
        rel = (target.rstrip('/') + '/' + name) if target != '/' else '/' + name
        dl = urllib.parse.quote(urllib.parse.unquote(rel), safe='/') + '?dl=1'
        page = (_TEXT_PREVIEW_TEMPLATE
                .replace('{{FILENAME}}', html.escape(name))
                .replace('{{ENC_LINKS}}', '')
                .replace('{{BACK}}', html.escape(target or '/', quote=True))
                .replace('{{DL}}', html.escape(dl, quote=True))
                .replace('{{EDIT}}', '')
                .replace('{{NOTE}}', '<div class="note">%s</div>' % html.escape(msg))
                .replace('{{TEXT}}', ''))
        self._send_html(page)
    def _serve_browse(self, fpath, path):
        t = self._t()
        base = os.path.abspath(self.directory) if hasattr(self, 'directory') else os.getcwd()
        abs_path = os.path.abspath(fpath)
        if not (abs_path == base or abs_path.startswith(base + os.sep)):
            self.send_error(403, 'Forbidden path')
            return
        if not os.path.isfile(abs_path):
            self.send_error(404, 'Not found')
            return
        directory = posixpath.dirname(path)
        name = os.path.basename(path)
        dir_disp = urllib.parse.unquote(directory or '/')
        name_disp = urllib.parse.unquote(name)
        fname = html.escape(name_disp)
        url_path = urllib.parse.quote(urllib.parse.unquote(path), safe='/')

        kind = _preview_kind(name_disp)
        if kind is None and _detect_file_encoding(abs_path):
            kind = 'text'
        if kind in ('text', 'markdown', 'docx', 'xlsx', 'pptx', 'doc', 'rtf'):
            # These formats already have a full preview page with their own
            # toolbar. Redirect instead of nesting two toolbars in an iframe.
            target = '/preview?' + urllib.parse.urlencode(
                {'dir': dir_disp, 'name': name_disp})
            self.send_response(302)
            self.send_header('Location', target)
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        src = url_path + '?raw=1'
        fallback = directory or '/'
        if not fallback.startswith('/'):
            fallback = '/' + fallback

        prev = ''
        if kind:
            prev = ('<a class="btn btn-prev" href="/preview?'
                    + urllib.parse.urlencode({'dir': dir_disp, 'name': name_disp})
                    + '" title="' + t('list.preview_title') + '">' + _ICON_PREVIEW + '</a>')

        dl = '<a class="btn btn-dl" href="' + url_path + '?dl=1" title="' + t('common.download') + '">' + _ICON_DL + '</a>'

        info_btn = (
            f'<button class="btn btn-info" type="button" title="{html.escape(t("preview.more_info", name=name_disp), quote=True)}" '
            f'data-dir="{html.escape(dir_disp, quote=True)}" '
            f'data-name="{html.escape(name_disp, quote=True)}" onclick="showInfo(this)">' + _ICON_INFO + '</button>'
        )

        confirmed = html.escape(t("preview.delete_confirm", name=name_disp), quote=True)
        delete_title = html.escape(t('common.delete'), quote=True)
        delete_form = (
            f'<form class="act-form" action="/delete" method="post" '
            f'onsubmit="return confirm(\'{confirmed}\')">'
            f'<input type="hidden" name="dir" value="{html.escape(dir_disp, quote=True)}">'
            f'<input type="hidden" name="name" value="{html.escape(name_disp, quote=True)}">'
            f'<button class="btn btn-del" type="submit" title="{delete_title}">' + _ICON_DEL + '</button></form>'
        )

        page = _BROWSE_TEMPLATE \
            .replace('{{FILENAME}}', fname) \
            .replace('{{FALLBACK}}', html.escape(fallback, quote=True)) \
            .replace('{{SRC}}', html.escape(src, quote=True)) \
            .replace('{{ACTION_PREVIEW}}', prev) \
            .replace('{{ACTION_DOWNLOAD}}', dl) \
            .replace('{{ACTION_DELETE}}', info_btn + delete_form)
        page = page.replace('</body>', _INFO_MODAL + '<script>' + _INFO_JS + '</script></body>')
        self._send_html(page)

