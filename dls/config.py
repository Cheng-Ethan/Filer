import os

FORCE_DOWNLOAD_EXTS = {'.json', '.js', '.mjs', '.css', '.map', '.txt', '.csv'}
MAX_UPLOAD_BYTES = 256 * 1024 * 1024
MAX_RECENT_DIRS = 5

_TEXT_ENCODINGS = ('utf-8', 'gb18030', 'big5', 'shift_jis')
_ALLOWED_ENCODINGS = {'utf-8', 'gb18030', 'big5', 'shift_jis',
                      'utf-16-le', 'utf-16-be', 'cp1252'}
_MAX_TEXT_PREVIEW_BYTES = 2 * 1024 * 1024
_MAX_PREVIEW_CHARS = 2 * 1024 * 1024
_MAX_ZIP_UNCOMPRESSED = 128 * 1024 * 1024

_PREVIEW_KINDS = {
    '.md': 'markdown', '.markdown': 'markdown',
    '.txt': 'text', '.log': 'text', '.csv': 'text', '.tsv': 'text',
    '.json': 'text', '.xml': 'text', '.ini': 'text', '.conf': 'text',
    '.cfg': 'text', '.yml': 'text', '.yaml': 'text', '.toml': 'text',
    '.properties': 'text', '.bat': 'text', '.cmd': 'text', '.ps1': 'text',
    '.sh': 'text', '.bash': 'text', '.py': 'text', '.js': 'text',
    '.mjs': 'text', '.css': 'text', '.sql': 'text', '.java': 'text',
    '.c': 'text', '.h': 'text', '.cpp': 'text', '.hpp': 'text',
    '.go': 'text', '.rs': 'text', '.php': 'text', '.rb': 'text',
    '.pl': 'text', '.lua': 'text', '.map': 'text', '.env': 'text',
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


def _preview_kind(name):
    return _PREVIEW_KINDS.get(os.path.splitext(name)[1].lower())
