import struct

_CFB_MAGIC = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'
_MAXREGSECT = 0xFFFFFFFA


def _cfb_streams(data):
    if len(data) < 512 or not data.startswith(_CFB_MAGIC):
        raise ValueError('不是 OLE2 文档')
    sector_size = 1 << struct.unpack_from('<H', data, 0x1E)[0]
    mini_size = 1 << struct.unpack_from('<H', data, 0x20)[0]
    if sector_size < 128 or sector_size > 65536:
        raise ValueError('扇区大小异常')
    first_dir = struct.unpack_from('<I', data, 0x30)[0]
    mini_cutoff = struct.unpack_from('<I', data, 0x38)[0]
    first_minifat = struct.unpack_from('<I', data, 0x3C)[0]
    first_difat = struct.unpack_from('<I', data, 0x44)[0]
    difat_count = struct.unpack_from('<I', data, 0x48)[0]

    def sector_offset(sec):
        return (sec + 1) * sector_size

    difat = list(struct.unpack_from('<109I', data, 0x4C))
    per = sector_size // 4 - 1
    sec = first_difat
    seen = set()
    for _ in range(difat_count):
        if sec >= _MAXREGSECT or sec in seen:
            break
        seen.add(sec)
        off = sector_offset(sec)
        if off + sector_size > len(data):
            break
        vals = struct.unpack_from('<%dI' % (sector_size // 4), data, off)
        difat.extend(vals[:per])
        sec = vals[per]

    fat = []
    for s in difat:
        if s >= _MAXREGSECT:
            continue
        off = sector_offset(s)
        if off + sector_size > len(data):
            continue
        fat.extend(struct.unpack_from('<%dI' % (sector_size // 4), data, off))
    if not fat:
        raise ValueError('FAT 为空')

    def read_chain(start, size=None):
        out = bytearray()
        sec = start
        seen = set()
        while sec < _MAXREGSECT and sec not in seen:
            seen.add(sec)
            off = sector_offset(sec)
            if off >= len(data):
                break
            out += data[off:off + sector_size]
            if size is not None and len(out) >= size:
                break
            if sec >= len(fat):
                break
            sec = fat[sec]
        return bytes(out[:size]) if size is not None else bytes(out)

    directory = read_chain(first_dir)
    entries = {}
    root = None
    for i in range(0, len(directory) - 127, 128):
        ent = directory[i:i + 128]
        name_len = struct.unpack_from('<H', ent, 0x40)[0]
        if name_len < 2 or name_len > 64:
            continue
        name = ent[:name_len - 2].decode('utf-16-le', 'replace')
        etype = ent[0x42]
        start = struct.unpack_from('<I', ent, 0x74)[0]
        size = struct.unpack_from('<Q', ent, 0x78)[0]
        if etype in (2, 5):
            entries[name] = (etype, start, size)
        if etype == 5:
            root = (start, size)

    mini_stream = read_chain(root[0], root[1]) if root else b''
    minifat = []
    if first_minifat < _MAXREGSECT:
        raw = read_chain(first_minifat)
        if raw:
            minifat = list(struct.unpack_from('<%dI' % (len(raw) // 4), raw, 0))

    def read_mini(start, size):
        out = bytearray()
        sec = start
        seen = set()
        while sec < _MAXREGSECT and sec not in seen:
            seen.add(sec)
            off = sec * mini_size
            if off >= len(mini_stream):
                break
            out += mini_stream[off:off + mini_size]
            if len(out) >= size:
                break
            if sec >= len(minifat):
                break
            sec = minifat[sec]
        return bytes(out[:size])

    def get(name):
        ent = entries.get(name)
        if not ent:
            return None
        _, start, size = ent
        if size < mini_cutoff:
            return read_mini(start, size)
        return read_chain(start, size)

    return get
