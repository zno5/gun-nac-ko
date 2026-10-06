#!/usr/bin/env python3
"""Verify 19 actual story frames against approved font pixel masks using local Mesen.
Ending uses an explicitly test-only ROM with a cold-boot redirect to real ending.
"""
from pathlib import Path
import json,hashlib,sys,argparse
from run_mesen import Runner, core_path
ROOT=Path(__file__).resolve().parents[1]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['opening','ending']);ap.add_argument('--rom',type=Path);ap.add_argument('--out',type=Path);args=ap.parse_args()
 base=ROOT/'build/story_patch';m=json.loads((base/'manifest.json').read_text());rom=args.rom or base/'Gun Nac (Korean story prototype).nes'
 release_sha=hashlib.sha256(rom.read_bytes()).hexdigest()
 out=args.out or ROOT/'build/runtime'/('verify_'+args.mode);out.mkdir(parents=True,exist_ok=True)
 if args.mode=='ending':
  data=bytearray(rom.read_bytes());assert data[0xe61:0xe68]==bytes.fromhex('a9 01 20 45 ed a9 91');data[0xe61:0xe68]=bytes.fromhex('a9 01 85 4c 4c 72 95');rom=out/'ending_TEST_ONLY.nes';rom.write_bytes(data)
 core=core_path();r=Runner(core,out);r.load(rom)
 pages=[p for p in m['pages'] if p['group']==args.mode];expected={}
 bank=(ROOT/f'build/font_preview/group_{args.mode}.chr').read_bytes();table=json.loads((ROOT/f'build/font_preview/group_{args.mode}_glyphs.json').read_text())
 for p in pages:
  checks=[]
  for row,line in enumerate(p['lines']):
   for col,c in enumerate(line):
    for half,tile in enumerate(table[c]):
     pat=bank[tile*16:tile*16+8]
     for yy,bits in enumerate(pat):
      for xx in range(8):checks.append((16+col*8+xx,(p['start_row']+row*2+half)*8+yy,bool(bits&(0x80>>xx))))
  expected[p['record']]=checks
 seen={};observed=set();last_audio=0;no_audio=0;done_frames=7200 if args.mode=='opening' else 9600
 for frame in range(1,done_frames+1):
  r.run();ram=r.ram();ptr=ram[0x12]|(ram[0x13]<<8)
  if frame>2 and r.audio_frames==last_audio:no_audio+=1
  last_audio=r.audio_frames
  # A completed string leaves $12/$13 at its 000000 terminator.
  for p in pages:
   if p['record'] in seen:continue
   if ptr==int(p['stream_end'],16):observed.add(p['record'])
   elif frame%12:continue
   # First page is written before fade-in; its pointer can be reused before visible.
   if not r.video:continue
   raw,w,h,pitch=r.video
   assert r.pixel==1 and w==256 and h==240,(r.pixel,w,h)
   def white(x,y):
    off=y*pitch+x*4
    return max(raw[off:off+3])>=128
   if all(white(x,y)==ink for x,y,ink in expected[p['record']]):
    path=f'{p["record"]}.png';r.capture(out/path);seen[p['record']]={'frame':frame,'image':path,'pixel_checks':len(expected[p['record']])};print('verified',p['record'],frame,flush=True)
  if frame in (6000,7200,9600):r.capture(out/f'checkpoint_{frame}.png')
 result={'mode':args.mode,'core':r.info,'core_sha256':hashlib.sha256(core.read_bytes()).hexdigest(),'release_rom_sha256':release_sha,'executed_rom_sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'ending_test_redirect':args.mode=='ending','frames':done_frames,'video_callbacks':r.video_count,'audio_frames':r.audio_frames,'frames_without_audio_after_startup':no_audio,'verified':seen,'missing':[p['record'] for p in pages if p['record'] not in seen],'terminators_observed':sorted(observed),'comparison':'Every foreground/background pixel inside each translated line rectangle matches approved BDF; excludes surrounding art.'}
 (out/'verification.json').write_text(json.dumps(result,indent=2));r.close();print('Missing:',result['missing']);assert not result['missing']
if __name__=='__main__':main()
