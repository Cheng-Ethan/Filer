import unittest
from unittest import mock

from dls import tts


class TtsHelperTest(unittest.TestCase):
    def test_rate_string(self):
        self.assertEqual(tts._rate_str(1.0), '+0%')
        self.assertEqual(tts._rate_str(1.5), '+50%')
        self.assertEqual(tts._rate_str(0.75), '-25%')

    def test_chunks_split(self):
        text = '第一句。第二句！第三句？'
        chunks = tts._chunks(text, limit=4)
        self.assertTrue(all(len(c) <= 4 for c in chunks))
        self.assertEqual(''.join(chunks), text)

    def test_dictionary_longest_match(self):
        with mock.patch.object(tts, '_load_dict',
                               return_value={'音乐': '音月', '银行': '银航'}):
            self.assertEqual(tts._apply_dict('音乐银行'), '音月银航')

    def test_markdown_strip(self):
        text = tts._markdown_to_text('# 标题\n\n**粗体** [链接](http://x) `code`')
        self.assertNotIn('#', text)
        self.assertNotIn('http', text)
        self.assertIn('标题', text)
        self.assertIn('链接', text)


if __name__ == '__main__':
    unittest.main()
