#!/usr/bin/env python3
"""Run the real ending into credits, locate every scrolling event pixel-for-pixel."""
from pathlib import Path
import argparse,hashlib,json
from run_mesen import Runner, core_path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'build/credits_patch'
ap=argparse.ArgumentParser();ap.add_argument('--rom',type=Path);ap.add_argument('--out',type=Path);args=ap.parse_args()
OUT=args.out or ROOT/'build/runtime/credits_verify';OUT.mkdir(parents=True,exist_ok=True)
m=json.loads((BASE/'manifest.json').read_text());release=args.rom or BASE/'Gun Nac (Korean credits prototype).nes'
data=bytearray(release.read_bytes());assert data[0xe61:0xe68]==bytes.fromhex('a9 01 20 45 ed a9 91')
data[0xe61:0xe68]=bytes.fromhex('a9 01 85 4c 4c 72 95');rom=OUT/'ending_TEST_ONLY.nes';rom.write_bytes(data)
font=(BASE/'credits.chr').read_bytes();expected={}
for e in m['events']:
 if e['kind']=='blank':continue
 lines=[]
 for half in (0,1):
  for y in range(8):
   # Logos preserve original 2bpp pixels; every nonzero font color is visible.
   lines.append(b''.join(bytes([font[t*16+y]|font[t*16+y+8]]) for t in e['tiles'][half*32:half*32+32]))
 expected[e['index']]=tuple(lines)
r=Runner(core_path(),OUT);r.load(rom)
seen={};phases={i:set() for i in expected};pointer_seen=set();last_audio=0;gaps=0;finished_frame=None;checkpoint_frames=[]
for frame in range(1,11501):
 r.run();ram=r.ram();ptr=ram[0x2f]|(ram[0x30]<<8)
 if frame>2 and last_audio==r.audio_frames:gaps+=1
 last_audio=r.audio_frames
 if 0x8000<=ptr<=int(m['end_pointer'],16):pointer_seen.add(ptr)
 if ptr==int(m['end_pointer'],16) and finished_frame is None:finished_frame=frame
 if frame%4==0 and frame>4800 and (len(seen)<len(expected) or any(len(v)<8 for v in phases.values())):
  raw,w,h,pitch=r.video;assert r.pixel==1
  actual=[]
  for y in range(120,240):
   # Background is black; credits have no animated star layer.
   green=raw[y*pitch+1:y*pitch+1024:4]
   actual.append(bytes(sum((green[x+i]>=128)<<(7-i) for i in range(8)) for x in range(0,256,8)))
  windows={tuple(actual[y:y+16]):120+y for y in range(len(actual)-15)}
  for index,pattern in expected.items():
   if pattern not in windows:continue
   phases[index].add(windows[pattern]%8)
   if index in seen or windows[pattern]>192:continue
   e=m['events'][index];name=f'event_{index:02}.png';r.capture(OUT/name)
   seen[index]=dict(frame=frame,y=windows[pattern],image=name,records=e['records'],pixel_checks=4096)
   print('verified',index,[v['record'] for v in e['records']],frame,flush=True)
 if frame in (5200,6000,7200,8400,9600,10800,11500):
  r.capture(OUT/f'checkpoint_{frame}.png');checkpoint_frames.append(frame)
# Exercise the original post-roll START route twice, including its button-release wait.
for i in range(480):
 r.buttons={3} if i in (0,1,240,241) else set();r.run()
 if i in (119,479):r.capture(OUT/f'post_start_{i+1}.png')
result=dict(release_rom_sha256=hashlib.sha256(release.read_bytes()).hexdigest(),executed_rom_sha256=hashlib.sha256(rom.read_bytes()).hexdigest(),ending_test_redirect=True,core=r.info,frames=r.frame,video_callbacks=r.video_count,audio_frames=r.audio_frames,frames_without_audio_after_startup=gaps,verified=seen,scroll_pixel_phases={i:sorted(v) for i,v in phases.items()},missing=[i for i in expected if i not in seen],finished_frame=finished_frame,end_pointer=m['end_pointer'],stream_pointers_observed=len(pointer_seen),checkpoints=checkpoint_frames)
(OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));r.close();print('Missing:',result['missing']);assert not result['missing'];assert finished_frame
assert all(len(v)==8 for v in phases.values()),phases
