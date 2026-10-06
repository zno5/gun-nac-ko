from pathlib import Path
import sys,json
sys.path.insert(0,'tools')
from run_mesen import Runner, core_path
out=Path('build/runtime/caption_cards');out.mkdir(parents=True,exist_ok=True)
for label,src in [('before',Path('build/shop_patch/Gun Nac (Korean shop prototype).nes')),('after',Path('build/caption_patch/Gun Nac (Korean captions prototype).nes'))]:
 for idx in range(5):
  data=bytearray(src.read_bytes());data[0xe61:0xe68]=bytes.fromhex('a9 01 85 4c 4c 72 95');data[0x1597:0x15a5]=bytes([0x20,0x04,0xa8,0x20,0x05,0xe8,0xa9,idx,0x20,0xd1,0x96,0x4c,0xa0,0x95]);p=out/f'{label}_{idx}_TEST_ONLY.nes';p.write_bytes(data)
  r=Runner(core_path(),out/f'{label}_{idx}');r.load(p)
  for f in range(360):r.run()
  r.capture(out/f'{label}_{idx}.png');r.close();print(label,idx,flush=True)
from font_bitmap import readpng
checks=[]
for idx in range(5):
 before=readpng(out/f'before_{idx}.png');after=readpng(out/f'after_{idx}.png')
 top,bottom,shift=(16,112,16) if idx in (1,2,3) else (32,112,0)
 assert before[top*768:bottom*768]==after[(top+shift)*768:(bottom+shift)*768],idx
 checks.append(dict(card=idx,picture_pixel_identical=True,shift_y=shift))
(out/'verification.json').write_text(json.dumps(checks,indent=2))
print('All five card illustrations preserved pixel-for-pixel.')
