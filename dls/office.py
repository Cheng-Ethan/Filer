import hashlib
import os
import posixpath
import re
import shutil
import struct
import subprocess
import tempfile
import threading
import xml.etree.ElementTree as ET
import zipfile

from .cfb import _cfb_streams
from .config import _MAX_ZIP_UNCOMPRESSED

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PDF_CACHE = os.path.join(_ROOT, 'cache', 'office')
_PDF_LOCK = threading.Lock()
_IMG_LOCK = threading.Lock()
_IMAGE_DPI = 120


def _child_env():
    # 不把 FILER_AUTH / DL_AUTH 传给子进程，避免凭据通过环境泄露。
    return {k: v for k, v in os.environ.items()
            if k not in ('FILER_AUTH', 'DL_AUTH')}


def _local(tag):
    return tag.rsplit('}', 1)[-1]


def _zip_open(path):
    z = zipfile.ZipFile(path)
    if sum(i.file_size for i in z.infolist()) > _MAX_ZIP_UNCOMPRESSED:
        z.close()
        raise ValueError('压缩内容过大')
    return z


def _docx_text(path):
    with _zip_open(path) as z:
        xml = z.read('word/document.xml')
    root = ET.fromstring(xml)
    out = []
    for p in root.iter():
        if _local(p.tag) != 'p':
            continue
        buf = []
        for node in p.iter():
            name = _local(node.tag)
            if name == 't' and node.text:
                buf.append(node.text)
            elif name == 'tab':
                buf.append('\t')
            elif name in ('br', 'cr'):
                buf.append('\n')
        out.append(''.join(buf))
    return '\n'.join(out)


_REL_NS = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
_W_NS = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def _paragraph_blocks(p, rels):
    buf = []
    seq = []
    for node in p.iter():
        name = _local(node.tag)
        if name == 't' and node.text:
            buf.append(node.text)
        elif name == 'tab':
            buf.append('\t')
        elif name in ('br', 'cr'):
            buf.append('\n')
        elif name == 'blip':
            if buf:
                seq.append(('text', ''.join(buf)))
                buf = []
            rid = node.get(_REL_NS + 'embed') or node.get(_REL_NS + 'link')
            if rid in rels:
                seq.append(('image', rels[rid]))
    if buf:
        seq.append(('text', ''.join(buf)))
    return seq


def _table_rows(tbl, rels):
    rows = []
    for tr in tbl:
        if _local(tr.tag) != 'tr':
            continue
        cells = []
        for tc in tr:
            if _local(tc.tag) != 'tc':
                continue
            colspan = 1
            tcpr = next((n for n in tc if _local(n.tag) == 'tcPr'), None)
            if tcpr is not None:
                gs = next((n for n in tcpr if _local(n.tag) == 'gridSpan'), None)
                if gs is not None:
                    try:
                        colspan = int(gs.get(_W_NS + 'val') or gs.get('val') or 1)
                    except (TypeError, ValueError):
                        colspan = 1
            blocks = []
            for child in tc:
                tag = _local(child.tag)
                if tag == 'p':
                    part = _paragraph_blocks(child, rels)
                    if blocks and part:
                        blocks.append(('text', '\n'))
                    blocks.extend(part)
                elif tag == 'tbl':
                    for pp in child.iter():
                        if _local(pp.tag) == 'p':
                            part = _paragraph_blocks(pp, rels)
                            if blocks and part:
                                blocks.append(('text', '\n'))
                            blocks.extend(part)
            cells.append((colspan, blocks))
        if cells:
            rows.append(cells)
    return rows


def docx_blocks(path):
    with _zip_open(path) as z:
        names = set(z.namelist())
        rels = {}
        rel_name = 'word/_rels/document.xml.rels'
        if rel_name in names:
            root = ET.fromstring(z.read(rel_name))
            for rel in root:
                if 'image' not in (rel.get('Type') or ''):
                    continue
                rid = rel.get('Id')
                target = rel.get('Target')
                if not rid or not target:
                    continue
                target = target.replace('\\', '/').lstrip('/')
                part = posixpath.normpath(posixpath.join('word', target))
                if part in names:
                    rels[rid] = part
        root = ET.fromstring(z.read('word/document.xml'))
        body = next((n for n in root.iter() if _local(n.tag) == 'body'), None)
        if body is None:
            return []
        blocks = []

        def walk(container):
            for child in container:
                tag = _local(child.tag)
                if tag == 'p':
                    blocks.extend(_paragraph_blocks(child, rels))
                elif tag == 'tbl':
                    blocks.append(('table', _table_rows(child, rels)))
                elif tag == 'sdt':
                    content = next((n for n in child.iter()
                                    if _local(n.tag) == 'sdtContent'), None)
                    if content is not None:
                        walk(content)

        walk(body)
        return blocks


def _xlsx_text(path):
    with _zip_open(path) as z:
        names = set(z.namelist())
        shared = []
        if 'xl/sharedStrings.xml' in names:
            root = ET.fromstring(z.read('xl/sharedStrings.xml'))
            for si in root.iter():
                if _local(si.tag) != 'si':
                    continue
                shared.append(''.join(t.text or '' for t in si.iter()
                                      if _local(t.tag) == 't'))
        out = []
        sheets = sorted(
            (n for n in names if re.match(r'^xl/worksheets/sheet\d+\.xml$', n)),
            key=lambda x: int(re.search(r'(\d+)', x).group(1)))
        for sheet in sheets:
            out.append('【%s】' % sheet.split('/')[-1])
            root = ET.fromstring(z.read(sheet))
            for row in root.iter():
                if _local(row.tag) != 'row':
                    continue
                cells = []
                for c in row:
                    if _local(c.tag) != 'c':
                        continue
                    t = c.get('t')
                    v = next((n for n in c if _local(n.tag) == 'v'), None)
                    if t == 's' and v is not None and v.text:
                        try:
                            cells.append(shared[int(v.text)])
                        except (ValueError, IndexError):
                            cells.append('')
                    elif t == 'inlineStr':
                        cells.append(''.join(n.text or '' for n in c.iter()
                                             if _local(n.tag) == 't'))
                    else:
                        cells.append(v.text if v is not None and v.text else '')
                if any(cells):
                    out.append('\t'.join(cells))
        return '\n'.join(out)


def _pptx_text(path):
    with _zip_open(path) as z:
        slides = [n for n in z.namelist()
                  if re.match(r'^ppt/slides/slide\d+\.xml$', n)]
        slides.sort(key=lambda x: int(re.search(r'(\d+)\.xml$', x).group(1)))
        out = []
        for idx, slide in enumerate(slides, 1):
            out.append('【第 %d 页】' % idx)
            root = ET.fromstring(z.read(slide))
            for node in root.iter():
                if _local(node.tag) == 't' and node.text:
                    out.append(node.text)
        return '\n'.join(out)


def _rtf_text(path):
    with open(path, 'rb') as f:
        text = f.read().decode('latin-1', 'replace')

    def hexrepl(m):
        try:
            return bytes.fromhex(m.group(1)).decode('gb18030')
        except Exception:
            return ''

    text = re.sub(r"\\'([0-9a-fA-F]{2})", hexrepl, text)
    text = re.sub(r'\\u(-?\d+)\??', lambda m: chr(int(m.group(1)) % 65536), text)
    text = re.sub(r'\\par[d]?\b', '\n', text)
    text = re.sub(r'\\(tab|cell|row)\b', '\t', text)
    text = re.sub(r'\\[a-zA-Z]+-?\d* ?', '', text)
    text = text.replace('\\{', '{').replace('\\}', '}').replace('\\\\', '\\')
    text = re.sub(r'[{}\\]', '', text)
    return re.sub(r'\n{3,}', '\n\n', text)


def _clean_doc_text(text):
    text = text.replace('\r', '\n').replace('\x0b', '\n').replace('\x0c', '\n')
    text = text.replace('\x07', '\t')
    text = re.sub(r'\x13[^\x14\x15]*\x14([^\x15]*)\x15', r'\1', text)
    text = re.sub(r'\x13[^\x15]*\x15', '', text)
    text = re.sub(r'[\x00-\x08\x0e-\x1f]', '', text)
    return re.sub(r'\n{4,}', '\n\n\n', text).strip('\n')


def _doc_text(path):
    with open(path, 'rb') as f:
        data = f.read()
    get = _cfb_streams(data)
    wd = get('WordDocument')
    if not wd or len(wd) < 0x01AA:
        raise ValueError('缺少 WordDocument 流')
    flags = struct.unpack_from('<H', wd, 0x0A)[0]
    if flags & 0x0100:
        raise ValueError('文档已加密')
    table = get('1Table' if (flags & 0x0200) else '0Table')
    if table is None:
        table = get('1Table') or get('0Table') or b''
    fc_clx = struct.unpack_from('<I', wd, 0x01A2)[0]
    lcb_clx = struct.unpack_from('<I', wd, 0x01A6)[0]
    pieces = []
    if lcb_clx and fc_clx + lcb_clx <= len(table):
        clx = table[fc_clx:fc_clx + lcb_clx]
        i = 0
        pcdt = None
        while i < len(clx):
            if clx[i] == 0x01:
                if i + 3 > len(clx):
                    break
                i += 3 + struct.unpack_from('<H', clx, i + 1)[0]
            elif clx[i] == 0x02:
                if i + 5 > len(clx):
                    break
                lcb = struct.unpack_from('<I', clx, i + 1)[0]
                pcdt = clx[i + 5:i + 5 + lcb]
                break
            else:
                break
        if pcdt and len(pcdt) >= 4:
            n = (len(pcdt) - 4) // 12
            cps = struct.unpack_from('<%dI' % (n + 1), pcdt, 0)
            for k in range(n):
                off = 4 * (n + 1) + k * 8 + 2
                if off + 4 > len(pcdt):
                    break
                fc = struct.unpack_from('<I', pcdt, off)[0]
                length = cps[k + 1] - cps[k]
                if length <= 0:
                    continue
                if fc & 0x40000000:
                    pos = (fc & ~0x40000000) // 2
                    raw = wd[pos:pos + length]
                    pieces.append(raw.decode('cp1252', 'replace'))
                else:
                    raw = wd[fc:fc + length * 2]
                    pieces.append(raw.decode('utf-16-le', 'replace'))
    if pieces:
        return _clean_doc_text(''.join(pieces))
    fc_min = struct.unpack_from('<I', wd, 0x18)[0]
    fc_mac = struct.unpack_from('<I', wd, 0x1C)[0]
    if 0 < fc_min < fc_mac <= len(wd):
        return _clean_doc_text(wd[fc_min:fc_mac].decode('gb18030', 'replace'))
    raise ValueError('无法定位正文')


def _office_text(path, kind):
    if kind == 'docx':
        return _docx_text(path)
    if kind == 'xlsx':
        return _xlsx_text(path)
    if kind == 'pptx':
        return _pptx_text(path)
    if kind == 'doc':
        return _doc_text(path)
    if kind == 'rtf':
        return _rtf_text(path)
    raise ValueError('不支持的类型')


def _soffice():
    return shutil.which('soffice') or shutil.which('libreoffice')


def office_pdf(path):
    exe = _soffice()
    if not exe:
        return None
    try:
        st = os.stat(path)
    except OSError:
        return None
    key = hashlib.sha256(('%s|%d|%d' % (os.path.abspath(path), st.st_mtime_ns,
                                         st.st_size)).encode('utf-8')).hexdigest()
    out = os.path.join(_PDF_CACHE, key + '.pdf')
    if os.path.isfile(out) and os.path.getsize(out) > 0:
        return out
    os.makedirs(_PDF_CACHE, exist_ok=True)
    with _PDF_LOCK:
        if os.path.isfile(out) and os.path.getsize(out) > 0:
            return out
        tmpdir = tempfile.mkdtemp(prefix='lo_', dir=_PDF_CACHE)
        profile = os.path.join(tmpdir, 'profile')
        try:
            cmd = [exe, '--headless', '--norestore', '--nologo',
                   '-env:UserInstallation=file://' + profile,
                   '--convert-to', 'pdf', '--outdir', tmpdir, path]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=120, env=_child_env())
            produced = os.path.join(
                tmpdir, os.path.splitext(os.path.basename(path))[0] + '.pdf')
            if not os.path.isfile(produced):
                pdfs = [os.path.join(tmpdir, n) for n in os.listdir(tmpdir)
                        if n.lower().endswith('.pdf')]
                produced = pdfs[0] if pdfs else None
            if produced and os.path.isfile(produced):
                os.replace(produced, out)
                return out
            return None
        except Exception:
            return None
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


def _run_cmd(cmd, timeout=120):
    return subprocess.run(cmd, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, timeout=timeout,
                          env=_child_env())


def office_pdf_page_count(pdf):
    exe = shutil.which('pdfinfo')
    if not exe:
        return 0
    try:
        out = _run_cmd([exe, pdf], 30).stdout
        m = re.search(rb'^Pages:\s*(\d+)', out, re.M)
        return int(m.group(1)) if m else 0
    except Exception:
        return 0


def office_pdf_page(pdf, page):
    exe = shutil.which('pdftoppm')
    if not exe:
        return None
    key = os.path.splitext(os.path.basename(pdf))[0]
    outdir = os.path.join(_PDF_CACHE, key)
    out = os.path.join(outdir, 'page-%d.jpg' % page)
    if os.path.isfile(out) and os.path.getsize(out) > 0:
        return out
    os.makedirs(outdir, exist_ok=True)
    with _IMG_LOCK:
        if os.path.isfile(out) and os.path.getsize(out) > 0:
            return out
        tmpdir = tempfile.mkdtemp(prefix='pg_', dir=_PDF_CACHE)
        try:
            prefix = os.path.join(tmpdir, 'p')
            _run_cmd([exe, '-jpeg', '-r', str(_IMAGE_DPI),
                      '-f', str(page), '-l', str(page), pdf, prefix], 120)
            files = [n for n in os.listdir(tmpdir) if n.lower().endswith('.jpg')]
            if not files:
                return None
            os.replace(os.path.join(tmpdir, files[0]), out)
            return out
        except Exception:
            return None
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
