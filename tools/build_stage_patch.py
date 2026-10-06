#!/usr/bin/env python3
"""Final approved graphic item: DOSMyungjo stage names on the caption build."""
from pathlib import Path
import csv,json,hashlib,struct,shutil
from font_bitmap import font,glyph
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'build/stage_patch';OUT.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
source=next((ROOT/'jp').glob('*.nes')).read_bytes();base=(ROOT/'build/caption_patch/Gun Nac (Korean captions prototype).nes').read_bytes()
bm=json.loads((ROOT/'build/caption_patch/manifest.json').read_text());assert sha(base)==bm['target_sha256'];assert sha(source)==bm['source_sha256']
workbook=ROOT/'translation/graphics.csv';rows=list(csv.DictReader(workbook.open(encoding='utf-8-sig')));stages=[r for r in rows if r['id'].startswith('stage_')];assert len(stages)==8
assert sha(workbook.read_bytes())==bm['graphics_csv_sha256']
assert sha((ROOT/'translation/text.csv').read_bytes())==bm['source_csv_sha256']
fpath=ROOT/'assets/fonts/dos/DOSMyungjo-16.bdf';f=font(fpath);rom=bytearray(base)
patterns={};letters={};masks={}
for c in sorted(set(''.join(r['ko_translation'] for r in stages))-{' ','／'}):
 rows16=glyph(f,c,14,16);assert not any(r&0x8000 for r in rows16)
 fg={(x-1,y) for y,r in enumerate(rows16) for x in range(16) if r&(0x8000>>x)};shadow={(x+1,y+1) for x,y in fg}-fg
 assert fg and all(0<=x<16 and 0<=y<16 for x,y in fg|shadow)
 masks[c]=[[3 if (x,y) in fg else 1 if (x,y) in shadow else 0 for x in range(16)] for y in range(16)]
 ids=[]
 for half in range(2):
  b=bytes(sum(0x80>>x for x in range(8) if masks[c][ty*8+y][half*8+x]&(1<<plane)) for ty in range(2) for plane in range(2) for y in range(8))
  if b not in patterns:patterns[b]=0x10+len(patterns)*2
  ids.append(patterns[b])
 letters[c]=ids
assert len(patterns)<=24, "Stage font exceeds 48 available 8x8 tiles"
# R4 or R5 maps this same 1KiB original bank, depending on the stage.
chrstart=0x40010+0x1c*1024
for b,tile in patterns.items():rom[chrstart+tile*16:chrstart+tile*16+32]=b
assert rom[chrstart:chrstart+0x100]==base[chrstart:chrstart+0x100] # AREA / CLEAR
assert rom[chrstart+0x400:chrstart+0x1000]==base[chrstart+0x400:chrstart+0x1000]
DATA=0xf400;data=bytearray(18);pages=[]
for i,r in enumerate(stages,1):
 ptr=DATA+len(data);data[i*2:i*2+2]=struct.pack('<H',ptr);entries=[];lines=[]
 for n,text in enumerate(r['ko_translation'].split('／')):
  width=sum(8 if c==' ' else 16 for c in text);x=(256-width)//2;y=104+n*24;lines.append(dict(text=text,x=x,y=y,width=width))
  for c in text:
   if c==' ':x+=8;continue
   for tile in letters[c]:
    data.extend([x,y-1,tile]);entries.append(dict(x=x,y=y,tile=tile));x+=8
 data.append(0);assert max(sum(e['y']==y for e in entries) for y in {e['y'] for e in entries})<=8
 pages.append(dict(id=r['id'],text=r['ko_translation'],lines=lines,sprites=entries))
# Stage 0 has no normal intro; retain its legacy code path below.
class Asm:
 def __init__(self,base):self.base=base;self.code=bytearray();self.labels={};self.fix=[]
 def emit(self,*b):self.code.extend(b)
 def abs(self,op,a):self.emit(op,a&255,a>>8)
 def label(self,n):self.labels[n]=self.base+len(self.code)
 def branch(self,op,n):self.emit(op,0);self.fix.append((len(self.code)-1,n))
 def finish(self):
  for off,n in self.fix:
   delta=self.labels[n]-(self.base+off+1);assert -128<=delta<128;self.code[off]=delta&255
  return self.code
a=Asm(0xf340);a.label('render');a.abs(0xac,0x0180);a.branch(0xf0,'legacy');a.emit(0xc0,9);a.branch(0xb0,'legacy')
a.abs(0xbe,0xd7b9);a.emit(0x86,0x06,0x98,0x0a,0xa8);a.abs(0xb9,DATA);a.emit(0x85,0x04);a.abs(0xb9,DATA+1);a.emit(0x85,0x05,0xa9,0,0x85,0x57,0xa0,0)
a.label('loop');a.emit(0xb1,0x04);a.branch(0xf0,'done');a.emit(0x85,0x56,0xc8,0xb1,0x04,0x85,0x55,0xc8,0xb1,0x04,0x18,0x65,0x06,0x85,0x58,0xc8,0x98,0x48);a.abs(0x20,0xccff);a.emit(0x68,0xa8);a.branch(0xd0,'loop')
a.label('done');a.abs(0x4c,0xd7a5)
a.label('legacy');a.abs(0x4c,0xd775)
a.label('intro_priority');a.abs(0xad,0x0188);a.branch(0xf0,'normal_priority');a.emit(0xc9,0x7e);a.branch(0xb0,'normal_priority');a.emit(0xa5,0x54,0x29,0xbf,0x85,0x54)
a.label('normal_priority');a.abs(0x4c,0xcb18)
code=a.finish();assert a.base+len(code)<=DATA and DATA+len(data)<=0xf700
# Expanded ROM's fixed last 16KiB, not its retained old-bank copy.
offset=lambda cpu:0x3c010+cpu-0xc000
for cpu,b in [(a.base,code),(DATA,data)]:
 off=offset(cpu);assert base[off:off+len(b)]==b'\xff'*len(b);rom[off:off+len(b)]=b
hook=offset(0xd772);assert base[hook:hook+3]==bytes.fromhex('ac 80 01');rom[hook:hook+3]=b'\x4c'+struct.pack('<H',a.base)
priority_hook=offset(0xe256);assert base[priority_hook:priority_hook+3]==bytes.fromhex('20 18 cb');rom[priority_hook:priority_hook+3]=b'\x20'+struct.pack('<H',a.labels['intro_priority'])
target=OUT/'Gun Nac (Korean).nes';target.write_bytes(rom);(OUT/'stage_font.chr').write_bytes(rom[chrstart:chrstart+1024]);(OUT/'injection.bin').write_bytes(code)
ips=bytearray(b'PATCH');i=0
while i<len(rom):
 if i<len(source) and rom[i]==source[i]:i+=1;continue
 start=i;i+=1
 while i<len(rom) and i-start<65535 and (i>=len(source) or rom[i]!=source[i]):i+=1
 ips+=start.to_bytes(3,'big')+(i-start).to_bytes(2,'big')+rom[start:i]
ips+=b'EOF';(OUT/'gun_nac_ko.ips').write_bytes(ips)
applied=bytearray(source);p=5
while ips[p:p+3]!=b'EOF':
 off=int.from_bytes(ips[p:p+3],'big');n=int.from_bytes(ips[p+3:p+5],'big');p+=5
 if len(applied)<off+n:applied.extend(bytes(off+n-len(applied)))
 applied[off:off+n]=ips[p:p+n];p+=n
assert applied==rom
m=dict(scope='All approved localization items integrated; DOSMyungjo stage names added',source_sha256=sha(source),base_sha256=sha(base),target_sha256=sha(rom),source_csv_sha256=bm['source_csv_sha256'],graphics_csv_sha256=sha(workbook.read_bytes()),font_sha256=sha(fpath.read_bytes()),font='DOSMyungjo 16px native BDF, baseline 14, x shift -1, shadow (+1,+1)',font_tiles_8x8=len(patterns)*2,unique_characters=len(letters),glyphs=letters,masks=masks,pages=pages,chr_file=hex(chrstart),hook_cpu='0xd772',priority_hook_cpu='0xe256',priority_scope='Only active stage intro ($0188=1..125); forward OAM allocation keeps names ahead of star sprites',code_cpu=hex(a.base),code_bytes=len(code),data_cpu=hex(DATA),data_bytes=len(data),mapper=4,prg_size=262144,chr_size=262144,ips_roundtrip=True,graphics_items_implemented=[r['id'] for r in rows if r['id'].startswith(('stage_','ending_','opening_'))],graphics_items_retained=[r['id'] for r in rows if '원본유지' in r['notes'] or r['id']=='logos'])
assert len(m['graphics_items_implemented'])==13 and len(m['graphics_items_retained'])==17
(OUT/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
for src,dst in [('LICENSE.txt','DOS_FONT_LICENSE.txt'),('README.md','DOS_FONT_README.md'),('provenance.json','DOS_FONT_PROVENANCE.json')]:
 if (fpath.parent/src).exists():shutil.copyfile(fpath.parent/src,OUT/dst)
print(json.dumps({k:v for k,v in m.items() if k not in ('masks','pages','glyphs')},ensure_ascii=False,indent=2))
