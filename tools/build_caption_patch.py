#!/usr/bin/env python3
"""JP-based caption patch on the verified shop build; preserve credit scroll timing."""
from pathlib import Path
import csv, hashlib, json, struct
from font_bitmap import font, glyph

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'build/caption_patch';OUT.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
source=next((ROOT/'jp').glob('*.nes')).read_bytes()
base=(ROOT/'build/shop_patch/Gun Nac (Korean shop prototype).nes').read_bytes()
bm=json.loads((ROOT/'build/shop_patch/manifest.json').read_text());assert sha(base)==bm['target_sha256']
rom=bytearray(base);rows={r['id']:r for r in csv.DictReader((ROOT/'translation/graphics.csv').open(encoding='utf-8-sig'))}
bdf=ROOT/'assets/fonts/dos/DOSIyagiBoldface-16.bdf';f=font(bdf)
# The old Japanese credits stream is now unused; the Korean stream lives in PRG bank 18.
DATA=0x97f1;END=source.index(255,DATA-0x7ff0)+0x7ff0+1;data=bytearray()
def alloc(b):
    address=DATA+len(data);data.extend(b);assert DATA+len(data)<=END,(len(data),END-DATA);return address
def packet(fn,args):assert len(args)==6;return struct.pack('<H',fn)+bytes(args)
def raw(ptr,addr,n):return packet(0xe875,[0,n,ptr&255,ptr>>8,addr&255,addr>>8])
attrs=alloc(bytes([255])*8)
palette=bytearray(source[0x1787:0x1787+26]);assert palette[0]==7
palette[11:14]=bytes([0x0c,0x0f,0x30]);palptr=alloc(palette)
hooks=[];scenes=[]
def patch(cpu,before,after):
    off=cpu-0x7ff0;assert bytes(rom[off:off+len(before)])==before,(hex(cpu),rom[off:off+len(before)].hex());assert len(before)==len(after)
    rom[off:off+len(after)]=after;hooks.append(dict(cpu=hex(cpu),before=before.hex(),after=after.hex()))
def caption_tiles(text):
    points=set();width=sum(16 if '\uac00'<=c<='\ud7a3' else 8 for c in text);x=(256-width)//2
    for c in text:
        if c!=' ':
            m=glyph(f,c,14,16);assert not any(r&0x8000 for r in m)
            points.update((x+xx-1,y) for y,row in enumerate(m) for xx in range(16) if row&(1<<(15-xx)))
        x+=16 if '\uac00'<=c<='\ud7a3' else 8
    shadow={(x+1,y+1) for x,y in points}-points;assert all(0<=x<256 and 0<=y<16 for x,y in points|shadow)
    patterns=[]
    for ty in range(2):
        for tx in range(32):
            planes=[bytearray(8),bytearray(8)]
            for y in range(8):
                for x in range(8):
                    p=(tx*8+x,ty*8+y);v=3 if p in points else 1 if p in shadow else 0
                    for bit in range(2):
                        if v&(1<<bit):planes[bit][y]|=0x80>>x
            patterns.append(bytes(planes[0]+planes[1]))
    return patterns,width
def make_scene(ident,banks,mt,metatile_ids,newbank,image_command=None):
    original=b''.join(source[0x20010+b*1024:0x20010+b*1024+2048] for b in banks)
    used={t for i in metatile_ids for t in source[mt-0x7ff0+i*5:mt-0x7ff0+i*5+4]}
    assert original[0xff0:]==bytes(16)
    free=iter(sorted(set(range(255))-used));chrdata=bytearray(original);mapping={bytes(16):255};ids=[]
    patterns,width=caption_tiles(rows[ident]['ko_translation'])
    for pattern in patterns:
        if pattern not in mapping:
            tile=next(free);mapping[pattern]=tile;chrdata[tile*16:tile*16+16]=pattern
        ids.append(mapping[pattern])
    for tile in used:assert chrdata[tile*16:tile*16+16]==original[tile*16:tile*16+16]
    off=0x40010+newbank*1024;assert base[off:off+4096]==bytes(4096);rom[off:off+4096]=chrdata
    ptr=alloc(bytes(ids));commands=(image_command or b'')+raw(ptr,0x2020,32)+raw(ptr+32,0x2040,32)+raw(attrs,0x23c0,8)+bytes(2)
    cmd=alloc(commands)
    scenes.append(dict(id=ident,text=rows[ident]['ko_translation'],width=width,font_bank=newbank,command=hex(cmd),caption_tiles=ids,caption_patterns={str(t):chrdata[t*16:t*16+16].hex() for t in set(ids)},art_tiles_preserved=len(used),font_tiles=len(mapping)-1,picture_shift_y=16 if ident in ('ending_normal','ending_hard','ending_puttsun') else 0))
    return cmd
for idx,ident in enumerate(['ending_robot','ending_normal','ending_hard','ending_puttsun']):
    table=0x1755+idx*8;b1,b0=source[table:table+2];mt,pal,oldcmd=struct.unpack('<HHH',source[table+2:table+8]);command=bytearray(source[oldcmd-0x7ff0:oldcmd-0x7ff0+8]);height,width=command[2:4];image_ids_ptr=int.from_bytes(command[4:6],'little')-0x7ff0;image_ids=source[image_ids_ptr:image_ids_ptr+height*width]
    if idx:command[6:8]=struct.pack('<H',int.from_bytes(command[6:8],'little')+64)
    bank=0x98+idx*4;cmd=make_scene(ident,[b0,b1],mt,image_ids,bank,bytes(command))
    entry=bytes([bank+2,bank])+struct.pack('<HHH',mt,palptr&0x7fff,cmd)
    patch(table+0x7ff0,source[table:table+8],entry)
    if idx==0:
        table4=0x1775;entry4=bytes([bank+2,bank])+struct.pack('<HHH',mt,palptr,cmd);patch(table4+0x7ff0,source[table4:table4+8],entry4)
openingcmd=make_scene('opening_bubble',[0x70,0x72],0xb53d,range(1,36),0xa8)
patch(0xa90d,bytes([0x70,0x72]),bytes([0xa8,0xaa]))
clearcmd=alloc(raw(255,0x2020,32)+raw(255,0x2040,32)+raw(attrs,0x23c0,8)+bytes(2))
rom[DATA-0x7ff0:DATA-0x7ff0+len(data)]=data
# The card clear now covers the caption and shifted picture through y=127.
patch(0x96d6,b'\x40',b'\x00');patch(0x96de,b'\x80',b'\x00');patch(0x96e2,b'\x01',b'\x02')
class Asm:
    def __init__(self,base):self.base=base;self.code=bytearray();self.labels={};self.fix=[]
    def emit(self,*bs):self.code.extend(bs)
    def abs(self,op,a):self.emit(op,a&255,a>>8)
    def label(self,n):self.labels[n]=self.base+len(self.code)
    def branch(self,op,n):self.emit(op,0);self.fix.append((len(self.code)-1,n,True))
    def jump(self,n):self.emit(0x4c,0,0);self.fix.append((len(self.code)-2,n,False))
    def finish(self):
        for off,n,rel in self.fix:
            addr=self.labels[n]
            if rel:
                delta=addr-(self.base+off+1);assert -128<=delta<128;self.code[off]=delta&255
            else:self.code[off:off+2]=struct.pack('<H',addr)
        return self.code
a=Asm(0xacd8);assert 0xab90+bm['injection_bytes']<=a.base
a.label('picture_irq')
# Original scroll position is untouched. Only post-roll tall cards use a later split.
a.abs(0xad,0x0407);a.abs(0x8d,0x0411);a.abs(0xad,0x0406);a.abs(0x8d,0x0410)
a.abs(0xad,0x0400);a.emit(0xc9,0x9c);a.branch(0x90,'normal_irq');a.emit(0xc9,0xa8);a.branch(0xb0,'normal_irq')
# Advancing the lower viewport's source by two tile rows cancels the 16px screen shift.
a.abs(0xad,0x0410);a.emit(0x18,0x69,0x40);a.abs(0x8d,0x0410);a.abs(0xad,0x0411);a.emit(0x69,0x00);a.abs(0x8d,0x0411)
a.emit(0x29,0x03,0xc9,0x03);a.branch(0xd0,'late_irq');a.abs(0xad,0x0410);a.emit(0xc9,0xc0);a.branch(0x90,'late_irq')
a.emit(0x38,0xe9,0xc0);a.abs(0x8d,0x0410);a.abs(0xad,0x0411);a.emit(0x29,0xfc);a.abs(0x8d,0x0411)
a.label('late_irq');a.abs(0xad,0x0408);a.branch(0xd0,'late_nonzero');a.emit(0xa9,0x78)
a.label('late_nonzero');a.emit(0x18,0x69,0x10);a.jump('irq_store')
a.label('normal_irq');a.abs(0xad,0x0408);a.branch(0xd0,'irq_store');a.emit(0xa9,0x78)
a.label('irq_store');a.abs(0x8d,0xc000);a.emit(0x60)
a.label('story_picture_finish');a.abs(0x20,0xed31);a.abs(0xad,0x0400);a.emit(0xc9,0xa8);a.branch(0xf0,'opening_caption');a.emit(0xa9,clearcmd&255,0xa0,clearcmd>>8);a.abs(0x4c,0xebcc)
a.label('opening_caption');a.emit(0xa9,openingcmd&255,0xa0,openingcmd>>8);a.abs(0x4c,0xebcc)
code=a.finish();assert a.base+len(code)<=0xaeb1
rom[a.base-0x7ff0:a.base-0x7ff0+len(code)]=code
patch(0xa790,bytes.fromhex('ad 07 04'),b'\x4c'+struct.pack('<H',a.labels['picture_irq']))
patch(0xa6a2,bytes.fromhex('20 31 ed'),b'\x20'+struct.pack('<H',a.labels['story_picture_finish']))
target=OUT/'Gun Nac (Korean captions prototype).nes';target.write_bytes(rom)
ips=bytearray(b'PATCH');i=0
while i<len(rom):
    if i<len(source) and rom[i]==source[i]:i+=1;continue
    start=i;i+=1
    while i<len(rom) and i-start<65535 and (i>=len(source) or rom[i]!=source[i]):i+=1
    ips+=start.to_bytes(3,'big')+(i-start).to_bytes(2,'big')+rom[start:i]
ips+=b'EOF';(OUT/'gun_nac_ko_captions.ips').write_bytes(ips)
applied=bytearray(source);p=5
while ips[p:p+3]!=b'EOF':
    off=int.from_bytes(ips[p:p+3],'big');n=int.from_bytes(ips[p+3:p+5],'big');p+=5
    if len(applied)<off+n:applied.extend(bytes(off+n-len(applied)))
    applied[off:off+n]=ips[p:p+n];p+=n
assert applied==rom
m=dict(scope='Five DOSIyagi picture captions; three tall ending cards lowered 16px; active credits scroll unchanged',source_sha256=sha(source),base_sha256=sha(base),target_sha256=sha(rom),source_csv_sha256=bm['source_csv_sha256'],graphics_csv_sha256=sha((ROOT/'translation/graphics.csv').read_bytes()),font_sha256=sha(bdf.read_bytes()),font_license='MIT-based hurss/fonts; preserve full license and attribution',mapper=4,prg_size=262144,chr_size=262144,scenes=scenes,hooks=hooks,injection_cpu=a.labels,injection_bytes=len(code),data_cpu=hex(DATA),data_bytes=len(data),reclaimed_credits_end=hex(END),ips_roundtrip=True,opening_shadow='Existing grey palette 3 retained to preserve illustration; ending uses dark cyan',stage_font_implementation='Pending; this patch changes picture captions only')
(OUT/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2));(OUT/'injection.bin').write_bytes(code)
print(json.dumps({k:v for k,v in m.items() if k!='scenes'},ensure_ascii=False,indent=2))
