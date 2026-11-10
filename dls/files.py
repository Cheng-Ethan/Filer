import collections
import datetime
import html
import json
import os
import posixpath
import re
import shutil
import threading
import urllib.parse

from .config import (FORCE_DOWNLOAD_EXTS, MAX_UPLOAD_BYTES, MAX_RECENT_DIRS,
                     _preview_kind)
from .templates import (_BROWSE_TEMPLATE, _ICON_DEL, _ICON_DL, _ICON_HELP,
                        _ICON_INFO, _ICON_OPEN, _ICON_PREVIEW, _INFO_CSS,
                        _INFO_JS, _INFO_MODAL)
from .textenc import _charset_for, _detect_file_encoding
from .util import _fmt_size

_RECENT_DIRS = collections.deque(maxlen=MAX_RECENT_DIRS)
_RECENT_LOCK = threading.Lock()


def _dir_has_children(path):
    try:
        with os.scandir(path) as it:
            return next(it, None) is not None
    except OSError:
        return False


class FilesMixin:
    def forced_download(self):
        """Return download filename if this request must be a download, else None."""
        raw, _, qs = self.path.partition('?')
        if 'raw=1' in qs:
            return None  # 内联浏览：iframe 原文渲染，不强制下载
        path = urllib.parse.unquote(raw)
        ext = os.path.splitext(path)[1].lower()
        if ext in FORCE_DOWNLOAD_EXTS:
            return os.path.basename(path)
        if 'dl=1' in qs:
            fpath = self.translate_path(path)
            if os.path.isfile(fpath):
                return os.path.basename(path)
        return None
    def guess_type(self, path):
        if self.forced_download():
            return 'application/octet-stream'
        base = super().guess_type(path)
        ctype, _, charset = (base or '').partition(';')
        ctype = ctype.strip()
        if ctype in ('', 'application/octet-stream'):
            inline = 'raw=1' in self.path.partition('?')[2]
            enc = _detect_file_encoding(path) if inline else None
            if inline and enc:
                return 'text/plain; charset=' + _charset_for(enc)
            return base or 'application/octet-stream'
        if charset:
            return base
        if ctype.startswith('text/') or ctype in (
                'application/javascript', 'application/x-javascript',
                'application/json', 'application/xml', 'application/xhtml+xml',
                'application/ecmascript', 'image/svg+xml'):
            enc = _detect_file_encoding(path)
            return ctype + '; charset=' + _charset_for(enc)
        return base
    def send_head(self):
        # 强制下载类型永不返回 304：去掉条件请求头，避免浏览器复用旧缓存导致预览
        if self.forced_download():
            for h in ('If-Modified-Since', 'If-None-Match'):
                if h in self.headers:
                    del self.headers[h]
        return super().send_head()
    def _download_disposition(self):
        """RFC 5987 文件名：ASCII 回退 + filename* UTF-8，保留原始文件名且绝不带额外后缀。"""
        name = self.forced_download() or ''
        ascii_name = name.encode('ascii', 'replace').decode('ascii').replace('"', '')
        if not ascii_name:
            ascii_name = 'download'
        cd = f'attachment; filename="{ascii_name}"'
        try:
            cd += "; filename*=utf-8''" + urllib.parse.quote(name)
        except Exception:
            pass
        return cd
    def end_headers(self):
        if self.forced_download():
            self.send_header('Content-Disposition', self._download_disposition())
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
        super().end_headers()
    def list_directory(self, path):
        try:
            names = list(os.listdir(path))
        except OSError:
            return super().list_directory(path)  # 容错：回退默认实现

        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()

        self._record_recent_dir()

        rows = []
        parent = posixpath.dirname(self.path.rstrip('/')) if self.path not in ('/', '') else ''
        parent = '/' if parent in ('', '/') else parent + '/'
        if self.path not in ('/', ''):
            rows.append(self._row_link(parent, '../', '📁', '返回上级目录',
                                       open_label=None, can_dl=False))

        # 排序：目录在前、文件在后，各自按名称排序
        dirs, files = [], []
        for n in names:
            (dirs if os.path.isdir(posixpath.join(path, n)) else files).append(n)
        dirs.sort(key=str.lower)
        files.sort(key=str.lower)
        for name in dirs:
            rows.append(self._row_link(urllib.parse.quote(name + '/'), name + '/', '📁', name,
                                       open_label=None, can_dl=False,
                                       row_cls='row-dir', delete=True,
                                       dirname=self.path, name=name,
                                       dir_nonempty=_dir_has_children(
                                           posixpath.join(path, name))))
        for name in files:
            rows.append(self._row_link(urllib.parse.quote(name), name, '📄', name,
                                       open_label='👁 打开',
                                       preview=bool(_preview_kind(name)),
                                           delete=True,
                                           dirname=self.path, name=name))

        body = (
            '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>文件下载</title>'
            '<style>'
            '*{box-sizing:border-box;}'
            'body{font-family:system-ui,"Microsoft YaHei",sans-serif;margin:0;padding:24px 24px 64px;background:#f1f5f9;color:#1e293b;}'
            '.box{max-width:860px;margin:0 auto;background:#fff;border-radius:12px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,.08);}'
            'h1{font-size:18px;margin:0;color:#1e3a5f;}'
            '.navbar{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:0 0 12px;}'
            '.recent{font-size:13px;color:#475569;margin:0 0 12px;padding:8px 10px;background:#f8fafc;border-radius:8px;word-break:break-all;}'
            '.recent a{color:#0f766e;text-decoration:none;font-weight:600;}'
            '.recent a:hover{text-decoration:underline;}'
            '.recent .sep{color:#cbd5e1;margin:0 4px;}'
            '.row{display:block;padding:12px 8px;border-bottom:1px solid #eef2f7;}'
            '.row-dir{background:#f8fafc;}'
            '.line1{display:flex;align-items:center;gap:10px;min-width:0;}'
            '.icon{font-size:17px;flex-shrink:0;}'
            '.name{flex:1;min-width:0;font-size:15px;color:#2563eb;word-break:break-all;text-decoration:none;display:block;cursor:pointer;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}'
            '.name:hover{text-decoration:underline;color:#1d4ed8;}'
            '.row-dir .name{color:#16a34a;font-weight:600;}'
            '.row-dir .name:hover{text-decoration:underline;color:#15803d;}'
            'a{text-decoration:none;}'
            'button{font:inherit;}'
            '.line2{display:none;margin-top:12px;align-items:center;gap:14px;flex-wrap:wrap;}'
            '.row:hover .line2,.row.active .line2{display:flex;}'
            '.actions{display:flex;align-items:center;gap:14px;flex-wrap:wrap;}'
            '.row.active{background:#eff8ff;}'
            '.rowsmark{margin-left:auto;width:42px;height:42px;padding:0;flex-shrink:0;display:inline-flex;align-items:center;justify-content:center;border-radius:8px;border:none;background:transparent;color:#94a3b8;cursor:pointer;font-size:22px;line-height:1;}'
            '.rowsmark:hover{color:#475569;background:#f1f5f9;}'
            '.rowsmark:active{background:#e2e8f0;}'
            '.btn{display:inline-flex;align-items:center;justify-content:center;gap:4px;height:38px;padding:0 14px;border-radius:8px;font-size:14px;border:1px solid #cbd5e1;color:#475569;background:#fff;white-space:nowrap;cursor:pointer;box-sizing:border-box;}'
            '.btn:hover{background:#f1f5f9;border-color:#94a3b8;}'
            '.btn-open{color:#2563eb;background:#eff6ff;border-color:#bfdbfe;}'
            '.btn-open:hover{background:#dbeafe;}'
            '.btn-dl{color:#b45309;background:#fffbeb;border-color:#fde68a;}'
            '.btn-dl:hover{background:#fef3c7;}'
            '.btn-prev{color:#7c3aed;background:#f5f3ff;border-color:#ddd6fe;}'
            '.btn-prev:hover{background:#ede9fe;}'
            '.btn-del{color:#b91c1c;background:#fef2f2;border-color:#fecaca;}'
            '.btn-del:hover{background:#fee2e2;}'
            '.btn-back{color:#334155;}'
            '.line2 .btn{width:46px;height:46px;padding:0;flex:0 0 auto;}'
            '.btn svg{width:23px;height:23px;display:block;flex-shrink:0;}'
            '.helpbtn{margin-left:auto;width:42px;height:42px;padding:0;border-radius:50%;color:#475569;background:#f8fafc;}'
            '.helpbtn svg{width:22px;height:22px;}'
            '[hidden]{display:none !important;}'
            '.legend{flex:1 1 100%;padding:8px 10px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;font-size:13px;color:#475569;display:inline-flex;align-items:center;gap:14px;flex-wrap:wrap;}'
            '.legend .lg-item{display:inline-flex;align-items:center;gap:6px;}'
            '.legend .lg-item svg{width:16px;height:16px;}'
            '.legend .lg-del{color:#dc2626;}'
            '.btn-up{color:#047857;background:#ecfdf5;border-color:#a7f3d0;}'
            '.btn-up:hover{background:#d1fae5;}'
            + _INFO_CSS +
            '.act-form{display:inline-flex;margin:0;}'
            '.upbar{display:flex;align-items:center;gap:10px;margin:0 0 16px;padding:12px;background:#f8fafc;border:1px dashed #cbd5e1;border-radius:10px;}'
            '.upbar input[type=file]{flex:1;min-width:0;font-size:14px;color:#334155;}'
            '.upnote{color:#64748b;font-size:12px;margin-top:4px;}'
            '.readbar{display:flex;gap:8px;margin:0 0 14px;padding:10px;background:#f0f9ff;border:1px solid #bae6fd;border-radius:10px;}'
            '.readbar input{flex:1;min-width:0;height:38px;border:1px solid #cbd5e1;border-radius:8px;padding:0 10px;font-size:14px;outline:none;}'
            '.readbar input:focus{border-color:#0284c7;}'
            '@media(max-width:640px){.line2{gap:10px;}.upbar{flex-wrap:wrap;}.upbar input[type=file]{flex:1 1 100%;}.upbar .btn{flex:1 1 100%;}.readbar{flex-wrap:wrap;}.readbar input{flex:1 1 100%;}.readbar .btn{flex:1 1 100%;}}'
            '.shell{position:sticky;bottom:0;z-index:30;background:#0f172a;color:#e2e8f0;border-radius:0 0 12px 12px;margin:16px -20px -20px;}'
            '.shell .shhead{display:flex;align-items:center;gap:8px;padding:8px 12px;border-bottom:1px solid #334155;font-size:13px;}'
            '.shell .shtog{height:26px;min-width:26px;padding:0 8px;border-radius:6px;border:1px solid #475569;background:#1e293b;color:#e2e8f0;cursor:pointer;font-size:13px;}'
            '.shell .shlabel{color:#64748b;}'
            '.shell .shcwd{color:#7dd3fc;word-break:break-all;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}'
            '.shell .shhelp{margin-left:auto;display:inline-flex;align-items:center;justify-content:center;width:26px;height:26px;padding:0;border-radius:50%;border:1px solid #475569;background:#1e293b;color:#e2e8f0;cursor:pointer;flex-shrink:0;}'
            '.shell .shhelp:hover{background:#334155;}'
            '.shell .shhelp svg{width:15px;height:15px;}'
            '.shell .shhint{display:flex;align-items:center;gap:6px;padding:8px 12px;border-bottom:1px solid #334155;font-size:13px;color:#7dd3fc;background:#0b1120;line-height:1.5;}'
            '.shell .shout{min-height:50vh;max-height:60vh;overflow-y:auto;overflow-x:hidden;overscroll-behavior:contain;-webkit-overflow-scrolling:touch;touch-action:pan-y;margin:0;padding:10px 12px;font-family:ui-monospace,Consolas,Menlo,monospace;font-size:13px;line-height:1.55;color:#d1fae5;white-space:pre-wrap;word-break:break-word;background:#0b1120;scrollbar-width:thin;scrollbar-color:#475569 #0b1120;}'
            '.shell .shout::-webkit-scrollbar{width:10px;height:10px;}'
            '.shell .shout::-webkit-scrollbar-track{background:#0b1120;}'
            '.shell .shout::-webkit-scrollbar-thumb{background:#475569;border-radius:5px;border:2px solid #0b1120;}'
            '.shell .shout::-webkit-scrollbar-thumb:hover{background:#64748b;}'
            '.shell .shout.collapsed{display:none;}'
            '.shell .shback{position:absolute;right:18px;bottom:60px;z-index:5;height:32px;padding:0 12px;border-radius:16px;border:1px solid #475569;background:#1e293b;color:#e2e8f0;font-size:12px;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.45);}'
            '.shell .shback:hover{background:#334155;}'
            '.shell .shinput{display:flex;align-items:center;gap:8px;padding:8px 12px;border-top:1px solid #334155;}'
            '.shell .shprompt{color:#34d399;font-weight:700;}'
            '.shell .shinput input{flex:1;min-width:0;height:34px;border-radius:6px;border:1px solid #475569;background:#1e293b;color:#e2e8f0;font-size:14px;padding:0 10px;box-sizing:border-box;outline:none;font-family:ui-monospace,Consolas,monospace;}'
            '.shell .shinput input:focus{border-color:#34d399;}'
            '.shell .shhist{margin-left:auto;display:inline-flex;align-items:center;justify-content:center;width:26px;height:26px;padding:0;border-radius:50%;border:1px solid #475569;background:#1e293b;color:#e2e8f0;cursor:pointer;flex-shrink:0;font-size:14px;}'
            '.shell .shhist:hover{background:#334155;}'
            '.shell .shhist.running{background:#450a0a;border-color:#b91c1c;color:#fecaca;}'
            '.shell #shkeybtn{margin-left:0;}'
            '.shell .shhead .shhelp{margin-left:0;}'
            '.shell .shhistpanel{background:#0b1120;border-bottom:1px solid #334155;padding:8px 12px;max-height:38vh;overflow:auto;}'
            '.shell .shsearchrow{display:flex;gap:8px;margin-bottom:8px;}'
            '.shell .shsearchrow input{flex:1;min-width:0;height:30px;border-radius:6px;border:1px solid #475569;background:#1e293b;color:#e2e8f0;font-size:13px;padding:0 10px;box-sizing:border-box;outline:none;}'
            '.shell .shsearchrow input:focus{border-color:#34d399;}'
            '.shell .shlists{display:grid;grid-template-columns:1fr 1fr;gap:12px;}'
            '.shell .shlisttitle{font-size:12px;color:#94a3b8;margin-bottom:6px;}'
            '.shell .shchips{display:flex;flex-wrap:wrap;gap:6px;}'
            '.shell .shchip{max-width:100%;text-align:left;border:1px solid #334155;background:#1e293b;color:#e2e8f0;border-radius:6px;padding:4px 8px;font-family:ui-monospace,Consolas,monospace;font-size:12px;cursor:pointer;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}'
            '.shell .shchip:hover{background:#334155;border-color:#475569;}'
            '.shell .shempty{font-size:12px;color:#64748b;}'
            '.shell .shinput .shstatus{font-size:12px;color:#fbbf24;white-space:nowrap;}'
            '.shell .shkeys{display:flex;align-items:center;gap:6px;padding:8px 12px;border-top:1px solid #334155;flex-wrap:wrap;}'
            '.shell .shkey{display:inline-flex;align-items:center;gap:5px;height:32px;padding:0 10px;border-radius:6px;border:1px solid #475569;background:#1e293b;color:#e2e8f0;font-size:13px;cursor:pointer;white-space:nowrap;flex-shrink:0;}'
            '.shell .shkey small{font-size:10px;color:#94a3b8;}'
            '.shell .shkey:hover{background:#334155;}'
            '.shell .shkey.active{background:#7f1d1d;border-color:#b91c1c;color:#fff;}'
            '.shell .shkey.active small{color:#fecaca;}'
            '@media(max-width:640px){.shell .shlists{grid-template-columns:1fr;}.shell .shkeys{gap:4px;padding:6px 8px;}.shell .shkey{height:30px;padding:0 8px;font-size:12px;}}'
            '</style></head><body><div class="box">'
            '<div class="navbar">'
            f'<a class="btn btn-back" href="{html.escape(parent, quote=True)}" '
            'onclick="if(history.length&gt;1){event.preventDefault();history.back();return false;}">← 返回上一页</a>'
            f'<h1>📁 目录 /{html.escape(urllib.parse.unquote(self.path), quote=True)}</h1>'
            '<button class="btn helpbtn" id="helpbtn" type="button" title="图标图例">' + _ICON_HELP + '</button>'
            '<div class="legend" id="legend" hidden>'
            '<span class="lg-item">' + _ICON_OPEN + '<span>打开（进入查看）</span></span>'
            '<span class="lg-item">' + _ICON_PREVIEW + '<span>预览（文本 / Markdown / Office 等）</span></span>'
            '<span class="lg-item">' + _ICON_DL + '<span>下载</span></span>'
            '<span class="lg-item lg-del">' + _ICON_DEL + '<span>删除</span></span>'
            '<span class="lg-item lg-info">' + _ICON_INFO + '<span>更多信息（文件属性）</span></span>'
            '<span class="lg-item"><span style="font-size:18px;color:#64748b;line-height:1">⋮</span><span>显示/隐藏操作按钮</span></span>'
            '<span class="lg-item"><span style="color:#16a34a">● 绿色名称 = 目录，点击即进入</span></span>'
            '</div>'
            '</div>'
            + self._recent_html()
            + '<form class="readbar" action="/read" method="get">'
            '<input type="url" name="url" placeholder="粘贴文章链接（微信公众号/网页），用本机语音朗读" required>'
            '<button class="btn btn-open" type="submit">读文章</button>'
            '</form>'
            + '<form action="/upload" method="post" enctype="multipart/form-data" class="upbar">'
            f'<input type="hidden" name="dir" value="{html.escape(urllib.parse.unquote(self.path), quote=True)}">'
            '<input type="file" name="file" multiple required>'
            '<button class="btn btn-up" type="submit">⬆ 上传到当前目录</button>'
            '</form>'
            '<div class="upnote">选中一个或多个文件后点击上传，文件将保存到当前目录。</div>'
            + ''.join(rows)
            + '</div>'
            + self._shell_html(os.path.abspath(path))
            + '<script>'
            'var hb=document.getElementById("helpbtn");'
            'var lg=document.getElementById("legend");'
            'hb.onclick=function(){lg.hidden=!lg.hidden;};'
            'document.addEventListener("click",function(e){'
            'var rows=document.querySelectorAll(".row");'
            'var m=e.target.closest(".rowsmark");'
            'if(m){var r=m.closest(".row");'
            'var on=r.classList.contains("active");'
            'for(var i=0;i<rows.length;i++)rows[i].classList.remove("active");'
            'if(!on)r.classList.add("active");'
            'return;}'
            'if(!e.target.closest(".row")){'
            'for(var i=0;i<rows.length;i++)rows[i].classList.remove("active");}});'
            '</script>'
            + '</body></html>'
        )
        self.wfile.write(body.replace('</body>', _INFO_MODAL + '<script>' + _INFO_JS + '</script></body>').encode('utf-8'))
        return None
    def _record_recent_dir(self):
        key = '/' if self.path in ('', '/') else '/' + self.path.strip('/')
        with _RECENT_LOCK:
            if key in _RECENT_DIRS:
                _RECENT_DIRS.remove(key)
            _RECENT_DIRS.append(key)
    def _recent_html(self):
        cur = '/' if self.path in ('', '/') else '/' + self.path.strip('/')
        with _RECENT_LOCK:
            entries = list(_RECENT_DIRS)
        links = []
        for d in reversed(entries):
            if d == cur:
                continue
            disp = '/' if d in ('', '/') else urllib.parse.unquote(d) + '/'
            href = urllib.parse.quote(urllib.parse.unquote(d), safe='/')
            links.append(f'<a href="{html.escape(href, quote=True)}">'
                         f'{html.escape(disp)}</a>')
        if not links:
            return ''
        return ('<div class="recent">🕘 最近访问： '
                + ' <span class="sep">·</span> '.join(links) + '</div>')
    def _row_link(self, href, label, icon, title, open_label='👁 打开',
                  can_dl=True, dl_href=None, preview=False, delete=False,
                  dirname=None, name=None, row_cls='', dir_nonempty=False):
        title_esc = html.escape(title, quote=True)
        name_html = (f'<a class="name" href="{html.escape(href, quote=True)}" '
                     f'title="打开 {title_esc}">{html.escape(label)}</a>')
        btns = []
        if open_label:
            btns.append(f'<a class="btn btn-open" href="{html.escape(href, quote=True)}" '
                        f'title="打开 {title_esc}">{_ICON_OPEN}</a>')
        if preview:
            p = '/preview?' + urllib.parse.urlencode(
                {'dir': urllib.parse.unquote(dirname or '/'), 'name': urllib.parse.unquote(name or '')})
            btns.append(f'<a class="btn btn-prev" href="{html.escape(p, quote=True)}" title="渲染预览 {title_esc}">{_ICON_PREVIEW}</a>')
        if can_dl:
            if dl_href is None:
                dl_href = href + ('&' if '?' in href else '?') + 'dl=1'
            btns.append(f'<a class="btn btn-dl" href="{html.escape(dl_href, quote=True)}" title="下载 {title_esc}">{_ICON_DL}</a>')
        if delete:
            is_dir = row_cls == 'row-dir' or label.endswith('/')
            if is_dir and dir_nonempty:
                msg = (f"目录「{label}」中包含文件或子目录。"
                       "删除后其中的所有内容会被一并删除，且不可恢复。确定删除整个目录吗？")
            elif is_dir:
                msg = f"确定删除空目录「{label}」吗？此操作不可恢复。"
            else:
                msg = f"确定删除文件「{label}」吗？此操作不可恢复。"
            confirm_attr = html.escape(
                'return confirm(%s)' % json.dumps(msg, ensure_ascii=False),
                quote=True)
            btns.append(
                f'<button class="btn btn-info" type="button" title="更多信息 {title_esc}" '
                f'data-dir="{html.escape(urllib.parse.unquote(dirname or "/"), quote=True)}" '
                f'data-name="{html.escape(name or "", quote=True)}" onclick="showInfo(this)">{_ICON_INFO}</button>'
            )
            btns.append(
                f'<form class="act-form" action="/delete" method="post" '
                f'onsubmit="{confirm_attr}">'
                f'<input type="hidden" name="dir" value="{html.escape(urllib.parse.unquote(dirname or "/"), quote=True)}">'
                f'<input type="hidden" name="name" value="{html.escape(name or "", quote=True)}">'
                f'<button class="btn btn-del" type="submit" title="删除 {title_esc}">{_ICON_DEL}</button></form>'
            )
        row_attr = f' class="row {row_cls}"' if row_cls else ' class="row"'
        rowsmark = (f'<button class="rowsmark" type="button" title="显示操作按钮">⋮</button>' if btns else '')
        parts = [f'<div{row_attr}>',
                 f'<div class="line1"><span class="icon">{icon}</span>{name_html}{rowsmark}</div>']
        if btns:
            parts.append(f'<div class="line2"><div class="actions">{"".join(btns)}</div></div>')
        parts.append('</div>')
        return ''.join(parts)
    def _parse_multipart(self):
        """Parse a multipart/form-data request body into a dict of field -> {name, filename, content}."""
        ctype = self.headers.get('Content-Type', '')
        m = re.search(r'boundary=(?:"([^"]+)"|([^;]+))', ctype)
        if not m:
            return None
        boundary = (m.group(1) or m.group(2)).encode('utf-8')
        length = int(self.headers.get('Content-Length', 0) or 0)
        if length <= 0 or length > MAX_UPLOAD_BYTES:
            return None
        body = self.rfile.read(length)

        fields = {}
        for part in body.split(b'--' + boundary):
            part = part.strip(b'\r\n-')
            if not part or part == b'--':
                continue
            header_blk, sep, content = part.partition(b'\r\n\r\n')
            if not sep:
                continue
            headers = header_blk.decode('utf-8', 'replace')
            name_m = re.search(r'name="([^"]+)"', headers)
            fn_m = re.search(r'filename="([^"]*)"', headers)
            if not name_m:
                continue
            fields[name_m.group(1)] = {
                'filename': str(urllib.parse.unquote(fn_m.group(1))) if fn_m else '',
                'content': content,
            }
        return fields
    def _parse_urlencoded(self):
        length = int(self.headers.get('Content-Length', 0) or 0)
        if length <= 0 or length > MAX_UPLOAD_BYTES:
            return None
        body = self.rfile.read(length).decode('utf-8', 'replace')
        fields = {}
        for pair in body.split('&'):
            k, _, v = pair.partition('=')
            if not k:
                continue
            fields[urllib.parse.unquote_plus(k)] = urllib.parse.unquote_plus(v)
        return fields
    def _handle_delete(self):
        fields = self._parse_urlencoded()
        if not fields:
            self.send_error(400, 'Bad form request')
            return
        base = os.path.abspath(self.directory) if hasattr(self, 'directory') else os.getcwd()
        target = fields.get('dir', '/')
        if not target.startswith('/'):
            target = '/' + target
        target_dir = os.path.abspath(os.path.join(base, target.lstrip('/')))
        if not target_dir.startswith(base + os.sep) and target_dir != base:
            self.send_error(403, 'Forbidden path')
            return
        name = fields.get('name', '')
        if not name or name in ('.', '..') or '/' in name or '\\' in name:
            self.send_error(400, 'Bad filename')
            return
        full = os.path.join(target_dir, name)
        if not (os.path.isfile(full) or os.path.isdir(full)):
            self.send_error(404, 'Not found')
            return
        try:
            if os.path.islink(full):
                # 符号链接只删除链接本身，绝不跟随进入目标目录
                os.remove(full)
            elif os.path.isdir(full):
                shutil.rmtree(full)
            else:
                os.remove(full)
        except OSError:
            self.send_error(403, 'Delete failed')
            return
        self.send_response(303)
        self.send_header('Location', urllib.parse.quote(target or '/', safe='/'))
        self.end_headers()
    def _handle_upload(self):
        fields = self._parse_multipart()
        if not fields:
            self.send_error(400, 'Bad multipart request')
            return

        # 目标目录：来自表单隐藏字段 dir（当前浏览的目录）
        target = fields.get('dir', {}).get('content', b'/').decode('utf-8', 'replace')
        base = os.path.abspath(self.directory) if hasattr(self, 'directory') else os.getcwd()
        if target and not target.startswith('/'):
            target = '/' + target
        target_dir = os.path.abspath(os.path.join(base, target.lstrip('/')))
        if not target_dir.startswith(base + os.sep) and target_dir != base:
            self.send_error(403, 'Forbidden path')
            return

        saved = 0
        for key, field in fields.items():
            if key == 'dir' or not field['filename']:
                continue
            fname = os.path.basename(field['filename'])  # 防目录穿越
            if not fname:
                continue
            dest = os.path.join(target_dir, fname)
            with open(dest, 'wb') as f:
                f.write(field['content'])
            saved += 1

        # 303 回到当前目录列表
        self.send_response(303)
        self.send_header('Location', urllib.parse.quote(target or '/', safe='/'))
        self.end_headers()
    def _serve_info(self):
        base = os.path.abspath(self.directory) if hasattr(self, 'directory') else os.getcwd()
        qs = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        target = qs.get('dir', ['/'])[0] or '/'
        if not target.startswith('/'):
            target = '/' + target
        target_dir = os.path.abspath(os.path.join(base, target.lstrip('/')))
        if not (target_dir == base or target_dir.startswith(base + os.sep)):
            self._send_json({'ok': False, 'error': 'forbidden'})
            return
        name = qs.get('name', [''])[0]
        if not name or name in ('.', '..') or '/' in name or '\\' in name:
            self._send_json({'ok': False, 'error': 'bad name'})
            return
        full = os.path.join(target_dir, name)
        if not os.path.lexists(full):
            self._send_json({'ok': False, 'error': 'not found'})
            return
        try:
            st = os.lstat(full)
        except OSError:
            self._send_json({'ok': False, 'error': 'lstat failed'})
            return
        is_dir = os.path.isdir(full)
        mode = st.st_mode & 0o777
        tri = lambda v: ('r' if v & 4 else '-') + ('w' if v & 2 else '-') + ('x' if v & 1 else '-')
        perm_str = tri((mode >> 6) & 7) + tri((mode >> 3) & 7) + tri(mode & 7)
        fmt_time = lambda ts: datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
        ext = os.path.splitext(name)[1].lower()
        if is_dir:
            typ = '目录'
        else:
            typ = '文件' + (f'（{ext.upper()}）' if ext else '（无后缀）')
        obj = {
            'ok': True,
            'name': name,
            'dir': target or '/',
            'type': typ,
            'is_dir': is_dir,
            'size': st.st_size,
            'size_human': _fmt_size(st.st_size),
            'mtime': fmt_time(st.st_mtime),
            'ctime': fmt_time(st.st_ctime),
            'perm': '{:04o}'.format(mode),
            'perm_str': perm_str,
            'readable': os.access(full, os.R_OK),
            'writable': os.access(full, os.W_OK),
        }
        self._send_json(obj)

