import html
import os

from ..config import (_ALLOWED_ENCODINGS, _MAX_EDIT_BYTES, _is_text_name,
                      _preview_kind)
from ..providers import (REGISTRY, EditContext, EditError, EditorPage,
                         EditorProvider, SaveResult)
from ..textenc import (_bom_for, _decode_bytes, _detect_encoding,
                       _detect_newline, _encode_text, _looks_text_strict)


class TextEditorProvider(EditorProvider):
    id = 'core.text'
    priority = -100

    def matches(self, name, path):
        if _is_text_name(name):
            return True
        kind = _preview_kind(name)
        if kind is not None:
            return False
        try:
            with open(path, 'rb') as f:
                raw = f.read(8192)
        except OSError:
            return False
        return _looks_text_strict(raw) is not None

    def can_edit(self, path):
        if os.path.islink(path) or not os.path.isfile(path):
            return False
        try:
            if os.path.getsize(path) > _MAX_EDIT_BYTES:
                return False
        except OSError:
            return False
        return os.access(path, os.W_OK)

    def render(self, ctx):
        try:
            with open(ctx.path, 'rb') as f:
                raw = f.read(_MAX_EDIT_BYTES + 1)
        except OSError:
            raise EditError('edit.read_failed', status=404)
        if len(raw) > _MAX_EDIT_BYTES:
            raise EditError('edit.too_large', status=413)
        detected = _detect_encoding(raw)
        if detected is None:
            raise EditError('edit.not_text', status=415)
        form = ctx.form or {}
        if 'text' in form:
            text = form.get('text', '')
            selected = (form.get('enc') or '').lower()
            if selected not in _ALLOWED_ENCODINGS:
                selected = detected
        else:
            text = _decode_bytes(raw, detected)
            selected = detected
        options = sorted(_ALLOWED_ENCODINGS | {detected})
        enc_options = ''.join(
            '<option value="%s"%s>%s</option>' % (
                html.escape(enc, quote=True),
                ' selected' if enc == selected else '',
                html.escape(enc))
            for enc in options)
        st = os.stat(ctx.path)
        body = (
            '<form class="editform" method="post" action="/edit">'
            '<input type="hidden" name="dir" value="%s">'
            '<input type="hidden" name="name" value="%s">'
            '<input type="hidden" name="mtime_ns" value="%s">'
            '<input type="hidden" name="size" value="%s">'
            '<div class="edittoolbar">'
            '<label class="editfield">{{i18n:edit.encoding}} '
            '<select name="enc" class="tsel">%s</select></label>'
            '<button class="btn btn-save" type="submit">{{i18n:edit.save}}</button>'
            '<a class="btn" href="/preview?dir=%s&amp;name=%s">{{i18n:common.cancel}}</a>'
            '<span class="editnote">{{i18n:edit.note}}</span>'
            '</div>'
            '<textarea class="editarea" name="text" spellcheck="false" '
            'autocomplete="off">%s</textarea>'
            '</form>'
        ) % (
            html.escape(ctx.target, quote=True),
            html.escape(ctx.name, quote=True),
            st.st_mtime_ns,
            st.st_size,
            enc_options,
            html.escape(ctx.target, quote=True),
            html.escape(ctx.name, quote=True),
            html.escape(text, quote=False),
        )
        return EditorPage(body=body)

    def save(self, ctx, files=None):
        form = ctx.form or {}
        text = form.get('text', '')
        try:
            with open(ctx.path, 'rb') as f:
                raw = f.read(_MAX_EDIT_BYTES + 1)
        except OSError:
            raise EditError('edit.read_failed', status=404)
        original = _detect_encoding(raw)
        enc = (form.get('enc') or '').lower()
        if enc not in _ALLOWED_ENCODINGS:
            enc = original or 'utf-8'
        bom = _bom_for(raw, enc) if enc == original else b''
        if enc == 'utf-8-sig' and not bom:
            bom = b'\xef\xbb\xbf'
        data = _encode_text(text, enc, bom, _detect_newline(raw))
        if len(data) > _MAX_EDIT_BYTES:
            raise EditError('edit.too_large', status=413)
        ctx.write_bytes(data)
        return SaveResult()


REGISTRY.add_editor(TextEditorProvider())
