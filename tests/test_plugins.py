import base64
import functools
import http.client
import io
import json
import os
import tempfile
import threading
import unittest
import urllib.parse
from http.server import ThreadingHTTPServer

from dls.handler import ForceDownloadHandler
from dls.plugins import PluginResponse, load_plugins
from dls.providers import PreviewProvider, ProviderRegistry

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLES = os.path.join(ROOT, 'examples', 'plugins')
AUTH = 'Basic ' + base64.b64encode(b'admin:test').decode('ascii')


class PluginLoaderTest(unittest.TestCase):
    def test_example_plugin_loads(self):
        registry = ProviderRegistry()
        stream = io.StringIO()
        loaded = load_plugins([EXAMPLES], registry=registry, stream=stream)
        self.assertIn('todo-editor', loaded)
        provider = registry.find_editor('list.todo', '/tmp/list.todo')
        self.assertIsNotNone(provider)
        self.assertEqual(provider.id, 'todo-editor:todo')

    def test_bad_plugin_isolation(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugin = os.path.join(tmp, 'broken')
            os.makedirs(plugin)
            with open(os.path.join(plugin, 'plugin.json'), 'w') as f:
                json.dump({'id': 'broken', 'api_version': 999}, f)
            with open(os.path.join(plugin, 'plugin.py'), 'w') as f:
                f.write('def register(ctx):\n    pass\n')
            stream = io.StringIO()
            loaded = load_plugins([tmp], registry=ProviderRegistry(), stream=stream)
            self.assertEqual(loaded, [])
            self.assertIn('skipped', stream.getvalue())

    def test_route_and_static_registration(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugin = os.path.join(tmp, 'demo')
            os.makedirs(os.path.join(plugin, 'static'))
            with open(os.path.join(plugin, 'static', 'a.txt'), 'w') as f:
                f.write('asset')
            with open(os.path.join(plugin, 'plugin.json'), 'w') as f:
                json.dump({'id': 'demo', 'api_version': 1, 'entry': 'plugin.py'}, f)
            with open(os.path.join(plugin, 'plugin.py'), 'w') as f:
                f.write(
                    'import os\n'
                    'from dls.plugins import PluginResponse\n'
                    'from dls.providers import PreviewProvider\n'
                    'class DemoPreview(PreviewProvider):\n'
                    '    id = "preview"\n'
                    '    def matches(self, name, path):\n'
                    '        return name.endswith(".demo")\n'
                    '    def render(self, ctx):\n'
                    '        return "<html>demo</html>"\n'
                    'def register(ctx):\n'
                    '    ctx.register_preview(DemoPreview())\n'
                    '    ctx.register_route("GET", "/plugins/demo/hello",\n'
                    '                        lambda req: PluginResponse(body=b"ok"))\n'
                    '    ctx.register_static("/plugins/demo/static",\n'
                    '                        os.path.join(ctx.dir, "static"))\n')
            registry = ProviderRegistry()
            loaded = load_plugins([tmp], registry=registry, stream=io.StringIO())
            self.assertIn('demo', loaded)
            self.assertIsNotNone(registry.find_preview('x.demo', '/tmp/x.demo'))
            self.assertIsNotNone(registry.match_route('GET', '/plugins/demo/hello'))
            self.assertIsNotNone(registry.match_static('/plugins/demo/static/a.txt'))


class PluginHttpTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plug_tmp = tempfile.TemporaryDirectory()
        demo = os.path.join(cls.plug_tmp.name, 'demo-preview')
        os.makedirs(os.path.join(demo, 'static'))
        with open(os.path.join(demo, 'static', 'hello.txt'), 'w') as f:
            f.write('static-ok')
        with open(os.path.join(demo, 'plugin.json'), 'w') as f:
            json.dump({'id': 'demo-preview', 'api_version': 1,
                       'entry': 'plugin.py'}, f)
        with open(os.path.join(demo, 'plugin.py'), 'w') as f:
            f.write(
                'import os\n'
                'from dls.plugins import PluginResponse\n'
                'from dls.providers import PreviewProvider\n'
                'class Demo(PreviewProvider):\n'
                '    id = "preview"\n'
                '    def matches(self, name, path):\n'
                '        return name.endswith(".demo")\n'
                '    def render(self, ctx):\n'
                '        return "<html><body>demo-preview</body></html>"\n'
                'def register(ctx):\n'
                '    ctx.register_preview(Demo())\n'
                '    ctx.register_route("GET", "/plugins/demo-preview/hello",\n'
                '                        lambda req: PluginResponse(body=b"route-ok"))\n'
                '    ctx.register_static("/plugins/demo-preview/static",\n'
                '                        os.path.join(ctx.dir, "static"))\n')
        load_plugins([EXAMPLES, cls.plug_tmp.name], stream=io.StringIO())
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = cls.tmp.name
        with open(os.path.join(cls.dir, 'list.todo'), 'w') as f:
            f.write('[ ] one\n[x] two\n')
        with open(os.path.join(cls.dir, 'sample.demo'), 'w') as f:
            f.write('demo')

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
        cls.plug_tmp.cleanup()

    def request(self, path, method='GET', body=None, content_type=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        headers = {'Authorization': AUTH, 'Accept-Language': 'en'}
        if content_type:
            headers['Content-Type'] = content_type
        conn.request(method, path, body=body, headers=headers)
        resp = conn.getresponse()
        data = resp.read()
        conn.close()
        return resp.status, data

    def test_plugin_preview_provider(self):
        status, data = self.request('/preview?dir=/&name=sample.demo')
        self.assertEqual(status, 200)
        self.assertIn(b'demo-preview', data)

    def test_plugin_route_and_static(self):
        status, data = self.request('/plugins/demo-preview/hello')
        self.assertEqual(status, 200)
        self.assertEqual(data, b'route-ok')
        status, data = self.request('/plugins/demo-preview/static/hello.txt')
        self.assertEqual(status, 200)
        self.assertEqual(data, b'static-ok')

    def test_plugin_editor_page(self):
        status, data = self.request('/edit?dir=/&name=list.todo')
        self.assertEqual(status, 200)
        page = data.decode('utf-8')
        self.assertIn('name="text0"', page)
        self.assertIn('one', page)

    def test_plugin_editor_save(self):
        path = os.path.join(self.dir, 'list.todo')
        st = os.stat(path)
        body = urllib.parse.urlencode({
            'dir': '/', 'name': 'list.todo', 'count': '2',
            'text0': 'one', 'done0': 'on', 'text1': 'two',
            'mtime_ns': str(st.st_mtime_ns), 'size': str(st.st_size),
        })
        status, _ = self.request('/edit', 'POST', body,
                                 'application/x-www-form-urlencoded')
        self.assertEqual(status, 303)
        with open(path, encoding='utf-8') as f:
            self.assertEqual(f.read(), '[x] one\n[ ] two\n')


if __name__ == '__main__':
    unittest.main()
