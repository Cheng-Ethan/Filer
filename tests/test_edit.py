import base64
import functools
import http.client
import os
import tempfile
import threading
import unittest
import urllib.parse
from http.server import ThreadingHTTPServer

from dls.handler import ForceDownloadHandler

AUTH = 'Basic ' + base64.b64encode(b'admin:test').decode('ascii')


class EditHttpTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = cls.tmp.name
        with open(os.path.join(cls.dir, 'plain.txt'), 'wb') as f:
            f.write(b'alpha\nbeta\n')
        with open(os.path.join(cls.dir, 'gbk.txt'), 'wb') as f:
            f.write('你好，世界\r\n'.encode('gbk'))
        with open(os.path.join(cls.dir, 'notes.md'), 'wb') as f:
            f.write(b'# notes\n')
        with open(os.path.join(cls.dir, 'bom.txt'), 'wb') as f:
            f.write(b'\xef\xbb\xbfhello\n')
        with open(os.path.join(cls.dir, 'binary.bin'), 'wb') as f:
            f.write(bytes(range(256)))
        handler = functools.partial(ForceDownloadHandler, directory=cls.dir,
                                    user='admin', password='test')
        cls.httpd = ThreadingHTTPServer(('127.0.0.1', 0), handler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever,
                                      daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.tmp.cleanup()

    def request(self, path, method='GET', body=None, content_type=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        headers = {'Authorization': AUTH, 'Accept-Language': 'en'}
        if content_type:
            headers['Content-Type'] = content_type
        conn.request(method, path, body=body, headers=headers)
        resp = conn.getresponse()
        data = resp.read()
        info = dict(resp.getheaders())
        conn.close()
        return resp.status, info, data

    def stat_fields(self, name):
        st = os.stat(os.path.join(self.dir, name))
        return str(st.st_mtime_ns), str(st.st_size)

    def post_edit(self, name, text, enc, mtime_ns, size):
        body = urllib.parse.urlencode({
            'dir': '/', 'name': name, 'text': text, 'enc': enc,
            'mtime_ns': mtime_ns, 'size': size,
        })
        return self.request('/edit', 'POST', body,
                            'application/x-www-form-urlencoded')

    def test_preview_has_edit_link(self):
        status, _, data = self.request('/preview?dir=/&name=plain.txt')
        self.assertEqual(status, 200)
        page = data.decode('utf-8')
        self.assertIn('/edit?', page)
        self.assertIn('btn-edit', page)
        self.assertIn('<span>Edit</span>', page)

    def test_open_markdown_redirects_to_preview(self):
        status, info, _ = self.request('/notes.md')
        self.assertEqual(status, 302)
        self.assertTrue(info.get('Location', '').startswith('/preview?'))

    def test_list_has_edit_link(self):
        status, info, data = self.request('/')
        self.assertEqual(status, 200)
        self.assertEqual(info.get('Cache-Control'), 'no-store')
        page = data.decode('utf-8')
        self.assertIn('/edit?', page)
        self.assertIn('plain.txt', page)

    def test_get_edit_page(self):
        status, _, data = self.request('/edit?dir=/&name=plain.txt')
        self.assertEqual(status, 200)
        page = data.decode('utf-8')
        self.assertIn('<textarea', page)
        self.assertIn('name="text"', page)

    def test_post_edit_utf8(self):
        mtime_ns, size = self.stat_fields('plain.txt')
        status, _, _ = self.post_edit('plain.txt', 'one\ntwo\n', 'utf-8',
                                      mtime_ns, size)
        self.assertEqual(status, 303)
        with open(os.path.join(self.dir, 'plain.txt'), 'rb') as f:
            self.assertEqual(f.read(), b'one\ntwo\n')

    def test_post_edit_preserves_gbk_and_crlf(self):
        mtime_ns, size = self.stat_fields('gbk.txt')
        status, _, _ = self.post_edit('gbk.txt', '再见\n', 'gb18030',
                                      mtime_ns, size)
        self.assertEqual(status, 303)
        with open(os.path.join(self.dir, 'gbk.txt'), 'rb') as f:
            self.assertEqual(f.read(), '再见\r\n'.encode('gbk'))

    def test_post_edit_preserves_utf8_bom(self):
        mtime_ns, size = self.stat_fields('bom.txt')
        status, _, _ = self.post_edit('bom.txt', '你好\n', 'utf-8-sig',
                                      mtime_ns, size)
        self.assertEqual(status, 303)
        with open(os.path.join(self.dir, 'bom.txt'), 'rb') as f:
            self.assertEqual(f.read(), b'\xef\xbb\xbf' + '你好\n'.encode('utf-8'))

    def test_conflict_rejected(self):
        path = os.path.join(self.dir, 'plain.txt')
        mtime_ns, size = self.stat_fields('plain.txt')
        with open(path, 'wb') as f:
            f.write(b'changed elsewhere\n')
        status, _, _ = self.post_edit('plain.txt', 'mine\n', 'utf-8',
                                      mtime_ns, size)
        self.assertEqual(status, 409)
        with open(path, 'rb') as f:
            self.assertEqual(f.read(), b'changed elsewhere\n')

    def test_traversal_rejected(self):
        status, _, _ = self.request('/edit?dir=/&name=../x')
        self.assertEqual(status, 400)

    def test_binary_not_editable(self):
        status, _, data = self.request('/preview?dir=/&name=binary.bin')
        self.assertEqual(status, 200)
        self.assertNotIn(b'/edit?', data)

    def test_markdown_has_edit_link(self):
        status, _, data = self.request('/preview?dir=/&name=notes.md')
        self.assertEqual(status, 200)
        self.assertIn(b'/edit?', data)
        self.assertIn(b'const MD_BASE = "/";', data)


if __name__ == '__main__':
    unittest.main()
