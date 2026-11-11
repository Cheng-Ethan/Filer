import base64
import contextlib
import functools
import html
import http.client
import io
import json
import os
import tempfile
import re
import sys
import threading
import time
import unittest
import urllib.parse
import zipfile
from http.server import ThreadingHTTPServer
from unittest import mock

import filer
from dls.handler import ForceDownloadHandler

AUTH = 'Basic ' + base64.b64encode(b'admin:test').decode('ascii')
GBK_TEXT = '你好，Windows 记事本'
PNG_1X1 = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9Zl1sAAAAASUVORK5CYII=')


def write_pic_docx(path):
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('[Content_Types].xml', '<Types/>')
        z.writestr('word/document.xml',
                   '<w:document xmlns:w="http://schemas.openxmlformats.org/'
                   'wordprocessingml/2006/main" '
                   'xmlns:r="http://schemas.openxmlformats.org/officeDocument/'
                   '2006/relationships" '
                   'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/'
                   'main"><w:body><w:p><w:r><w:t>图片前</w:t></w:r><w:r>'
                   '<w:drawing><a:blip r:embed="rId1"/></w:drawing></w:r>'
                   '<w:r><w:t>图片后</w:t></w:r></w:p></w:body></w:document>')
        z.writestr('word/_rels/document.xml.rels',
                   '<Relationships xmlns="http://schemas.openxmlformats.org/'
                   'package/2006/relationships"><Relationship Id="rId1" '
                   'Type="http://schemas.openxmlformats.org/officeDocument/'
                   '2006/relationships/image" Target="media/image1.png"/>'
                   '</Relationships>')
        z.writestr('word/media/image1.png', PNG_1X1)


def header(info, name):
    for key, value in info.items():
        if key.lower() == name.lower():
            return value
    return ''


class HttpTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = cls.tmp.name
        with open(os.path.join(cls.dir, 'gbk.txt'), 'wb') as f:
            f.write(GBK_TEXT.encode('gbk'))
        with open(os.path.join(cls.dir, 'plain.txt'), 'wb') as f:
            f.write(b'plain ascii\n')
        write_pic_docx(os.path.join(cls.dir, 'pic.docx'))
        ForceDownloadHandler.auth_user = 'admin'
        ForceDownloadHandler.auth_pass = 'test'
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

    def request(self, path, method='GET', body=None, auth=True):
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        headers = {'Authorization': AUTH, 'Accept-Language': 'zh-CN'} if auth else {'Accept-Language': 'zh-CN'}
        conn.request(method, path, body=body, headers=headers)
        resp = conn.getresponse()
        data = resp.read()
        info = dict(resp.getheaders())
        conn.close()
        return resp.status, info, data

    def test_root(self):
        status, _, data = self.request('/')
        self.assertEqual(status, 200)
        self.assertIn(b'gbk.txt', data)

    def test_unauthorized(self):
        status, info, _ = self.request('/', auth=False)
        self.assertEqual(status, 401)
        self.assertIn('Basic', header(info, 'WWW-Authenticate'))

    def _run_main(self, argv):
        stderr = io.StringIO()
        with mock.patch.dict(os.environ, {}, clear=True), \
                mock.patch.object(sys, 'argv', argv), \
                mock.patch('filer.ThreadingHTTPServer') as server, \
                contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as cm:
                filer.main()
        self.assertEqual(cm.exception.code, 2)
        server.assert_not_called()
        return stderr.getvalue()

    def test_version(self):
        stdout = io.StringIO()
        with mock.patch.object(sys, 'argv', ['filer.py', '--version']), \
                contextlib.redirect_stdout(stdout):
            with self.assertRaises(SystemExit) as cm:
                filer.main()
        self.assertEqual(cm.exception.code, 0)
        self.assertIn('0.1.0', stdout.getvalue())

    def test_missing_user_refuses_start(self):
        err = self._run_main(['filer.py'])
        self.assertIn('DL_AUTH', err)

    def test_empty_password_refuses_start(self):
        err = self._run_main(['filer.py', '--user', 'admin:'])
        self.assertIn("--user must be 'username:password', both non-empty", err)

    def test_raw_gbk_charset(self):
        status, info, data = self.request('/gbk.txt?raw=1')
        self.assertEqual(status, 200)
        self.assertIn('gb18030', header(info, 'Content-Type'))
        self.assertEqual(data, GBK_TEXT.encode('gbk'))

    def test_preview_gbk(self):
        status, _, data = self.request('/preview?dir=/&name=gbk.txt')
        self.assertEqual(status, 200)
        self.assertIn(GBK_TEXT, data.decode('utf-8'))

    def test_preview_enc_override(self):
        status, _, data = self.request(
            '/preview?dir=/&name=gbk.txt&enc=utf-8')
        self.assertEqual(status, 200)
        self.assertIn(b'ttsBtn', data)

    def test_info(self):
        status, _, data = self.request('/info?dir=/&name=gbk.txt')
        self.assertEqual(status, 200)
        obj = json.loads(data)
        self.assertTrue(obj['ok'])
        self.assertEqual(obj['name'], 'gbk.txt')
        self.assertEqual(obj['size'], len(GBK_TEXT.encode('gbk')))

    def test_download(self):
        status, info, data = self.request('/gbk.txt?dl=1')
        self.assertEqual(status, 200)
        self.assertIn('attachment', header(info, 'Content-Disposition'))
        self.assertEqual(data, GBK_TEXT.encode('gbk'))

    def test_unsupported_preview(self):
        with open(os.path.join(self.dir, 'x.zip'), 'wb') as f:
            f.write(b'PK\x03\x04' + bytes(range(256)))
        status, _, data = self.request('/preview?dir=/&name=x.zip')
        self.assertEqual(status, 200)
        self.assertIn('暂不支持网页预览'.encode('utf-8'), data)

    def test_docx_images(self):
        status, _, data = self.request('/preview?dir=/&name=pic.docx')
        self.assertEqual(status, 200)
        page = data.decode('utf-8')
        self.assertIn('图片前', page)
        self.assertIn('图片后', page)
        m = re.search(r'/docmedia\?[^"\s]+', page)
        self.assertIsNotNone(m)
        url = html.unescape(m.group(0))
        status, info, img = self.request(url)
        self.assertEqual(status, 200)
        self.assertEqual(header(info, 'Content-Type'), 'image/png')
        self.assertTrue(img.startswith(b'\x89PNG'))

    def test_cmd(self):
        body = json.dumps({'cmd': 'echo hi', 'dir': '/', 'stream': False})
        status, _, data = self.request('/cmd', 'POST', body)
        self.assertEqual(status, 200)
        obj = json.loads(data)
        self.assertEqual(obj['code'], 0)
        self.assertIn('hi', obj['out'])

    def test_cmd_cancel(self):
        headers = {'Authorization': AUTH, 'Content-Type': 'application/json', 'Accept-Language': 'zh-CN'}
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
        conn.request('POST', '/cmd', body=json.dumps(
            {'cmd': 'echo start; sleep 100; echo never', 'dir': '/',
             'stream': True, 'id': 'cancel-test'}), headers=headers)
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)
        time.sleep(0.3)
        conn2 = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
        conn2.request('POST', '/cmd/cancel', body=json.dumps({'id': 'cancel-test'}),
                      headers=headers)
        r2 = conn2.getresponse()
        result = json.loads(r2.read())
        conn2.close()
        self.assertTrue(result['cancelled'])
        out = resp.read().decode('utf-8', 'replace')
        conn.close()
        self.assertIn('已取消', out)
        self.assertNotIn('never', out)

    def test_delete_nonempty_dir(self):
        root = os.path.join(self.dir, 'del-tree')
        os.makedirs(os.path.join(root, 'sub'))
        with open(os.path.join(root, 'sub', 'x.txt'), 'w') as f:
            f.write('x')
        with open(os.path.join(root, 'top.txt'), 'w') as f:
            f.write('y')

        status, _, page = self.request('/')
        self.assertEqual(status, 200)
        self.assertIn('包含文件或子目录', page.decode('utf-8'))

        body = urllib.parse.urlencode({'dir': '/', 'name': 'del-tree'})
        status, _, _ = self.request('/delete', 'POST', body)
        self.assertEqual(status, 303)
        self.assertFalse(os.path.exists(root))


if __name__ == '__main__':
    unittest.main()
