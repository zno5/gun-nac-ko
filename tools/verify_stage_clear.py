#!/usr/bin/env python3
"""Shared AREA/CLEAR tiles regression with an explicit RAM display-state fixture."""
from pathlib import Path
import json
from run_mesen import Runner, core_path
from font_bitmap import readpng
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'build/runtime/stage_clear';out.mkdir(parents=True,exist_ok=True)
for label,rom in [('before',ROOT/'build/caption_patch/Gun Nac (Korean captions prototype).nes'),('after',ROOT/'build/stage_patch/Gun Nac (Korean).nes')]:
 for area in (1,7,8):
  r=Runner(core_path(),out/f'{label}_{area}');r.load(rom);injected=False
  def frames(n,buttons=()):
   r.buttons=set(buttons)
   for _ in range(n):r.run()
  def press(b):frames(2,[b]);frames(78)
  for f in range(900):
   r.buttons={3} if f in (360,361,720,721) else set();r.run();ram=r.ram()
   if f>720 and not injected and ram[0]==0 and ram[1]==1 and ram[0x26]&16:ram[0x26]&=239;ram[0x180]=area;injected=True
  assert injected
  for _ in range(3):press(5)
  press(8)
  if area==8:press(8)
  for _ in range(12):ram[0x188]=0x7e;frames(1)
  r.capture(out/f'{label}_{area}.png');r.close();print(label,area,flush=True)
checks=[]
for area in (1,7,8):
 a=readpng(out/f'before_{area}.png');b=readpng(out/f'after_{area}.png')
 for y in range(96,145):
  lo=(y*256+96)*3;hi=(y*256+162)*3;assert a[lo:hi]==b[lo:hi],(area,y)
 checks.append(dict(area=area,area_clear_pixels_unchanged=True))
(out/'verification.json').write_text(json.dumps(dict(fixture='Set RAM $0188=0x7e to invoke original AREA/CLEAR renderer, not a boss-clear playthrough',checks=checks),indent=2));print('AREA/CLEAR regions match baseline.')
