import html
import os

from dls.providers import EditContext, EditError, EditorPage, EditorProvider

MAX_BYTES = 1024 * 1024


def _parse_lines(text):
    items = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        done = stripped.lower().startswith('[x]')
        if stripped.startswith(('[ ]', '[x]', '[X]')):
            stripped = stripped[3:].strip()
        items.append((done, stripped))
    return items


def _render(ctx, text=None):
    if text is None:
        raw = ctx.read_bytes(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise EditError('edit.too_large', status=413)
        text = raw.decode('utf-8', 'replace')
    items = _parse_lines(text)
    st = os.stat(ctx.path)
    rows = []
    for index, (done, label) in enumerate(items):
        checked = ' checked' if done else ''
        rows.append((
            '<label class="todo-row">'
            '<input type="checkbox" name="done%d"%s>'
            '<input type="text" name="text%d" value="%s">'
            '</label>') % (index, checked, index, html.escape(label, quote=True)))
    body = (
        '<form class="editform" method="post" action="/edit">'
        '<input type="hidden" name="dir" value="%s">'
        '<input type="hidden" name="name" value="%s">'
        '<input type="hidden" name="count" value="%d">'
        '<input type="hidden" name="mtime_ns" value="%d">'
        '<input type="hidden" name="size" value="%d">'
        '<div class="edittoolbar">'
        '<button class="btn btn-save" type="submit">%s</button>'
        '<span class="editnote">%s</span>'
        '</div>'
        '<div class="todolist">%s</div>'
        '</form>'
    ) % (
        html.escape(ctx.target, quote=True),
        html.escape(ctx.name, quote=True),
        len(items),
        st.st_mtime_ns,
        st.st_size,
        html.escape(ctx.t('plugin.todo-editor.save')),
        html.escape(ctx.t('plugin.todo-editor.note')),
        ''.join(rows) or '<p class="editnote">%s</p>' % html.escape(
            ctx.t('plugin.todo-editor.empty')),
    )
    head = (
        '<style>'
        '.todolist{background:#fff;border:1px solid #e2e8f0;border-radius:10px;'
        'padding:14px 16px;box-shadow:0 2px 10px rgba(0,0,0,.06);}'
        '.todo-row{display:flex;align-items:center;gap:10px;padding:6px 0;'
        'border-bottom:1px solid #f1f5f9;}'
        '.todo-row:last-child{border-bottom:none;}'
        '.todo-row input[type=text]{flex:1;min-width:0;}'
        '</style>'
    )
    return EditorPage(body=body, head=head)


class TodoEditor(EditorProvider):
    id = 'todo'
    priority = 100

    def matches(self, name, path):
        return os.path.splitext(name)[1].lower() == '.todo'

    def can_edit(self, path):
        if os.path.islink(path) or not os.path.isfile(path):
            return False
        try:
            return (os.path.getsize(path) <= MAX_BYTES
                    and os.access(path, os.W_OK))
        except OSError:
            return False

    def render(self, ctx):
        return _render(ctx)

    def save(self, ctx, files=None):
        form = ctx.form or {}
        try:
            count = int(form.get('count', '0'))
        except (TypeError, ValueError):
            count = 0
        lines = []
        for index in range(max(0, min(count, 10000))):
            text = (form.get('text%d' % index) or '').strip()
            if not text:
                continue
            mark = '[x]' if form.get('done%d' % index) else '[ ]'
            lines.append('%s %s' % (mark, text))
        data = ('\n'.join(lines) + ('\n' if lines else '')).encode('utf-8')
        ctx.write_bytes(data)
        return None


def register(ctx):
    ctx.register_editor(TodoEditor())
    ctx.register_locale(os.path.join(ctx.dir, 'locales'))
