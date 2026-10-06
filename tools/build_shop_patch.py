#!/usr/bin/env python3
"""Add approved Korean shop strings and dynamic values to the B2 credits build."""
from pathlib import Path
import csv,hashlib,io,json,re,struct
from font_policy import POLICY
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'build/shop_patch';OUT.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
source=next((ROOT/'jp').glob('*.nes')).read_bytes();base=(ROOT/'build/credits_patch/Gun Nac (Korean credits prototype).nes').read_bytes()
bm=json.loads((ROOT/'build/credits_patch/manifest.json').read_text());assert sha(base)==bm['target_sha256'] and bm['font_policy']==POLICY
assert sha(source)==bm['source_sha256']
csvbytes=(ROOT/'translation/text.csv').read_bytes();assert sha(csvbytes)==bm['source_csv_sha256']
preview=json.loads((ROOT/'build/font_preview/manifest.json').read_text())
assert preview['font_policy']==POLICY and preview['source_csv_sha256']==sha(csvbytes)
assert preview['font_sha256']==sha((ROOT/'assets/fonts/Galmuri11-Condensed.bdf').read_bytes())
rows=[r for r in csv.DictReader(io.StringIO(csvbytes.decode('utf-8-sig'))) if r['group']=='shop']
texts={int(r['jp_text_offset'],16):r['ko_translation'] for r in rows}
records=[r for r in json.loads((ROOT/'analysis/jp_text.json').read_text()) if r['group']=='shop']
t=lambda off:texts[off]
# Align quantity digits and the currency suffix in fixed 8-pixel cells.
menu_items=[]
for off in (0x20e4,0x20fd,0x2118):
 match=re.fullmatch(r'(.*?)\s+(\d+)(개|회)\s+(\d+)엔',t(off))
 assert match,hex(off)
 menu_items.append(match.groups())
label_width=max(len(label) for label,quantity,unit,price in menu_items)+2
price_width=max(len(price) for label,quantity,unit,price in menu_items)
menu_lines=[f'{label:<{label_width}}{quantity}{unit} {price:>{price_width}}엔'
            for label,quantity,unit,price in menu_items]+[t(0x2132)]
# Positions are tile coordinates; approved wording is kept in the CSV.
layout={
 0x1fb1:[(2,15,t(0x1fb3))],0x1fc4:[(2,20,t(0x1fc6))],0x1fdf:[(2,27,t(0x1fe1))],
 0x1ff7:[(2,18,t(0x1ff9)),(2,20,t(0x2005)),(2,22,t(0x2024))],
 0x2038:[(2,20,t(0x203a)),(2,22,t(0x205a))],
 0x2072:[(2,20,t(0x2074)),(2,22,t(0x2092))],
 0x20a1:[(2,18,t(0x20a3)),(2,20,t(0x20b2)+' '+t(0x20ba)+' '+t(0x20bf)),(2,22,t(0x20c7))],
 0x20d6:[(2,18,t(0x20d8))]+[(7,20+i*2,s) for i,s in enumerate(menu_lines)],
 0x2138:[(2,20,t(0x213a))],
 0x214f:[(2,18,t(0x2151)),(2,20,t(0x216e)),(9,24,t(0x217b)),(2,27,t(0x218e))],
 0x21a0:[(2,20,t(0x21a2))],0x21c3:[(2,20,t(0x21c5))],0x21e0:[(2,20,t(0x21e2))],
 0x21f7:[(2,18,t(0x21f9))],0x2211:[(2,20,t(0x2213)),(2,27,t(0x2225))],0x2238:[(2,20,t(0x223a))],
 0x2256:[(2,18,t(0x2258)),(2,20,t(0x226c)),(9,24,t(0x2273)),(2,27,t(0x2285))],
 0x2297:[(2,18,t(0x2299)),(2,20,t(0x22b8)),(9,24,t(0x22bf)),(2,27,t(0x22c9))],
 0x22da:[(6,20,t(0x22dc).replace(' 보내져 있어요.','')),(6,22,'보내져 있어요.')],
 0x22ec:[(6,20,t(0x22ee))],0x2302:[(2,20,t(0x2304))],
 0x2325:[(2,18,t(0x2327)),(2,20,t(0x2342)),(2,22,t(0x235f))],
}
for off,lines in layout.items():
 approved=''.join(r['ko_translation'] for r in rows if int(r['jp_record_offset'],16)==off and r['review_status']!='배치용 공백')
 assert re.sub(r'\s+','',''.join(s for x,y,s in lines))==re.sub(r'\s+','',approved),hex(off)
# Explicit dynamic sources. The original gameplay routines still own these RAM values.
fields={'소지금':(0,3),'무기번호':(1,1),'무기레벨':(2,1),'연사단계':(3,1),'폭탄종류':(4,1),'폭탄수량':(5,2),'배송수량':(7,2)}
idx=json.loads((ROOT/'build/font_preview/glyph_index.json').read_text());raw=(ROOT/'build/font_preview/glyphs_8x16.1bpp').read_bytes()
allmasks={c:raw[i*16:i*16+16] for i,c in enumerate(idx['characters'])}
chars=set(' 0123456789FBTW')
for rr in layout.values():
 for x,y,s in rr:chars.update(re.sub(r'\{[^}]+\}','',s))
patterns=[bytes(16)];glyphs={}
for c in sorted(chars):
 m=allmasks[c];pair=[]
 for h in (0,1):
  p=m[h*8:h*8+8]*2
  if p not in patterns:patterns.append(p)
  pair.append(patterns.index(p))
 glyphs[c]=pair
assert len(patterns)<=255,len(patterns)
font=b''.join(patterns).ljust(4096,b'\0')
# Metadata arrays: original pointer lo/hi, stream pointer lo/hi, original end lo/hi.
N=len(records);data=bytearray(0x100);pages=[];fix=[]
def command(addr,tiles):
 data.extend(struct.pack('<HB',addr,len(tiles)));data.extend(tiles)
def dynamic(addr,field,table):
 data.extend(struct.pack('<HBB',addr,0x80,field));fix.append((len(data),table));data.extend(b'\0\0')
def cells(s,record):
 out=[]
 for token in re.split(r'(\{[^}]+\})',s):
  if token.startswith('{'):
   name=token[1:-1];fid,width=fields[name]
   if record==0x22da and name=='폭탄종류':fid=6
   for col in range(width):out.append((fid,width,col))
  else:out.extend(token)
 return out
for i,r in enumerate(records):
 off=int(r['start'],16);end=int(r['end_exclusive'],16);cpu=off+0x7ff0;ptr=0x8000+len(data)
 for j,value in enumerate([cpu&255,cpu>>8,ptr&255,ptr>>8,(end+0x7ff0)&255,(end+0x7ff0)>>8]):data[j*N+i]=value
 rendered=[];occupied=set()
 if off in (0x22da,0x22ec):
  for yy in (20,21,22,23):command(0x2000+yy*32+6,[0]*24)
 for x,y,s in layout[off]:
  cc=cells(s,off);width=30-x;lines=[]
  while len(cc)>width:
   cut=max([i for i,c in enumerate(cc[:width+1]) if c==' '] or [width])
   lines.append(cc[:cut]);cc=cc[cut:]
   if cc and cc[0]==' ':cc=cc[1:]
  lines.append(cc)
  for line_index,line in enumerate(lines):
   yy=y+line_index*2;assert yy+1<=28,(hex(off),yy)
   for h in (0,1):
    j=0
    while j<len(line):
     addr=0x2000+(yy+h)*32+x+j
     if isinstance(line[j],tuple):
      fid,w,c=line[j];table=('type' if fid==4 else 'shiptype' if fid==6 else f'num{w}_{c}')+f'_{h}'
      dynamic(addr,fid,table);j+=1
     else:
      stop=j+1
      while stop<len(line) and isinstance(line[stop],str):stop+=1
      command(addr,[glyphs[c][h] for c in line[j:stop]]);j=stop
    for col in range(len(line)):
     key=(x+col,yy+h);assert key not in occupied,(hex(off),key);occupied.add(key)
   rendered.append(dict(x=x,y=yy,cells=line))
 data.extend(b'\0\0\0');pages.append(dict(record=hex(off),pointer=hex(ptr),lines=rendered))
# Table lookup avoids extra decimal arithmetic and preserves the original 0..255 range.
tables={}
for name in sorted({name for _,name in fix}):
 tables[name]=0x8000+len(data);h=int(name[-1])
 for value in range(256):
  if name.startswith('shiptype'):c='FBTW'[value&3]
  elif name.startswith('type'):c=chr(value) if chr(value) in 'FBTW' else ' '
  else:
   w,col=map(int,re.match(r'num(\d)_(\d)_',name).groups());c=str(value).rjust(w)[-w:][col]
  data.append(glyphs[c][h])
for off,name in fix:data[off:off+2]=struct.pack('<H',tables[name])
assert len(data)<=8192,len(data)
class Asm:
 def __init__(self,base):self.base=base;self.code=bytearray();self.labels={};self.fix=[]
 def label(self,n):self.labels[n]=self.base+len(self.code)
 def emit(self,*bs):self.code.extend(bs)
 def abs(self,op,a):self.emit(op,a&255,a>>8)
 def ref(self,op,n):self.emit(op,0,0);self.fix.append((len(self.code)-2,n,False))
 def branch(self,op,n):self.emit(op,0);self.fix.append((len(self.code)-1,n,True))
 def finish(self):
  for off,n,rel in self.fix:
   v=self.labels[n]
   if rel:
    d=v-(self.base+off+1);assert -128<=d<128,(n,d);self.code[off]=d&255
   else:self.code[off:off+2]=struct.pack('<H',v)
  return self.code
a=Asm(0xab90);assert 0xab20+bm['injection_bytes']<=a.base
a.label('dispatch');a.emit(0xa5,0x00,0x48,0xa9,0x13);a.abs(0x20,0xe629);a.emit(0xa2,0x00)
a.label('search');a.abs(0xbd,0x8000);a.emit(0xc5,0x12);a.branch(0xd0,'next');a.abs(0xbd,0x8000+N);a.emit(0xc5,0x13);a.branch(0xf0,'found')
a.label('next');a.emit(0xe8,0xe0,N);a.branch(0x90,'search')
# Fail-safe for an unexpected pointer: restore the bank and use the original path.
a.emit(0x68);a.abs(0x20,0xe629);a.abs(0x4c,0xe6e3)
a.label('found');a.abs(0xbd,0x8000+N*5);a.emit(0x48);a.abs(0xbd,0x8000+N*4);a.emit(0x48)
a.abs(0xbd,0x8000+N*2);a.emit(0x85,0x12);a.abs(0xbd,0x8000+N*3);a.emit(0x85,0x13)
a.label('row');a.emit(0xa0,0x00,0xb1,0x12,0x85,0x14,0xc8,0xb1,0x12,0x85,0x15,0xc8,0xb1,0x12)
a.branch(0xf0,'done');a.emit(0x85,0x11,0xa9,0x03);a.ref(0x20,'advance');a.emit(0xa5,0x11);a.branch(0x30,'dynamic')
a.abs(0x20,0xe875);a.emit(0xa5,0x11);a.ref(0x20,'advance');a.ref(0x4c,'row')
a.label('dynamic');a.emit(0xa0,0x00,0xb1,0x12);a.ref(0x20,'value');a.emit(0xaa,0xa5,0x12,0x48,0xa5,0x13,0x48,0xa0,0x01,0xb1,0x12,0x85,0x04,0xc8,0xb1,0x12,0x85,0x13,0xa5,0x04,0x85,0x12,0x8a,0xa8,0xb1,0x12,0xaa,0x68,0x85,0x13,0x68,0x85,0x12,0x8a)
a.abs(0x20,0xe959);a.emit(0xa9,0x03);a.ref(0x20,'advance');a.ref(0x4c,'row')
a.label('done');a.abs(0x20,0xe7d6);a.emit(0x68,0x85,0x12,0x68,0x85,0x13,0x68);a.abs(0x20,0xe629);a.emit(0xa0,0x00,0x60)
a.label('advance');a.emit(0x18,0x65,0x12,0x85,0x12);a.branch(0x90,'advanced');a.emit(0xe6,0x13);a.label('advanced');a.emit(0x60)
a.label('value')
for i,name in enumerate(['money','weapon','level','rate','delivery_type','delivery_count','ship_type']):
 a.emit(0xc9,i);a.branch(0xf0,'value_'+name)
a.abs(0xac,0x0403);a.abs(0xb9,0x0178);a.emit(0x29,0x3f,0x60)
a.label('value_money');a.abs(0xad,0x018e);a.emit(0x60)
a.label('value_weapon');a.emit(0xa5,0x34,0x18,0x69,0x01,0x60)
a.label('value_level');a.emit(0xa5,0x33,0xc9,0x08);a.branch(0x90,'level_ok');a.emit(0xa9,0x07);a.label('level_ok');a.emit(0x18,0x69,0x01,0x60)
a.label('value_rate');a.emit(0xa5,0x3c,0x18,0x69,0x01,0x60)
a.label('value_delivery_type');a.abs(0xad,0x0405);a.emit(0x60)
a.label('value_delivery_count');a.abs(0xad,0x0404);a.emit(0x60)
a.label('value_ship_type');a.abs(0xac,0x0403);a.abs(0xb9,0x0178);a.emit(*([0x4a]*6),0x60)
for name,ptr in [('money_update',0x9fa1),('weapon_update',0xa13f),('rate_update',0xa1e7)]:
 a.label(name);a.emit(0xa9,ptr&255,0x85,0x12,0xa9,ptr>>8,0x85,0x13);a.ref(0x4c,'dispatch')
a.label('shipment_update');a.abs(0xac,0x0403);a.abs(0xb9,0x0178);a.emit(0x29,0x3f);a.branch(0xf0,'shipment_empty');a.emit(0xa0,0xca);a.ref(0x4c,'shipment_pointer');a.label('shipment_empty');a.emit(0xa0,0xdc)
a.label('shipment_pointer');a.emit(0x84,0x12,0xa9,0xa2,0x85,0x13);a.ref(0x4c,'dispatch')
a.label('stash_count');a.abs(0x8d,0x0404);a.emit(0x60)
a.label('stash_type');a.abs(0x8d,0x0405);a.emit(0x60)
code=a.finish();assert a.base+len(code)<=0xaeb1,(len(code),hex(a.base+len(code)))
rom=bytearray(base);rom[0x26010:0x26010+len(data)]=data;rom[0x64010:0x65010]=font
rom[a.base-0x8000+16:a.base-0x8000+16+len(code)]=code
hooks=[]
def patch(cpu,before,after):
 off=cpu-0x8000+16;assert base[off:off+len(before)]==before,(hex(cpu),base[off:off+len(before)].hex());assert len(before)==len(after)
 rom[off:off+len(after)]=after;hooks.append(dict(cpu=hex(cpu),before=before.hex(),after=after.hex()))
# Only shop call sites; never globally redirect a shared text or number routine.
for cpu in [0x9b6c,0x9bde,0x9d06,0x9d28,0x9da5,0x9df8,0x9ec8,0x9f06,0x9f17,0x9f3c]:
 off=cpu-0x8000+16;before=base[off:off+3];assert before in (bytes.fromhex('20 d1 e6'),bytes.fromhex('20 e3 e6'))
 patch(cpu,before,b'\x20'+struct.pack('<H',a.labels['dispatch']))
for cpu,name in [(0x9c96,'weapon_update'),(0x9d6b,'rate_update'),(0x9f09,'money_update'),(0x9e5b,'shipment_update')]:
 off=cpu-0x8000+16;patch(cpu,base[off:off+3],b'\x4c'+struct.pack('<H',a.labels[name]))
for cpu,before,name in [(0x9b32,'20 7d e9','stash_count'),(0x9b3e,'20 59 e9','stash_type')]:patch(cpu,bytes.fromhex(before),b'\x20'+struct.pack('<H',a.labels[name]))
patch(0x9f92,b'\x7c',b'\x90');patch(0x9f9c,b'\x7e',b'\x92')
patch(0x9ef2,b'\x40',b'\x80') # Clear through row 28; money occupies rows 15/16.
patch(0x9bab,b'\x9f',b'\xa4');patch(0x9cfa,b'\xb7',b'\xcf')
# Shipment refreshes must erase both status rows before shorter text is rendered.
# Both templates include the same cleared rectangle before their own text.
rompath=OUT/'Gun Nac (Korean shop prototype).nes';rompath.write_bytes(rom)
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
(OUT/'gun_nac_ko_shop.ips').write_bytes(ips)
m=dict(scope='Shop, credits, settings, opening and ending; B2 font',source_sha256=sha(source),base_credits_sha256=sha(base),target_sha256=sha(rom),source_csv_sha256=sha(csvbytes),font_sha256=bm['font_sha256'],font_policy=POLICY,mapper=4,prg_size=262144,chr_size=262144,data_bank=19,data_bytes=len(data),font_banks=[0x90,0x92],font_tiles=len(patterns),injection_cpu=a.labels,injection_bytes=len(code),hooks=hooks,ips_roundtrip=True,pages=pages)
(OUT/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2));(OUT/'shop.chr').write_bytes(font);(OUT/'glyphs.json').write_text(json.dumps(glyphs,ensure_ascii=False,indent=2));(OUT/'injection.bin').write_bytes(code)
print(json.dumps({k:v for k,v in m.items() if k not in ('pages','hooks')},ensure_ascii=False,indent=2))
