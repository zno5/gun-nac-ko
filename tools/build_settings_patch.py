#!/usr/bin/env python3
"""Add 8x16 settings to the verified Japanese-based story prototype.

Keep the original input, limits, sound control, hidden-option gate and game state.
Only replace drawing, settings CHR selection and cursor vertical alignment.
"""
from pathlib import Path
import csv, hashlib, io, json, re, struct
from font_policy import apply_font_policy, POLICY

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/settings_patch'
OUT.mkdir(parents=True, exist_ok=True)
source = next((ROOT / 'jp').glob('*.nes')).read_bytes()
story = ROOT / 'build/story_patch'
base = (story / 'Gun Nac (Korean story prototype).nes').read_bytes()
story_manifest = json.loads((story / 'manifest.json').read_text())
assert story_manifest['font_policy'] == POLICY
digest = lambda b: hashlib.sha256(b).hexdigest()
assert digest(base) == story_manifest['target_sha256']
assert digest(source) == story_manifest['source_sha256']
csv_bytes = (ROOT / 'translation/text.csv').read_bytes()
assert digest(csv_bytes) == story_manifest['source_csv_sha256']
rows = {r['jp_text_offset']: r for r in csv.DictReader(io.StringIO(csv_bytes.decode('utf-8-sig')))}
overrides = json.loads((ROOT / 'translation/display_overrides.json').read_text())
def text_at(offset):
    key = f'0x{offset:06X}'
    if key in overrides:
        assert rows[key]['ko_translation'] == overrides[key]['reviewed_ko_text']
        return overrides[key]['text']
    return rows[key]['ko_translation']

# Full-width rows erase both halves of the previous setting when labels shorten.
specs = [
    ('area', 0x180, 10, [text_at(0x1489) + str(v) for v in range(9)]),
    ('sound', 0x1ae, 12, [text_at(0x1491) + f'{v:02X}' for v in range(0x49)]),
    ('difficulty', 0x4c, 14, [text_at(0x149f) + str(v + 1) + ' ' + text_at(p)
                            for v, p in enumerate([0x14db, 0x14f0, 0x1504, 0x1519])]),
    ('counterattack', 0x4e, 16, [text_at(0x14ad) + '   ' + text_at(p) for p in [0x1528, 0x152d]]),
    ('priority', 0xf1, 18, [text_at(p) for p in [0x154a, 0x155e]]),
    ('weapon', 0x1b6, 20, [text_at(0x14b9).replace('{무기번호}', str(v + 1)) for v in range(5)]),
    ('bomb', 0x1b7, 22, [text_at(0x14c4).replace('{폭탄번호}', c) for c in 'FBTW']),
    ('death', 0x1be, 24, [text_at(p) for p in [0x1532, 0x153e]]),
]
title = text_at(0x1473)
characters = set(' ' + title + ''.join(s for _, _, _, values in specs for s in values))
# Read the original BDF pixels directly; never rescale or squeeze Hangul.
bdf = (ROOT / 'assets/fonts/Galmuri11-Condensed.bdf').read_text()
masks = {}
for block in bdf.split('STARTCHAR ')[1:]:
    cp = int(re.search(r'^ENCODING (-?\d+)', block, re.M)[1])
    if cp < 0 or chr(cp) not in characters:
        continue
    w, h, ox, oy = map(int, re.search(r'^BBX (.*)', block, re.M)[1].split())
    bitmap = block.split('BITMAP\n', 1)[1].split('ENDCHAR', 1)[0].splitlines()
    mask = bytearray(16)
    for row, bits in enumerate(bitmap):
        for col in range(w):
            if int(bits, 16) & (1 << (len(bits) * 4 - col - 1)):
                x, y = ox + col, 14 - oy - h + row
                assert 0 <= x < 8 and 0 <= y < 16
                mask[y] |= 0x80 >> x
    masks[chr(cp)] = apply_font_policy(chr(cp), bytes(mask))
assert set(masks) == characters
patterns = [bytes(16)]
glyphs = {}
for c in sorted(characters):
    pair = []
    for half in (0, 1):
        pattern = masks[c][half * 8:half * 8 + 8] * 2
        if pattern not in patterns:
            # EB94 clears the nametable with original ASCII space ($20).
            if len(patterns) == 0x20:
                patterns.append(bytes(16))
            patterns.append(pattern)
        pair.append(patterns.index(pattern))
    glyphs[c] = pair
assert len(patterns) < 255
font = b''.join(patterns).ljust(4096, b'\0')
assert font[0x200:0x210] == font[0xff0:] == bytes(16)

data = bytearray()
def stream(row, text, x=6, width=24):
    assert len(text) <= width and x + width <= 32
    ptr = 0x8000 + len(data)
    for half in (0, 1):
        data.extend(struct.pack('<HB', 0x2000 + (row + half) * 32 + x, width))
        data.extend(glyphs[c][half] for c in text.ljust(width))
    data.extend(b'\0\0\0')
    return ptr
title_ptr = stream(6, title, (32 - len(title)) // 2, len(title))
tables = {}
entries = []
for name, ram, row, values in specs:
    ptrs = [stream(row, s) for s in values]
    tables[name] = 0x8000 + len(data)
    data.extend(b''.join(struct.pack('<H', p) for p in ptrs))
    entries.append(dict(name=name, ram=hex(ram), row=row, x=6, width=24,
                        values=values, pointers=[hex(p) for p in ptrs]))
assert len(data) <= 8192

class Asm:
    def __init__(self, base):
        self.base = base; self.code = bytearray(); self.labels = {}; self.fix = []
    def label(self, name): self.labels[name] = self.base + len(self.code)
    def emit(self, *bs): self.code.extend(bs)
    def abs(self, op, addr): self.emit(op, addr & 255, addr >> 8)
    def ref(self, op, name):
        self.emit(op, 0, 0); self.fix.append((len(self.code) - 2, name, False))
    def branch(self, op, name):
        self.emit(op, 0); self.fix.append((len(self.code) - 1, name, True))
    def finish(self):
        for off, name, relative in self.fix:
            addr = self.labels[name]
            if relative:
                delta = addr - (self.base + off + 1)
                assert -128 <= delta < 128
                self.code[off] = delta & 255
            else: self.code[off:off + 2] = struct.pack('<H', addr)
        return self.code

# Reclaimed story bytes, after the existing story renderer/IRQ. R7 stays mapped.
a = Asm(0xaa00)
assert story_manifest['injection_bytes'] + 0xa97d <= a.base
a.label('title')
a.emit(0xa5, 0x00, 0x48, 0xa9, 0x11); a.abs(0x20, 0xe629)
a.emit(0xa9, title_ptr & 255, 0x85, 0x12, 0xa9, title_ptr >> 8, 0x85, 0x13)
a.ref(0x20, 'render'); a.ref(0x4c, 'restore')
a.label('update')
a.emit(0xa5, 0x00, 0x48, 0xa9, 0x11); a.abs(0x20, 0xe629)
for i, (name, ram, row, values) in enumerate(specs):
    if i == 5:
        a.abs(0xad, 0xfff9); a.branch(0xf0, 'restore')
    a.abs(0xad, ram)
    # Original text selection treats every nonzero flag as true. In particular
    # $F1 can become $FF outside settings; do not use it as an unchecked index.
    if name in ('counterattack', 'priority', 'death'):
        a.emit(0xf0, 0x02, 0xa9, 0x01)
    a.emit(0x0a, 0xaa)
    a.abs(0xbd, tables[name]); a.emit(0x85, 0x12)
    a.abs(0xbd, tables[name] + 1); a.emit(0x85, 0x13)
    a.ref(0x20, 'render')
a.label('restore'); a.emit(0x68); a.abs(0x20, 0xe629)
a.label('noop'); a.emit(0x60)
a.label('render')
a.emit(0xa0, 0x00, 0xb1, 0x12, 0x85, 0x14, 0xc8, 0xb1, 0x12, 0x85, 0x15, 0xc8, 0xb1, 0x12)
a.branch(0xf0, 'done'); a.emit(0x85, 0x11, 0xa9, 0x03)
a.ref(0x20, 'advance'); a.abs(0x20, 0xe875)
a.emit(0xa5, 0x11); a.ref(0x20, 'advance'); a.ref(0x4c, 'render')
a.label('done'); a.abs(0x4c, 0xe7d6)
a.label('advance'); a.emit(0x18, 0x65, 0x12, 0x85, 0x12)
a.branch(0x90, 'advanced'); a.emit(0xe6, 0x13)
a.label('advanced'); a.emit(0x60)
code = a.finish()
assert a.base + len(code) < 0xaeb1  # End of reclaimed story text.
rom = bytearray(base)
rom[16 + 0x22000:16 + 0x22000 + len(data)] = data  # PRG bank 17.
rom[0x40010 + 0x22000:0x40010 + 0x23000] = font  # CHR banks 88/8A.
rom[a.base - 0x8000 + 16:a.base - 0x8000 + 16 + len(code)] = code
hooks = []
def patch(cpu, before, after):
    off = cpu - 0x8000 + 16
    assert base[off:off + len(before)] == before, hex(cpu)
    assert len(before) == len(after)
    rom[off:off + len(after)] = after
    hooks.append(dict(cpu=hex(cpu), before=before.hex(), after=after.hex()))
patch(0x9250, b'\x7c', b'\x88')
patch(0x9257, b'\x7e', b'\x8a')
patch(0x926c, bytes.fromhex('20 e3 e6'), b'\x20' + struct.pack('<H', a.labels['title']))
patch(0x927c, bytes.fromhex('20 e3 e6'), b'\x20' + struct.pack('<H', a.labels['noop']))
patch(0x9395, bytes.fromhex('a9 21 85'), b'\x4c' + struct.pack('<H', a.labels['update']))
patch(0x92c5, b'\x4e', b'\x54')
dest = OUT / 'Gun Nac (Korean settings prototype).nes'
dest.write_bytes(rom)
ips = bytearray(b'PATCH'); i = 0
while i < len(rom):
    if i < len(source) and source[i] == rom[i]: i += 1; continue
    start = i; i += 1
    while i < len(rom) and i - start < 65535 and (i >= len(source) or source[i] != rom[i]): i += 1
    ips += start.to_bytes(3, 'big') + (i - start).to_bytes(2, 'big') + rom[start:i]
ips += b'EOF'
applied = bytearray(source); pos = 5
while ips[pos:pos + 3] != b'EOF':
    off = int.from_bytes(ips[pos:pos + 3], 'big'); n = int.from_bytes(ips[pos + 3:pos + 5], 'big'); pos += 5
    if len(applied) < off + n: applied.extend(bytes(off + n - len(applied)))
    applied[off:off + n] = ips[pos:pos + n]; pos += n
assert applied == rom
(OUT / 'gun_nac_ko_settings.ips').write_bytes(ips)
manifest = dict(scope='Opening, ending and settings; Japanese base; hidden-option availability unchanged',
                source_sha256=digest(source), base_story_sha256=digest(base), target_sha256=digest(rom),
                source_csv_sha256=digest(csv_bytes), font_sha256=digest((ROOT / 'assets/fonts/Galmuri11-Condensed.bdf').read_bytes()),
                display_overrides_sha256=digest((ROOT / 'translation/display_overrides.json').read_bytes()),
                mapper=4, prg_size=262144, chr_size=262144, data_bank=17, data_bytes=len(data),
                font_banks=[0x88, 0x8a], font_tiles=len(patterns), injection_bytes=len(code),
                injection_cpu=a.labels, hooks=hooks, ips_roundtrip=True,
                title=dict(text=title, row=6, x=(32-len(title))//2), settings=entries)
manifest['font_policy'] = POLICY
(OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
(OUT / 'settings.chr').write_bytes(font)
(OUT / 'glyphs.json').write_text(json.dumps(glyphs, ensure_ascii=False, indent=2))
(OUT / 'injection.bin').write_bytes(code)
print(json.dumps({k: v for k, v in manifest.items() if k not in ('settings', 'hooks')}, ensure_ascii=False, indent=2))
