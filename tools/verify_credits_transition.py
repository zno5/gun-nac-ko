#!/usr/bin/env python3
"""Check residual ending text against an ending-font-only control ROM."""
from pathlib import Path
import json,hashlib,argparse
from run_mesen import Runner, core_path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--rom',type=Path,default=ROOT/'build/stage_patch/Gun Nac (Korean).nes');p.add_argument('--out',type=Path,default=ROOT/'build/runtime/credits_transition_regression');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
base=bytearray(a.rom.read_bytes());assert base[0xe61:0xe68]==bytes.fromhex('a9 01 20 45 ed a9 91');base[0xe61:0xe68]=bytes.fromhex('a9 01 85 4c 4c 72 95')
streams={};captures={}
for mode in ['fixed','ending_font_control']:
 data=bytearray(base)
 if mode=='ending_font_control':data[0x29d4:0x29d9]=bytes.fromhex('a9 84 4c d1 a9') # CPU $A9C4
 path=a.out/f'{mode}_TEST_ONLY.nes';path.write_bytes(data)
 r=Runner(core_path(),a.out/mode);r.load(path);trace=[]
 for frame in range(1,5521):
  r.run();ram=r.ram();ptr=ram[0x2f]|ram[0x30]<<8
  if frame>=5100:
   raw,w,h,pitch=r.video;trace.append(dict(frame=frame,ptr=ptr,sha256=hashlib.sha256(raw).hexdigest()))
  if frame in [5100,5190,5220,5280,5340,5390,5460,5520]:r.capture(a.out/f'{mode}_{frame}.png')
 r.close();streams[mode]=trace
control={t['frame']:t for t in streams['ending_font_control']};checked=[]
for t in streams['fixed']:
 if t['ptr']>=0xa800 or 0x8000<=t['ptr']<=0x8003:
  assert t['sha256']==control[t['frame']]['sha256'],('Residual ending text differs',t['frame']);checked.append(t['frame'])
assert len(checked)>250
# The font must actually switch: a forced ending font misrenders the first credit.
assert streams['fixed'][-1]['sha256']!=streams['ending_font_control'][-1]['sha256']
result=dict(rom_sha256=hashlib.sha256(a.rom.read_bytes()).hexdigest(),ending_text_frames_equal_to_control=len(checked),first_frame=min(checked),last_frame=max(checked),credits_font_switch_confirmed=True,fixture='Test-only boot redirect; control holds ending font after story')
(a.out/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
