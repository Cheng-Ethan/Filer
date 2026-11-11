import os
import urllib.parse
from http.server import SimpleHTTPRequestHandler

from .article import ArticleMixin
from .auth import AuthMixin
from .editor import EditorMixin
from .files import FilesMixin
from .i18n import resolve_lang, set_current_lang
from .plugins import PluginsMixin
from .preview import PreviewMixin
from .providers import REGISTRY
from .response import ResponseMixin
from .shell import ShellMixin
from .tts import TtsMixin


class ForceDownloadHandler(AuthMixin, FilesMixin, PreviewMixin, EditorMixin,
                           TtsMixin, ArticleMixin, ShellMixin, PluginsMixin,
                           ResponseMixin, SimpleHTTPRequestHandler):
    def do_POST(self):
        if not self.require_auth():
            return
        set_current_lang(resolve_lang(self))
        path = urllib.parse.urlsplit(self.path).path
        if path == '/delete':
            self._handle_delete()
        elif path == '/edit':
            self._handle_edit()
        elif path == '/upload':
            self._handle_upload()
        elif path == '/cmd':
            self._handle_cmd()
        elif path == '/cmd/cancel':
            self._handle_cmd_cancel()
        else:
            route = REGISTRY.match_route('POST', path)
            if route:
                self._serve_plugin_route(route)
            else:
                self.send_error(404, 'Not found')
    def do_GET(self):
        if not self.require_auth():
            return
        set_current_lang(resolve_lang(self))
        parts = urllib.parse.urlsplit(self.path)
        path = parts.path
        if path == '/read':
            self._serve_read()
            return
        if path == '/article/img':
            self._serve_article_img()
            return
        if path == '/article/tts':
            self._serve_article_tts()
            return
        if path.startswith('/pdfjs/'):
            self._serve_pdfjs()
            return
        if path == '/officepage':
            self._serve_officepage()
            return
        if path == '/officepdf':
            self._serve_office_pdf()
            return
        if path == '/docmedia':
            self._serve_docmedia()
            return
        if path == '/edit':
            self._serve_edit()
            return
        match = REGISTRY.match_static(path)
        if match:
            self._serve_plugin_static(match)
            return
        route = REGISTRY.match_route('GET', path)
        if route:
            self._serve_plugin_route(route)
            return
        if path == '/tts/voices':
            self._serve_tts_voices()
            return
        if path == '/tts':
            self._serve_tts()
            return
        if path == '/preview':
            self._serve_preview()
            return
        if path == '/info':
            self._serve_info()
            return
        qs = urllib.parse.parse_qs(parts.query)
        fpath = self.translate_path(path)
        if 'raw' in qs:
            super().do_GET()
            return
        if os.path.isfile(fpath):
            # .html 等自成页面的文件：全窗口打开，不再叠加操作工具栏
            if os.path.splitext(path)[1].lower() in ('.html', '.htm'):
                super().do_GET()
                return
            # 强制下载（FORCE 类型或 ?dl=1）：直接回传文件字节，绝不含 HTML 包装
            if self.forced_download():
                if not os.access(fpath, os.R_OK):
                    msg = '文件无读取权限（权限不足）。'.encode('utf-8')
                    self.send_response(403)
                    self.send_header('Content-Type', 'text/plain; charset=utf-8')
                    self.send_header('Content-Length', str(len(msg)))
                    self.end_headers()
                    self.wfile.write(msg)
                    return
                super().do_GET()
                return
            self._serve_browse(fpath, path)
            return
        if os.path.isdir(fpath):
            # 以"浏览文件"为准：目录永远显示文件列表，绝不自动把 index.html 当网页打开
            if not path.endswith('/'):
                new_parts = (parts.scheme, parts.netloc, parts.path + '/',
                             parts.query, parts.fragment)
                self.send_response(301)
                self.send_header('Location', urllib.parse.urlunsplit(new_parts))
                self.send_header('Content-Length', '0')
                self.end_headers()
                return
            self.list_directory(fpath)
            return
        super().do_GET()
    def do_HEAD(self):
        if not self.require_auth():
            return
        super().do_HEAD()

