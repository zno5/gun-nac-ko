#!/usr/bin/env python3
"""Shop integration: real inputs, explicit test-only RAM fixtures, pixel checks.
No RAM fixture is written to the released ROM or patch.
"""
from pathlib import Path
import argparse,hashlib,json
from run_mesen import Runner, core_path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'build/shop_patch'
m=json.loads((BASE/'manifest.json').read_text());pages={int(p['record'],16):p for p in m['pages']}
font=(BASE/'shop.chr').read_bytes();glyphs=json.loads((BASE/'glyphs.json').read_text())
masks={c:b''.join(bytes(font[t*16+y]|font[t*16+y+8] for y in range(8)) for t in pair) for c,pair in glyphs.items()}
WHITE=bytes(49 if i>=200 else 48 for i in range(256))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('language',choices=['jp','ko']);ap.add_argument('scenario',choices=['welcome','purchase','shipping','delivery','blocked','converter']);ap.add_argument('--bomb-type',type=int,default=2);ap.add_argument('--quantity',type=int,default=7);ap.add_argument('--rom',type=Path);ap.add_argument('--out',type=Path);args=ap.parse_args()
 tag=args.scenario+(f'_{args.bomb_type}_{args.quantity}' if args.scenario=='delivery' else '')
 out=args.out or ROOT/'build/runtime'/f'shop_{args.language}_{tag}';out.mkdir(parents=True,exist_ok=True)
 rom=args.rom or (next((ROOT/'jp').glob('*.nes')) if args.language=='jp' else BASE/'Gun Nac (Korean shop prototype).nes')
 executed_sha=hashlib.sha256(rom.read_bytes()).hexdigest()
 r=Runner(core_path(),out);r.load(rom)
 seen={};checks=[];fixtures=[];last_audio=0;gaps=0
 def field(fid,ram):
  ship=ram[0x178+ram[0x403]] if ram[0x403]<8 else 0
  return [ram[0x18e],ram[0x34]+1,min(ram[0x33],7)+1,ram[0x3c]+1,ram[0x405],ram[0x404],ship>>6,ship&63][fid]
 def actual():
  raw,w,h,pitch=r.video;assert r.pixel==1 and (w,h)==(256,240)
  return [int(raw[y*pitch+1:y*pitch+1024:4].translate(WHITE),2) for y in range(240)]
 def matches(off,screen,debug=False):
  ram=r.ram()
  for line in pages[off]['lines']:
   chars=[]
   for c in line['cells']:
    if isinstance(c,str):chars.append(c)
    else:
     fid,width,col=c;v=field(fid,ram)
     if fid==4:
      if chr(v) not in 'FBTW':return False
      chars.append(chr(v))
     elif fid==6:chars.append('FBTW'[v])
     else:chars.append(str(v).rjust(width)[-width:][col])
   shift=256-(line['x']+len(chars))*8;mask=((1<<(len(chars)*8))-1)<<shift
   for y in range(16):
    expected=int.from_bytes(bytes(masks[c][y] for c in chars),'big')<<shift
    if screen[line['y']*8+y]&mask!=expected:
     if debug:print('mismatch',hex(off),'row',line['y']*8+y,'x',255-((screen[line['y']*8+y]&mask)^expected).bit_length()+1,'text',''.join(chars),flush=True)
     return False
  return True
 def step(buttons=()):
  nonlocal last_audio,gaps
  r.buttons=set(buttons);r.run()
  if r.frame>2 and r.audio_frames==last_audio:gaps+=1
  last_audio=r.audio_frames
  if args.language=='ko' and r.frame>720 and len(seen)<len(pages):
   screen=actual()
   for off in pages:
    if off not in seen and matches(off,screen):
     name=f'record_{off:06X}.png';r.capture(out/name);seen[off]=dict(frame=r.frame,image=name)
 def frames(n,buttons=()):
  for _ in range(n):step(buttons)
 def press(button):frames(2,[button]);frames(78)
 def fixture(values,reason):
  ram=r.ram()
  for address,value in values.items():ram[address]=value
  fixtures.append(dict(frame=r.frame,reason=reason,values={hex(k):v for k,v in values.items()}))
 def state(label,expected=(),shot=False):
  ram=r.ram();s={hex(a):ram[a] for a in [0x26,0x32,0x33,0x34,0x3c,0x180,0x18e,0x18f,0x190,0x400,0x401,0x403,*range(0x17a,0x180)]}
  checks.append(dict(label=label,state=s))
  if args.language=='ko':
   screen=actual()
   for off in expected:
    if not matches(off,screen):
     matches(off,screen,True);r.capture(out/('FAIL_'+label+'.png'));raise AssertionError((label,hex(off),r.frame))
  if shot:r.capture(out/(label+'.png'))
  return ram
 def menu(index):
  for _ in range(5):
   if r.ram()[0x400]==index:return
   press(5)
  raise AssertionError('main menu cursor did not move')
 def select(index):
  for _ in range(9):
   if r.ram()[0x401]==index:return
   press(7)
  raise AssertionError(('horizontal cursor did not move',index))
 # Boot and enter via the normal title START. Fixtures wait for the real shop bank.
 injected=False
 for f in range(900):
  step([3] if f in (360,361,720,721) else [])
  ram=r.ram()
  if args.scenario!='welcome' and not injected and f>720 and ram[0]==0 and ram[1]==1 and ram[0x26]&16:
   area=8 if args.scenario=='converter' else 1 if args.scenario=='blocked' else 3
   values={0x26:ram[0x26]&239,0x180:area,0x18e:255 if args.scenario=='shipping' else 200}
   if args.scenario=='delivery':values[0x17a]=(args.bomb_type<<6)|args.quantity
   fixture(values,'Simulate a later shop visit with funds; delivery fixture is already-shipped inventory.');injected=True
 if args.scenario=='welcome':
  state('welcome',[0x1fb1,0x1ff7,0x1fdf],True)
  press(8);state('bomb_strength',[0x2038,0x1fdf],True)
  press(8);state('bomb_limit',[0x2072,0x1fdf],True)
  press(8);frames(300);state('stage_after_welcome',shot=True)
 elif args.scenario=='delivery':
  state('delivery_notice',[0x20a1,0x1fdf],True)
  assert r.ram()[0x17a]==0
  press(8);frames(240);state('delivery_received',[0x20d6],True)
 elif args.scenario=='purchase':
  state('main',[0x1fb1,0x20d6],True);press(8);state('weapon_menu',[0x214f],True)
  start_money=r.ram()[0x18e]
  for i in range(2):press(8);state(f'weapon_upgrade_{i+1}',[0x214f,0x1fb1])
  assert r.ram()[0x18e]==start_money-20
  press(8);state('wing_required',[0x21a0,0x1fdf],True);press(8)
  select(5);press(8);state('wing_bought',[0x214f,0x1fb1],True);assert r.ram()[0x32]&128
  press(8);state('wing_already_owned',[0x21e0,0x1fdf],True);press(8)
  while r.ram()[0x33]<7:
   select(r.ram()[0x34]);press(8);state(f'weapon_level_{r.ram()[0x33]+1}',[0x214f,0x1fb1])
  press(8);state('weapon_max',[0x21c3,0x1fdf],True);press(8);press(0)
  menu(1);press(8);state('rapid_menu',[0x21f7,0x2211],True)
  press(0);state('rapid_cancel',[0x20d6]);menu(1);press(8)
  for i in range(4):
   cash=r.ram()[0x18e];press(8);assert r.ram()[0x18e]==cash-6
   state(f'rapid_level_{i+2}',[0x21f7,0x2238,0x1fdf] if i==3 else [0x21f7,0x2211,0x1fb1],True)
  press(8);menu(0);press(8)
  while r.ram()[0x18e]>=10:
   select(1 if r.ram()[0x34]==0 else 0);cash=r.ram()[0x18e];press(8)
   assert r.ram()[0x18e]==cash-10;state(f'purchase_cash_{r.ram()[0x18e]}',[0x214f,0x1fb1])
  select(1 if r.ram()[0x34]==0 else 0);cash=r.ram()[0x18e];press(8)
  assert r.ram()[0x18e]==cash;state('insufficient_funds',[0x1fc4,0x1fdf],True);press(8)
  state('back_to_main',[0x20d6]);menu(3);press(8);frames(300);state('stage_after_purchase',shot=True)
 elif args.scenario=='shipping':
  state('main',[0x1fb1,0x20d6]);menu(2);press(8);state('area_select',[0x2256,0x22ec],True)
  for i in range(5):press(7);state(f'area_cursor_{i}',[0x2256,0x22ec])
  assert r.ram()[0x401]==3
  select(7);press(8);state('bomb_select',[0x2297,0x22ec],True)
  for qty in range(1,64):
   if qty in (2,3,4):press(7)
   cash=r.ram()[0x18e];press(8);assert r.ram()[0x18e]==cash-4
   assert r.ram()[0x17f]&63==qty
   state(f'shipped_{qty}',[0x2297,0x22da,0x1fb1],qty in (1,2,3,4,9,10,63))
  fixture({0x18e:7},'Only for testing the original quantity cap at 63 with sufficient payment.')
  press(8);assert r.ram()[0x17f]&63==63;assert r.ram()[0x18e]==3
  state('shipping_cap',[0x22da,0x1fb1],True)
  press(0);menu(2);press(8);state('empty_after_nonempty',[0x2256,0x22ec],True)
  select(7);state('shipment_persists',[0x2256,0x22da],True);press(8);press(8)
  state('shipping_insufficient',[0x1fc4,0x1fdf],True);press(8)
  menu(3);press(8);frames(300);state('stage_after_shipping',shot=True)
 else:
  state('main',[0x1fb1,0x20d6]);menu(2);press(8);state('shipping_blocked',[0x2302,0x1fdf],True);press(8)
  menu(3);press(8)
  if args.scenario=='converter':
   state('converter',[0x2325,0x1fdf],True);assert r.ram()[0x32]&32;press(8)
  frames(300);state('stage_after_exit',shot=True)
 result=dict(language=args.language,scenario=tag,release_rom_sha256=executed_sha,core=r.info,frames=r.frame,video_callbacks=r.video_count,audio_frames=r.audio_frames,frames_without_audio_after_startup=gaps,fixtures=fixtures,checks=checks,verified_records={hex(k):v for k,v in seen.items()},pixel_verification=args.language=='ko')
 (out/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));r.close();print(json.dumps({k:v for k,v in result.items() if k not in ('checks','fixtures','verified_records')},ensure_ascii=False))
if __name__=='__main__':main()
