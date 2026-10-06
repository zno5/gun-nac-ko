"""Native BDF raster and local PNG helpers; no embedded font data."""
import re,struct,zlib
def font(path, legacy=False):
    result = {}
    for block in path.read_text().split('STARTCHAR ')[1:]:
        enc = re.search(r'^ENCODING (-?\d+)', block, re.M)
        if not enc or int(enc[1]) < 0:
            continue
        cp = int(enc[1])
        if legacy:
            try:
                char = bytes([(cp >> 8) + 128, (cp & 255) + 128]).decode('euc_kr')
            except (ValueError, UnicodeDecodeError):
                continue
        else:
            char = chr(cp)
        box = tuple(map(int, re.search(r'^BBX (.*)', block, re.M)[1].split()))
        bitmap = re.split(r'^BITMAP[ \t]*\n', block, maxsplit=1, flags=re.M)[1].split('ENDCHAR')[0].splitlines()
        result[char] = box, bitmap
    return result

def glyph(fontdata, c, baseline, width):
    if c == ' ':
        return [0] * 16
    (w, h, ox, oy), bitmap = fontdata[c]
    rows = [0] * 16
    for iy, line in enumerate(bitmap):
        bits = int(line, 16)
        for ix in range(w):
            if bits & (1 << (len(line)*4 - ix - 1)):
                x, y = ox + ix, baseline - oy - h + iy
                assert 0 <= x < width and 0 <= y < 16, (c, x, y)
                rows[y] |= 1 << (width - x - 1)
    return rows

def png(path, w, h, rgb):
    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data))
    raw = b''.join(b'\0' + bytes(rgb[y*w*3:(y+1)*w*3]) for y in range(h))
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w,h,8,2,0,0,0)) + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))

def readpng(path):
    b = path.read_bytes(); p = 8; data = b''
    while p < len(b):
        n = int.from_bytes(b[p:p+4], 'big'); tag = b[p+4:p+8]; d = b[p+8:p+8+n]; p += n+12
        if tag == b'IHDR':
            w,h,depth,color,*_ = struct.unpack('>IIBBBBB',d)
            assert (w,h,depth,color) == (256,240,8,2)
        elif tag == b'IDAT':
            data += d
    raw = zlib.decompress(data)
    assert all(raw[y*769] == 0 for y in range(240))
    return bytearray(b''.join(raw[y*769+1:(y+1)*769] for y in range(240)))
