#!/usr/bin/env python3
"""All eight real stage-intro render paths. Start-stage RAM is a test-only fixture."""
from pathlib import Path
import argparse,json,hashlib
from run_mesen import Runner, core_path
ROOT=Path(__file__).resolve().parents[1]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--rom',type=Path,default=ROOT/'build/stage_patch/Gun Nac (Korean).nes');ap.add_argument('--out',type=Path,default=ROOT/'build/runtime/stage_final');ap.add_argument('--baseline',action='store_true');args=ap.parse_args();out=args.out;out.mkdir(parents=True,exist_ok=True)
 m=json.loads((ROOT/'build/stage_patch/manifest.json').read_text());checks=[]
 for area in range(1,9):
  r=Runner(core_path(),out/f'area_{area}');r.load(args.rom)
  def frames(n,buttons=()):
   r.buttons=set(buttons)
   for _ in range(n):r.run()
  def press(b):frames(2,[b]);frames(78)
  injected=False
  for f in range(900):
   r.buttons={3} if f in (360,361,720,721) else set();r.run();ram=r.ram()
   if f>720 and not injected and ram[0]==0 and ram[1]==1 and ram[0x26]&16:
    ram[0x26]&=239;ram[0x180]=area;injected=True
  assert injected
  for _ in range(3):press(5)
  press(8)
  if area==8:press(8)
  frames(1,[8]);r.capture(out/f'stage_{area}.png');ram=r.ram();oam=[list(ram[i:i+4]) for i in range(0x200,0x300,4)];banks=list(ram[0x1a3:0x1a9])
  record=dict(area=area,frame=r.frame,ram_area=ram[0x180],intro_counter=ram[0x188],banks=banks,oam=oam)
  if not args.baseline:
   page=m['pages'][area-1];expected=[]
   for line in page['lines']:
    x=line['x']
    for c in line['text']:
     if c==' ':x+=8;continue
     expected.extend((x+xx,line['y']+yy,(255,254,255) if v==3 else (0,64,77)) for yy,row in enumerate(m['masks'][c]) for xx,v in enumerate(row) if v)
     x+=16
   def verify_pixels():
    raw,w,h,pitch=r.video;assert r.pixel==1 and (w,h)==(256,240)
    for x,y,color in expected:
     off=y*pitch+x*4
     if tuple(raw[off:off+3][::-1])!=color:
      r.capture(out/f'failure_{area}_{r.frame}.png');(out/f'failure_{area}_{r.frame}.ram').write_bytes(bytes(r.ram()))
     assert tuple(raw[off:off+3][::-1])==color,(area,r.frame,x,y,color,tuple(raw[off:off+3][::-1]))
   verify_pixels();record['caption_ink_shadow_pixels']=len(expected)
   offset=0xc1 if area>=7 else 0
   for e in page['sprites']:assert [e['y']-1,e['tile']+offset,0,e['x']] in oam
   record['max_name_sprites_per_scanline']=max(sum(e['y']==y for e in page['sprites']) for y in {e['y'] for e in page['sprites']})
   phases=0;vanished=False
   for n in range(300):
    previous=ram[0x188];frames(1)
    if previous>1 and ram[0x188]>0:
     verify_pixels();phases+=1
    if not ram[0x188]:vanished=True
   assert vanished
   record['additional_frames_pixel_verified']=phases;record['intro_finished']=True;r.capture(out/f'gameplay_{area}.png')
  (out/f'stage_{area}.json').write_text(json.dumps(record,indent=2));checks.append(record);r.close();print(area,record['intro_counter'],banks,flush=True)
 (out/'run.json').write_text(json.dumps(dict(rom_sha256=hashlib.sha256(args.rom.read_bytes()).hexdigest(),fixture='RAM $0180 start area, shop flag $26; release ROM unmodified',stages=checks),indent=2))
if __name__=='__main__':main()
