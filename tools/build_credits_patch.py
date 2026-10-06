#!/usr/bin/env python3
"""JP-based settings/story build plus two-tile scrolling credits, original logos."""
from pathlib import Path
import csv, hashlib, io, json, struct
from font_policy import POLICY
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'build/credits_patch'; OUT.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
source=next((ROOT/'jp').glob('*.nes')).read_bytes()
base=(ROOT/'build/settings_patch/Gun Nac (Korean settings prototype).nes').read_bytes()
bm=json.loads((ROOT/'build/settings_patch/manifest.json').read_text())
assert sha(base)==bm['target_sha256'] and sha(source)==bm['source_sha256']
assert bm['font_policy']==POLICY
csv_bytes=(ROOT/'translation/text.csv').read_bytes()
assert sha(csv_bytes)==bm['source_csv_sha256']
preview=json.loads((ROOT/'build/font_preview/manifest.json').read_text())
assert preview['font_policy']==POLICY
assert preview['source_csv_sha256']==sha(csv_bytes)
assert preview['font_sha256']==sha((ROOT/'assets/fonts/Galmuri11-Condensed.bdf').read_bytes())
rows={int(r['jp_record_offset'],16):r for r in csv.DictReader(io.StringIO(csv_bytes.decode('utf-8-sig'))) if r['group']=='credits'}
glyphs=json.loads((ROOT/'build/font_preview/group_credits_glyphs.json').read_text())
f=(ROOT/'build/font_preview/group_credits.chr').read_bytes()
count=max(t for pair in glyphs.values() for t in pair)+1
patterns=[f[i*16:i*16+8]*2 for i in range(count)]
logos={}
for tile in list(range(0x60,0x7b))+list(range(0x7f,0x83)):
    off=0x20010+0x1f000+tile*16
    pat=source[off:off+16]
    if pat not in patterns:patterns.append(pat)
    logos[tile]=patterns.index(pat)
assert len(patterns)<255
font=b''.join(patterns).ljust(4096,b'\0');assert font[0xff0:]==bytes(16)
# Original FE spacing and packed two-row logo commands become bounded events.
events=[];p=0x1801
while source[p]!=255:
    if source[p]==254:
        events.append(dict(kind='blank',records=[],tiles=[0]*64));p+=1;continue
    canvas=[0]*64;items=[]
    def consume(half=None):
        global p
        start=p;pos=source[p];p+=1;end=source.index(254,p)
        raw=source[p:end];p=end+1;r=rows[start];x=pos&31
        if r['review_status']=='로고 유지':
            assert half is not None
            ids=[logos[t] for t in raw]
            canvas[half*32+x:half*32+x+len(ids)]=ids
        elif r['review_status']!='배치용 공백':
            s=r['ko_translation'];assert x+len(s)<=30,(start,s)
            for h in (0,1):canvas[h*32+x:h*32+x+len(s)]=[glyphs[c][h] for c in s]
        items.append(dict(record=f'0x{start:06X}',text=r['ko_translation'],x=x,kind=r['review_status']))
        return pos
    if source[p]>=32:
        consume(0);consume(1)
    else:consume(1)
    events.append(dict(kind='row',records=items,tiles=canvas))
data=bytearray()
for i,e in enumerate(events):
    e['index']=i;e['pointer']=hex(0x8000+len(data))
    data.append(0 if e['kind']=='blank' else 1)
    if e['kind']=='row':data.extend(e['tiles'])
    e['next_pointer']=hex(0x8000+len(data))
end_ptr=0x8000+len(data);data.append(255);assert len(data)<=8192
assert {r['record'] for e in events for r in e['records']}=={f'0x{off:06X}' for off in rows}
class Asm:
    def __init__(self,base):self.base=base;self.code=bytearray();self.labels={};self.fix=[]
    def label(self,n):self.labels[n]=self.base+len(self.code)
    def emit(self,*bs):self.code.extend(bs)
    def abs(self,op,addr):self.emit(op,addr&255,addr>>8)
    def ref(self,op,n):self.emit(op,0,0);self.fix.append((len(self.code)-2,n,False))
    def branch(self,op,n):self.emit(op,0);self.fix.append((len(self.code)-1,n,True))
    def finish(self):
        for off,n,rel in self.fix:
            addr=self.labels[n]
            if rel:
                d=addr-(self.base+off+1);assert -128<=d<128;self.code[off]=d&255
            else:self.code[off:off+2]=struct.pack('<H',addr)
        return self.code
# Existing settings injection ends below AB20. No new persistent RAM is needed.
a=Asm(0xab20);assert 0xaa00+bm['injection_bytes']<=a.base
a.label('event');a.emit(0xa5,0x00,0x48,0xa9,0x12);a.abs(0x20,0xe629)
a.emit(0xa5,0x2f,0x85,0x12,0xa5,0x30,0x85,0x13,0xa0,0x00,0xb1,0x12,0xc9,0xff)
a.branch(0xf0,'end');a.emit(0x48,0xa9,0x01);a.ref(0x20,'advance');a.emit(0x68);a.branch(0xf0,'save')
# Two 32-byte raw rows stay inside the original queue's per-packet budget.
a.emit(0xa9,0x20,0x85,0x11);a.abs(0x20,0xe875)
a.emit(0xa9,0x20);a.ref(0x20,'advance')
a.emit(0x18,0xa5,0x14,0x69,0x20,0x85,0x14);a.branch(0x90,'bottom');a.emit(0xe6,0x15)
a.label('bottom');a.emit(0xa9,0x20,0x85,0x11);a.abs(0x20,0xe875)
a.emit(0xa9,0x20);a.ref(0x20,'advance');a.abs(0x20,0xe7d6)
a.label('save');a.emit(0xa5,0x12,0x85,0x2f,0xa5,0x13,0x85,0x30,0x68);a.abs(0x20,0xe629);a.abs(0x4c,0x95ad)
a.label('end');a.emit(0x68);a.abs(0x20,0xe629);a.emit(0xa9,0x01);a.abs(0x8d,0x0180);a.abs(0x4c,0x9692)
a.label('advance');a.emit(0x18,0x65,0x12,0x85,0x12);a.branch(0x90,'advanced');a.emit(0xe6,0x13);a.label('advanced');a.emit(0x60)
code=a.finish();assert a.base+len(code)<=0xaeb1
rom=bytearray(base)
rom[0x24010:0x24010+len(data)]=data # PRG bank 18
rom[0x63010:0x64010]=font # CHR banks 8C/8E
rom[a.base-0x8000+16:a.base-0x8000+16+len(code)]=code
hooks=[]
def patch(cpu,before,after):
    off=cpu-0x8000+16;assert base[off:off+len(before)]==before,(hex(cpu),base[off:off+len(before)].hex());assert len(before)==len(after)
    rom[off:off+len(after)]=after;hooks.append(dict(cpu=hex(cpu),before=before.hex(),after=after.hex()))
patch(0x95a6,b'\xf1',b'\x00');patch(0x95aa,b'\x97',b'\x80')
patch(0x9642,bytes.fromhex('a5 2f 85'),b'\x4c'+struct.pack('<H',a.labels['event']))
# Shared story IRQ already identifies credits by $30 < $A8.
patch(0xa9c5,b'\x7c',b'\x8c')
dest=OUT/'Gun Nac (Korean credits prototype).nes';dest.write_bytes(rom)
ips=bytearray(b'PATCH');i=0
while i<len(rom):
    if i<len(source) and source[i]==rom[i]:i+=1;continue
    start=i;i+=1
    while i<len(rom) and i-start<65535 and (i>=len(source) or source[i]!=rom[i]):i+=1
    ips+=start.to_bytes(3,'big')+(i-start).to_bytes(2,'big')+rom[start:i]
ips+=b'EOF';applied=bytearray(source);pos=5
while ips[pos:pos+3]!=b'EOF':
    off=int.from_bytes(ips[pos:pos+3],'big');n=int.from_bytes(ips[pos+3:pos+5],'big');pos+=5
    if len(applied)<off+n:applied.extend(bytes(off+n-len(applied)))
    applied[off:off+n]=ips[pos:pos+n];pos+=n
assert applied==rom
(OUT/'gun_nac_ko_credits.ips').write_bytes(ips)
m=dict(scope='Opening, ending, settings and scrolling credits; original logos preserved',source_sha256=sha(source),base_settings_sha256=sha(base),target_sha256=sha(rom),source_csv_sha256=sha(csv_bytes),font_sha256=preview['font_sha256'],mapper=4,prg_size=262144,chr_size=262144,data_bank=18,data_bytes=len(data),font_banks=[0x8c,0x8e],font_tiles=len(patterns),injection_cpu=a.labels,injection_bytes=len(code),hooks=hooks,ips_roundtrip=True,end_pointer=hex(end_ptr),events=events)
m['font_policy']=POLICY
(OUT/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2));(OUT/'credits.chr').write_bytes(font);(OUT/'glyphs.json').write_text(json.dumps(glyphs,ensure_ascii=False,indent=2));(OUT/'injection.bin').write_bytes(code)
print(json.dumps({k:v for k,v in m.items() if k!='events'},ensure_ascii=False,indent=2))
