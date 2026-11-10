import os
import struct
import tempfile
import unittest
import zipfile

from dls.office import _office_text, docx_blocks


def _write_docx(path):
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('word/document.xml',
                   '<w:document xmlns:w="http://schemas.openxmlformats.org/'
                   'wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>你好'
                   '</w:t></w:r></w:p><w:p><w:r><w:t>第二段</w:t></w:r></w:p>'
                   '</w:body></w:document>')


def _write_xlsx(path):
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('xl/sharedStrings.xml',
                   '<sst xmlns="http://schemas.openxmlformats.org/'
                   'spreadsheetml/2006/main"><si><t>姓名</t></si><si><t>张三</t>'
                   '</si></sst>')
        z.writestr('xl/worksheets/sheet1.xml',
                   '<worksheet xmlns="http://schemas.openxmlformats.org/'
                   'spreadsheetml/2006/main"><sheetData><row><c t="s"><v>0</v>'
                   '</c><c t="s"><v>1</v></c></row></sheetData></worksheet>')


def _write_pptx(path):
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('ppt/slides/slide1.xml',
                   '<p:sld xmlns:p="p" xmlns:a="a"><a:p><a:r><a:t>第一页'
                   '</a:t></a:r></a:p></p:sld>')


def _dirent(name, etype, start, size):
    n = name.encode('utf-16-le') + b'\x00\x00'
    e = bytearray(128)
    e[:len(n)] = n
    struct.pack_into('<H', e, 0x40, len(n))
    e[0x42] = etype
    e[0x43] = 1
    struct.pack_into('<III', e, 0x44, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF)
    struct.pack_into('<I', e, 0x74, start)
    struct.pack_into('<Q', e, 0x78, size)
    return bytes(e)


def _write_doc(path):
    text = '测试文档 Hello\r\n第二行'
    tbytes = text.encode('utf-16-le')
    wd_size = tb_size = 4096
    clx = (b'\x02' + struct.pack('<I', 16) + struct.pack('<II', 0, len(text))
           + struct.pack('<HIH', 0, 0x0400, 0))
    wd = bytearray(wd_size)
    struct.pack_into('<H', wd, 0x0A, 0x0200)
    struct.pack_into('<I', wd, 0x01A2, 0)
    struct.pack_into('<I', wd, 0x01A6, len(clx))
    wd[0x0400:0x0400 + len(tbytes)] = tbytes
    tb = bytearray(tb_size)
    tb[:len(clx)] = clx

    fat = [0xFFFFFFFF] * 128
    fat[0] = 0xFFFFFFFD
    fat[1] = 0xFFFFFFFE
    for i in range(8):
        fat[2 + i] = 3 + i if i < 7 else 0xFFFFFFFE
    for i in range(8):
        fat[10 + i] = 11 + i if i < 7 else 0xFFFFFFFE

    hdr = bytearray(512)
    hdr[:8] = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'
    struct.pack_into('<HHH', hdr, 0x18, 0x003E, 0x0003, 0xFFFE)
    struct.pack_into('<HH', hdr, 0x1E, 9, 6)
    struct.pack_into('<I', hdr, 0x2C, 1)
    struct.pack_into('<I', hdr, 0x30, 1)
    struct.pack_into('<I', hdr, 0x38, 4096)
    struct.pack_into('<I', hdr, 0x3C, 0xFFFFFFFE)
    struct.pack_into('<I', hdr, 0x44, 0xFFFFFFFE)
    for i in range(109):
        struct.pack_into('<I', hdr, 0x4C + i * 4,
                         0 if i == 0 else 0xFFFFFFFF)

    data = (bytes(hdr) + struct.pack('<128I', *fat)
            + _dirent('Root Entry', 5, 0xFFFFFFFE, 0)
            + _dirent('WordDocument', 2, 2, wd_size)
            + _dirent('1Table', 2, 10, tb_size)
            + bytes(512 - 3 * 128) + bytes(wd) + bytes(tb))
    with open(path, 'wb') as f:
        f.write(data)


class OfficeExtractTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_docx(self):
        p = os.path.join(self.dir, 'a.docx')
        _write_docx(p)
        text = _office_text(p, 'docx')
        self.assertIn('你好', text)
        self.assertIn('第二段', text)

    def test_docx_images_order(self):
        p = os.path.join(self.dir, 'pic.docx')
        with zipfile.ZipFile(p, 'w') as z:
            z.writestr('word/document.xml',
                       '<w:document xmlns:w="http://schemas.openxmlformats.org/'
                       'wordprocessingml/2006/main" '
                       'xmlns:r="http://schemas.openxmlformats.org/officeDocument/'
                       '2006/relationships" '
                       'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/'
                       'main"><w:body><w:p><w:r><w:t>前</w:t></w:r><w:r>'
                       '<w:drawing><a:blip r:embed="rId1"/></w:drawing></w:r>'
                       '<w:r><w:t>后</w:t></w:r></w:p></w:body></w:document>')
            z.writestr('word/_rels/document.xml.rels',
                       '<Relationships xmlns="http://schemas.openxmlformats.org/'
                       'package/2006/relationships"><Relationship Id="rId1" '
                       'Type="http://schemas.openxmlformats.org/officeDocument/'
                       '2006/relationships/image" Target="media/image1.png"/>'
                       '</Relationships>')
            z.writestr('word/media/image1.png', b'\x89PNG\r\n\x1a\n')
        blocks = docx_blocks(p)
        self.assertEqual(blocks, [('text', '前'),
                                  ('image', 'word/media/image1.png'),
                                  ('text', '后')])

    def test_xlsx(self):
        p = os.path.join(self.dir, 'a.xlsx')
        _write_xlsx(p)
        text = _office_text(p, 'xlsx')
        self.assertIn('姓名', text)
        self.assertIn('张三', text)

    def test_pptx(self):
        p = os.path.join(self.dir, 'a.pptx')
        _write_pptx(p)
        self.assertIn('第一页', _office_text(p, 'pptx'))

    def test_rtf(self):
        p = os.path.join(self.dir, 'a.rtf')
        with open(p, 'wb') as f:
            f.write(rb'{\rtf1\ansi \u20320?\u22909? Hello\par second}')
        text = _office_text(p, 'rtf')
        self.assertIn('你好', text)
        self.assertIn('Hello', text)

    def test_doc(self):
        p = os.path.join(self.dir, 'a.doc')
        _write_doc(p)
        text = _office_text(p, 'doc')
        self.assertIn('测试文档', text)
        self.assertIn('第二行', text)

    def test_doc_rejects_binary(self):
        p = os.path.join(self.dir, 'bad.doc')
        with open(p, 'wb') as f:
            f.write(bytes(range(256)) * 4)
        with self.assertRaises(ValueError):
            _office_text(p, 'doc')


if __name__ == '__main__':
    unittest.main()
