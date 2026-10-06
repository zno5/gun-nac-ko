#!/usr/bin/env python3
"""Build a JP-based MMC3 Korean story proof: 256 KiB PRG + 256 KiB CHR.
Only opening/ending text and their font IRQ path are changed. No game cheats.
"""
from pathlib import Path
import json,hashlib,struct,zlib
from font_policy import POLICY
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'build/story_patch';OUT.mkdir(parents=True,exist_ok=True)
source=next((ROOT/'jp').glob('*.nes')).read_bytes()
assert hashlib.sha256(source).hexdigest()=='08ead6a2a83a7c476ac76a067a04055a6f68fe5b50248ea873d00305111da44d'
preview=json.loads((ROOT/'build/font_preview/manifest.json').read_text())
assert preview['font_policy']==POLICY
assert preview['source_csv_sha256']==hashlib.sha256((ROOT/'translation/text.csv').read_bytes()).hexdigest()
for field,path in [('font_sha256','assets/fonts/Galmuri11-Condensed.bdf'),('layout_overrides_sha256','translation/layout_overrides.json'),('display_overrides_sha256','translation/display_overrides.json')]:
 assert preview[field]==hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),f'Stale preview: {path}; rebuild font preview first'
# Fixed banks move to new last two slots; preserve old copies for explicit bank references.
prg=bytearray(source[16:0x20010])+bytearray([255])*0x20000
prg[0x3c000:0x40000]=prg[0x1c000:0x20000]
chrdata=bytearray(source[0x20010:])+bytearray(0x20000)
for i,group in enumerate(['opening','ending']):
 bank=(ROOT/f'build/font_preview/group_{group}.chr').read_bytes();assert bank[0xff0:0x1000]==bytes(16)
 # The original text uses color 3 for ink: set both bitplanes identically.
 bank=b''.join(bank[t:t+8]*2 for t in range(0,4096,16))
 chrdata[0x20000+i*4096:0x21000+i*4096]=bank
stream=bytearray();pointers={};pages=[]
for p in preview['pages']:
 if p['group'] not in ('opening','ending'):continue
 assert p['record'] not in pointers,'Multiple pages need an explicit story state machine'
 table=json.loads((ROOT/f'build/font_preview/group_{p["group"]}_glyphs.json').read_text())
 pointers[p['record']]=0x8000+len(stream);base=0x2000 if p['group']=='opening' else 0x2400
 for row,line in enumerate(p['lines']):
  for half in [0,1]:
   start_row={'0x0029BD':21,'0x002E8E':19}.get(p['record'],17)
   addr=base+(start_row+row*2+half)*32+2
   stream+=struct.pack('<HB',addr,len(line))+bytes(table[c][half] for c in line)
 stream+=b'\0\0\0';p['stream_end']=0x8000+len(stream)-3;pages.append(p)
assert len(stream)<=8192
prg[0x20000:0x20000+len(stream)]=stream
refs=json.loads((ROOT/'config/story_pointers.json').read_text())
for r in refs:
 off=int(r['pointer_file'],16)-16;prg[off:off+2]=struct.pack('<H',pointers[r['text_file']])
# Tiny assembler for this bounded injection. Branches are range checked.
class Asm:
 def __init__(self,base):self.base=base;self.code=bytearray();self.labels={};self.fix=[]
 def label(self,n):self.labels[n]=self.base+len(self.code)
 def emit(self,*bs):self.code.extend(bs)
 def abs(self,op,a):self.emit(op,a&255,a>>8)
 def call(self,n):self.emit(0x20,0,0);self.fix.append((len(self.code)-2,n,False))
 def jump(self,n):self.emit(0x4c,0,0);self.fix.append((len(self.code)-2,n,False))
 def branch(self,op,n):self.emit(op,0);self.fix.append((len(self.code)-1,n,True))
 def finish(self):
  for off,n,rel in self.fix:
   addr=self.labels[n]
   if rel:
    delta=addr-(self.base+off+1);assert -128<=delta<128;(self.code.__setitem__(off,delta&255))
   else:self.code[off:off+2]=struct.pack('<H',addr)
  return self.code
asm=Asm(0xa97d);a=asm
# Existing story opcode 05 already clears text. Preserve cumulative story additions.
a.label('render')
# Select appended data bank in R6. CPU is executing in the unchanged R7 slot.
a.emit(0xa5,0x00,0x48,0xa9,0x10);a.abs(0x20,0xe629)
a.label('row');a.emit(0xa0,0x00,0xb1,0x12,0x85,0x14,0xc8,0xb1,0x12,0x85,0x15,0xc8,0xb1,0x12);a.branch(0xf0,'done')
a.emit(0x85,0x11,0xa9,0x03);a.call('advance');a.abs(0x20,0xe875)
a.emit(0xa5,0x11);a.call('advance');a.jump('row')
a.label('done');a.abs(0x20,0xe7d6);a.emit(0x68);a.abs(0x20,0xe629);a.emit(0x60)
a.label('advance');a.emit(0x18,0x65,0x12,0x85,0x12);a.branch(0x90,'advanced');a.emit(0xe6,0x13);a.label('advanced');a.emit(0x60)
# IRQ callback changes only A and flags, like the replaced original. Stack is balanced.
a.label('font_irq');a.emit(0xa9,0x00);a.abs(0x8d,0x8000)
# Story $2F/$30 points into $A8xx/$A9xx; credits point into $97xx-$9Axx.
a.emit(0xa5,0x30,0xc9,0xa8);a.branch(0xb0,'story_font');a.emit(0xa9,0x7c);a.jump('font_store')
a.label('story_font');a.emit(0xa9,0x80,0x24,0x26);a.branch(0x10,'font_store');a.emit(0xa9,0x84)
a.label('font_store');a.abs(0x8d,0x8001);a.emit(0x48,0xa9,0x01);a.abs(0x8d,0x8000);a.emit(0x68,0x18,0x69,0x02);a.abs(0x8d,0x8001);a.emit(0x60)
code=a.finish();assert len(code)<0x2ec1-0x298d
prg[0x297d:0x297d+len(code)]=code
assert source[0x26cb:0x26ce]==bytes.fromhex('20 d1 e6')
prg[0x26bb:0x26be]=bytes([0x20])+struct.pack('<H',a.labels['render'])
assert source[0x27ff:0x2802]==bytes.fromhex('a9 00 8d')
prg[0x27ef:0x27f2]=bytes([0x4c])+struct.pack('<H',a.labels['font_irq'])
header=bytearray(source[:16]);header[4]=16;header[5]=32
rom=bytes(header+prg+chrdata);dest=OUT/'Gun Nac (Korean story prototype).nes';dest.write_bytes(rom)
# IPS patch: original header/PRG/CHR rearrangement and appended bytes are all represented.
patch=bytearray(b'PATCH');i=0
while i<len(rom):
 if i<len(source) and source[i]==rom[i]:i+=1;continue
 start=i;i+=1
 while i<len(rom) and i-start<65535 and (i>=len(source) or source[i]!=rom[i]):i+=1
 patch+=start.to_bytes(3,'big')+(i-start).to_bytes(2,'big')+rom[start:i]
patch+=b'EOF';(OUT/'gun_nac_ko_story.ips').write_bytes(patch)
# Independently apply IPS to source and ensure exact target reconstruction.
applied=bytearray(source);pos=5
while patch[pos:pos+3]!=b'EOF':
 off=int.from_bytes(patch[pos:pos+3],'big');n=int.from_bytes(patch[pos+3:pos+5],'big');pos+=5
 if len(applied)<off+n:applied.extend(bytes(off+n-len(applied)))
 applied[off:off+n]=patch[pos:pos+n];pos+=n
assert bytes(applied)==rom
manifest={'scope':'Opening and ending story only; shop/settings/credits/embedded graphic text remain Japanese','source_sha256':hashlib.sha256(source).hexdigest(),'target_sha256':hashlib.sha256(rom).hexdigest(),'source_csv_sha256':preview['source_csv_sha256'],'prg_size':len(prg),'chr_size':len(chrdata),'mapper':4,'story_records':len(pages),'new_data_bank':16,'data_bytes':len(stream),'injection_cpu':a.labels,'injection_bytes':len(code),'ips_roundtrip':True,'fixed_banks_preserved':prg[0x3c000:]==source[0x1c010:0x20010],'pages':[{'record':p['record'],'pointer':hex(pointers[p['record']]),'stream_end':hex(p['stream_end']),'start_row':{'0x0029BD':21,'0x002E8E':19}.get(p['record'],17),'group':p['group'],'lines':p['lines']} for p in pages]}
manifest['font_policy']=POLICY
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2));(OUT/'injection.bin').write_bytes(code);print(json.dumps({k:v for k,v in manifest.items() if k!='pages'},ensure_ascii=False,indent=2))
