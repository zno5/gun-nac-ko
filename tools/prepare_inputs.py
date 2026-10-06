#!/usr/bin/env python3
"""Validate a user-supplied ROM and derive ignored, local-only text metadata."""
from pathlib import Path
import argparse,hashlib,json,shutil,zlib
from rom_text import regions,records,credits
ROOT=Path(__file__).resolve().parents[1]
def fingerprints(data):
 return dict(bytes=len(data),crc32=f'{zlib.crc32(data)&0xffffffff:08X}',**{k:hashlib.new(k,data).hexdigest() for k in ('md5','sha1','sha256')})
def prepare(path):
 spec=json.loads((ROOT/'config/rom.json').read_text());data=path.read_bytes();actual=fingerprints(data)
 for k,v in actual.items():
  if v!=spec[k]:raise ValueError(f'Wrong source ROM: {k}: expected {spec[k]}, got {v}. Hashes include the 16-byte header.')
 destination=ROOT/'jp/Gun Nac (Japan).nes';destination.parent.mkdir(exist_ok=True)
 others=[p for p in destination.parent.glob('*.nes') if p!=destination]
 if others:raise ValueError('Keep exactly one .nes file in jp/: '+', '.join(p.name for p in others))
 if destination.exists() and destination.read_bytes()!=data:raise ValueError('Refusing to replace a different local input ROM')
 if path.resolve()!=destination.resolve():shutil.copyfile(path,destination)
 extracted=[]
 for args in regions:extracted+=records(data,*args)
 extracted+=credits(data)
 for p in json.loads((ROOT/'config/story_pointers.json').read_text()):
  off=int(p['pointer_file'],16);assert int.from_bytes(data[off:off+2],'little')==int(p['cpu_target'],16)
 out=ROOT/'analysis';out.mkdir(exist_ok=True)
 (out/'jp_text.json').write_text(json.dumps(extracted,ensure_ascii=False,indent=2)+'\n')
 (out/'input_hashes.json').write_text(json.dumps(actual,indent=2)+'\n')
 return actual
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--rom',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.rom),indent=2))
