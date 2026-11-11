import json
import os
import urllib.parse

from .i18n import render_page, resolve_lang


class ResponseMixin:
    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def _send_html(self, page, status=200):
        page = render_page(page, resolve_lang(self))
        body = page.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def _send_file_bytes(self, full, ctype, name):
        try:
            f = open(full, 'rb')
        except OSError:
            self.send_error(404, 'Read failed')
            return
        try:
            size = os.fstat(f.fileno()).st_size
            self.send_response(200)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(size))
            self.send_header('Cache-Control', 'no-store')
            ascii_name = (name.encode('ascii', 'replace').decode('ascii')
                          .replace('"', '') or 'file')
            self.send_header('Content-Disposition',
                             'inline; filename="%s"; filename*=utf-8\'\'%s'
                             % (ascii_name, urllib.parse.quote(name)))
            self.end_headers()
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                self.wfile.write(chunk)
        finally:
            f.close()

