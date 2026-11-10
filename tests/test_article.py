import unittest

from dls.article import _ContentParser, _extract_globol_detail


class ArticleParseTest(unittest.TestCase):
    def test_extract_globol_detail(self):
        page = (
            '<html><script>var GLOBOL_INFO\n'
            '        try {\n'
            '            GLOBOL_INFO = {\n'
            '                detailContent: {"seq":"1","title":"\\u6807\\u9898",'
            '"content":"<p>\\u6b63\\u6587{\\u6d4b\\u8bd5}</p>","source":"\\u6765\\u6e90"},'
            '                aboutRead: [],\n'
            '                ctime: \'2026-11-09 16:14:38\'\n'
            '            };\n'
            '        } catch (e) { GLOBOL_INFO = null }</script></html>')
        detail = _extract_globol_detail(page)
        self.assertIsInstance(detail, dict)
        self.assertEqual(detail['title'], '标题')
        self.assertEqual(detail['source'], '来源')
        parser = _ContentParser('https://example.com', fragment=True)
        parser.feed(detail['content'])
        self.assertEqual(''.join(parser.texts).replace('\u3000', ' ').strip(),
                         '正文{测试}')

    def test_extract_globol_detail_missing(self):
        self.assertIsNone(_extract_globol_detail('<html><body>无正文</body></html>'))


if __name__ == '__main__':
    unittest.main()
