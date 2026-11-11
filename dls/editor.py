import html
import os
import urllib.parse

from . import editors as _editors  # noqa: F401
from .config import MAX_EDIT_REQUEST_BYTES
from .paths import PathError, resolve_file
from .providers import (REGISTRY, EditContext, EditError, EditorPage,
                        SaveResult)
from .templates import _EDIT_TEMPLATE, _ICON_EDIT


class EditorMixin:
    def _edit_link(self, name, target, full):
        provider = REGISTRY.find_editor(name, full)
        if not provider:
            return ''
        try:
            if not provider.can_edit(full):
                return ''
        except Exception:
            return ''
        url = '/edit?' + urllib.parse.urlencode({'dir': target, 'name': name})
        t = self._t()
        title = html.escape(t('edit.edit_title', name=name), quote=True)
        label = html.escape(t('common.edit'), quote=False)
        return ('<a class="btn btn-edit" href="%s" title="%s">%s<span>%s</span></a>'
                % (html.escape(url, quote=True), title, _ICON_EDIT, label))

    def _serve_edit(self):
        qs = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        target = qs.get('dir', ['/'])[0] or '/'
        if not target.startswith('/'):
            target = '/' + target
        name = qs.get('name', [''])[0]
        ctx, error = self._make_edit_context(target, name)
        if error:
            return
        provider = REGISTRY.find_editor(name, ctx.path)
        if not provider or not provider.can_edit(ctx.path):
            self._preview_message(self._t()('edit.unsupported'), name, target)
            return
        try:
            page = provider.render(ctx)
        except EditError as e:
            self._send_edit_page(
                target, name, EditorPage(body=''),
                note=self._t()(e.key, **e.kwargs), status=e.status)
            return
        except Exception as e:
            self._send_edit_page(
                target, name, EditorPage(body=''), note=str(e), status=500)
            return
        self._send_edit_page(target, name, page)

    def _handle_edit(self):
        parsed = self._parse_edit_form()
        if parsed is None:
            self.send_error(400, 'Bad form request')
            return
        form, files = parsed
        target = form.get('dir', '') or '/'
        if not target.startswith('/'):
            target = '/' + target
        name = form.get('name', '') or ''
        ctx, error = self._make_edit_context(target, name, form=form)
        if error:
            return
        provider = REGISTRY.find_editor(name, ctx.path)
        if not provider or not provider.can_edit(ctx.path):
            self.send_error(403, 'Editing not allowed')
            return
        try:
            result = provider.save(ctx, files)
        except EditError as e:
            note = self._t()(e.key, **e.kwargs)
            try:
                page = provider.render(ctx)
            except Exception:
                page = EditorPage(body='')
            self._send_edit_page(target, name, page, note=note, status=e.status)
            return
        except Exception as e:
            try:
                page = provider.render(ctx)
            except Exception:
                page = EditorPage(body='')
            self._send_edit_page(target, name, page, note=str(e), status=500)
            return
        redirect = result.redirect if isinstance(result, SaveResult) else ''
        if not redirect:
            redirect = '/preview?' + urllib.parse.urlencode(
                {'dir': target, 'name': name})
        self.send_response(303)
        self.send_header('Location', urllib.parse.quote(redirect, safe='/?=&%'))
        self.end_headers()

    def _make_edit_context(self, target, name, form=None):
        try:
            _, target_dir, full = resolve_file(self, target, name)
        except PathError as e:
            self.send_error(e.status, e.message)
            return None, True
        if not os.path.isfile(full):
            self.send_error(404, 'Not found')
            return None, True
        if not os.access(full, os.R_OK):
            self.send_error(403, 'Read forbidden')
            return None, True
        return EditContext(self, name, target, target_dir, full, form=form), False

    def _parse_edit_form(self):
        ctype = (self.headers.get('Content-Type') or '').lower()
        if 'multipart/form-data' in ctype:
            fields = self._parse_multipart(limit=MAX_EDIT_REQUEST_BYTES)
            if not fields:
                return None
            form, files = {}, {}
            for key, field in fields.items():
                if field.get('filename'):
                    files[key] = field['content']
                else:
                    form[key] = field['content'].decode('utf-8', 'replace')
            return form, files
        form = self._parse_urlencoded(limit=MAX_EDIT_REQUEST_BYTES)
        if form is None:
            return None
        return form, {}

    def _send_edit_page(self, target, name, page, note='', status=200):
        back = '/preview?' + urllib.parse.urlencode(
            {'dir': target, 'name': name})
        rel = (target.rstrip('/') + '/' + name) if target != '/' else '/' + name
        url_path = urllib.parse.quote(urllib.parse.unquote(rel), safe='/')
        dl = url_path + '?dl=1'
        note_html = ''
        if note:
            note_html = '<div class="edit-error">%s</div>' % html.escape(note)
        body = (_EDIT_TEMPLATE
                .replace('{{FILENAME}}', html.escape(name))
                .replace('{{BACK}}', html.escape(back, quote=True))
                .replace('{{DL}}', html.escape(dl, quote=True))
                .replace('{{EDIT_HEAD}}', page.head or '')
                .replace('{{NOTE}}', note_html)
                .replace('{{BODY}}', page.body or ''))
        self._send_html(body, status=status)
