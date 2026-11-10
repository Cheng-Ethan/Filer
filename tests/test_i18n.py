import json
import os
import re
import unittest

from dls import i18n

_LOCALES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'dls', 'locales')
_PLACEHOLDER = re.compile(r'\{(\w+)\}')


def _load(code):
    with open(os.path.join(_LOCALES, code + '.json'), encoding='utf-8') as f:
        return json.load(f)


class I18nFilesTest(unittest.TestCase):
    def test_en_meta(self):
        data = _load('en')
        self.assertEqual(data['_meta']['name'], 'English')
        self.assertEqual(data['_meta']['code'], 'en')
        self.assertEqual(data['_meta']['dir'], 'ltr')

    def test_key_sets_match(self):
        en = i18n.flatten(_load('en'))
        zh = i18n.flatten(_load('zh-CN'))
        self.assertEqual(set(en), set(zh))

    def test_placeholders_match(self):
        en = i18n.flatten(_load('en'))
        zh = i18n.flatten(_load('zh-CN'))
        for key in en:
            self.assertEqual(set(_PLACEHOLDER.findall(en[key])),
                             set(_PLACEHOLDER.findall(zh[key])), key)

    def test_values_clean(self):
        for code in ('en', 'zh-CN'):
            for key, value in i18n.flatten(_load(code)).items():
                self.assertTrue(value, key)
                self.assertEqual(value, value.strip(), key)

    def test_filename_matches_code(self):
        for code in ('en', 'zh-CN'):
            self.assertTrue(os.path.isfile(os.path.join(_LOCALES, code + '.json')))
            self.assertEqual(_load(code)['_meta']['code'], code)

    def test_zh_differs_from_en(self):
        whitelist = {'app.title'}
        en = i18n.flatten(_load('en'))
        zh = i18n.flatten(_load('zh-CN'))
        for key in en:
            if key in whitelist:
                continue
            self.assertNotEqual(en[key], zh[key], key)


class I18nBehaviourTest(unittest.TestCase):
    def test_negotiate(self):
        self.assertEqual(
            i18n.negotiate_lang('zh-CN,zh;q=0.9', i18n.available_locales()),
            'zh-CN')
        self.assertEqual(
            i18n.negotiate_lang('ja,en;q=0.5', i18n.available_locales()),
            'en')
        self.assertEqual(i18n.negotiate_lang('', i18n.available_locales()), 'en')
        self.assertEqual(
            i18n.negotiate_lang('zh-TW', i18n.available_locales()), 'zh-CN')

    def test_translator_fallback(self):
        self.assertEqual(i18n.get_translator('zh-CN')('app.title'),
                         'filer')
        self.assertEqual(i18n.get_translator('zh-CN')('missing.key'),
                         'missing.key')

    def test_resolve_lang_priority(self):
        class Handler:
            def __init__(self, cookie='', path='/', accept=''):
                self.headers = {'Accept-Language': accept}
                if cookie:
                    self.headers['Cookie'] = 'filer_lang=' + cookie
                self.path = path

        self.assertEqual(
            i18n.resolve_lang(Handler('zh-CN', '/?lang=en', 'en')), 'zh-CN')
        self.assertEqual(
            i18n.resolve_lang(Handler('', '/?lang=zh-CN', 'en')), 'zh-CN')
        self.assertEqual(
            i18n.resolve_lang(Handler('', '/', 'zh-CN,zh;q=0.9')), 'zh-CN')
        self.assertEqual(i18n.resolve_lang(Handler()), 'en')


if __name__ == '__main__':
    unittest.main()
