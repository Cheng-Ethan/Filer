import os

FORCE_DOWNLOAD_EXTS = {'.json', '.js', '.mjs', '.css', '.map', '.txt', '.csv'}
MAX_UPLOAD_BYTES = 256 * 1024 * 1024
MAX_RECENT_DIRS = 5

_TEXT_ENCODINGS = ('utf-8', 'gb18030', 'big5', 'shift_jis')
_ALLOWED_ENCODINGS = {'utf-8', 'gb18030', 'big5', 'shift_jis',
                      'utf-16-le', 'utf-16-be', 'utf-32-le', 'utf-32-be',
                      'cp1252'}
_MAX_TEXT_PREVIEW_BYTES = 2 * 1024 * 1024
_MAX_PREVIEW_CHARS = 2 * 1024 * 1024
_MAX_ZIP_UNCOMPRESSED = 128 * 1024 * 1024
_MAX_EDIT_BYTES = 2 * 1024 * 1024
MAX_EDIT_REQUEST_BYTES = 16 * 1024 * 1024
MAX_EDIT_BACKUPS = 20

_PREVIEW_KINDS = {
    '.md': 'markdown', '.markdown': 'markdown',
    '.txt': 'text', '.log': 'text', '.csv': 'text', '.tsv': 'text',
    '.rst': 'text', '.tex': 'text',
    '.json': 'text', '.xml': 'text', '.ini': 'text', '.conf': 'text',
    '.cfg': 'text', '.yml': 'text', '.yaml': 'text', '.toml': 'text',
    '.properties': 'text', '.bat': 'text', '.cmd': 'text', '.ps1': 'text',
    '.sh': 'text', '.bash': 'text', '.py': 'text', '.js': 'text',
    '.mjs': 'text', '.css': 'text', '.sql': 'text', '.java': 'text',
    '.c': 'text', '.h': 'text', '.cpp': 'text', '.hpp': 'text',
    '.go': 'text', '.rs': 'text', '.php': 'text', '.rb': 'text',
    '.pl': 'text', '.lua': 'text', '.r': 'text', '.map': 'text',
    '.env': 'text', '.ts': 'text', '.tsx': 'text', '.jsx': 'text',
    '.cjs': 'text', '.cs': 'text', '.kt': 'text', '.kts': 'text',
    '.swift': 'text', '.scala': 'text', '.vue': 'text', '.svelte': 'text',
    '.docx': 'docx', '.xlsx': 'xlsx', '.pptx': 'pptx',
    '.doc': 'doc', '.wps': 'doc', '.et': 'xlsx', '.dps': 'pptx',
    '.rtf': 'rtf',
    '.pdf': 'pdf',
    '.png': 'image', '.jpg': 'image', '.jpeg': 'image', '.gif': 'image',
    '.webp': 'image', '.bmp': 'image', '.ico': 'image', '.svg': 'svg',
    '.html': 'html', '.htm': 'html',
    '.mp3': 'audio', '.wav': 'audio', '.ogg': 'audio', '.m4a': 'audio',
    '.mp4': 'video', '.webm': 'video', '.ogv': 'video',
}


_EDIT_TEXT_EXTS = frozenset(
    ext for ext, kind in _PREVIEW_KINDS.items() if kind in ('text', 'markdown')
) | {'.html', '.htm'}

# os.path.splitext('.env') does not treat the leading dot as an extension,
# so these names need an explicit allowlist.
_EDIT_TEXT_BASENAMES = frozenset(name.lower() for name in (
    '.env', '.editorconfig', '.gitignore', '.gitattributes', '.dockerignore',
    '.npmrc', '.nvmrc', '.prettierrc', '.eslintrc', '.babelrc', '.bashrc',
    '.zshrc', '.profile', '.vimrc', '.wgetrc', 'makefile', 'dockerfile',
    'containerfile', 'rakefile', 'gemfile', 'procfile', 'readme', 'license',
    'changelog', 'authors', 'notice',
))


def _preview_kind(name):
    return _PREVIEW_KINDS.get(os.path.splitext(name)[1].lower())


def _is_text_name(name):
    base = os.path.basename(name).lower()
    if base in _EDIT_TEXT_BASENAMES:
        return True
    return os.path.splitext(name)[1].lower() in _EDIT_TEXT_EXTS
