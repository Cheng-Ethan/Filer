import unittest

from dls.textenc import _decode_bytes, _detect_encoding


class TextEncodingTest(unittest.TestCase):
    def test_utf8(self):
        raw = '你好，Windows 记事本'.encode('utf-8')
        self.assertEqual(_detect_encoding(raw), 'utf-8')
        self.assertEqual(_decode_bytes(raw, 'utf-8'), '你好，Windows 记事本')

    def test_gbk(self):
        raw = '你好，Windows 记事本'.encode('gbk')
        enc = _detect_encoding(raw)
        self.assertEqual(enc, 'gb18030')
        self.assertEqual(_decode_bytes(raw, enc), '你好，Windows 记事本')

    def test_utf16_bom(self):
        raw = b'\xff\xfe' + '你好'.encode('utf-16-le')
        self.assertEqual(_detect_encoding(raw), 'utf-16-le')
        self.assertEqual(_decode_bytes(raw, 'utf-16-le'), '你好')

    def test_ascii(self):
        self.assertEqual(_detect_encoding(b'hello world'), 'utf-8')

    def test_binary(self):
        self.assertIsNone(_detect_encoding(bytes(range(256))))


if __name__ == '__main__':
    unittest.main()
