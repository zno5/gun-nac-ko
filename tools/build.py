#!/usr/bin/env python3
"""Rebuild the entire patch from public sources plus a local ROM and three BDFs."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys
from prepare_inputs import prepare
ROOT=Path(__file__).resolve().parents[1]
STEPS=['build_font_preview','build_story_patch','build_settings_patch','build_credits_patch','build_shop_patch','build_caption_patch','build_stage_patch']
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,default=ROOT/'jp/Gun Nac (Japan).nes');p.add_argument('--check-reference',action='store_true',help='Require the original reviewed ROM and IPS checksums; omit when editing translations');args=p.parse_args()
 if sys.version_info<(3,10):raise SystemExit('Python 3.10 or newer is required')
 if not __debug__:raise SystemExit('Do not use python -O: this build relies on assertions')
 if not args.rom.is_file():raise SystemExit('Supply your own Japanese ROM with --rom PATH; see docs/BUILD.ko.md')
 prepare(args.rom)
 for item in json.loads((ROOT/'config/font_sources.json').read_text())['fonts']:
  path=ROOT/item['destination']
  if not path.is_file():raise SystemExit('Missing font. Run: python3 tools/fetch_fonts.py (or supply the exact BDF manually)')
  if hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:raise SystemExit('Wrong BDF version: '+item['destination'])
 out=ROOT/'build';out.mkdir(exist_ok=True)
 for name in STEPS:
  print('Building:',name,flush=True)
  with (out/(name+'.log')).open('w',encoding='utf-8') as log:
   try:subprocess.run([sys.executable,str(ROOT/'tools'/(name+'.py'))],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
   except subprocess.CalledProcessError:
    print((out/(name+'.log')).read_text(),file=sys.stderr);raise
 target=out/'stage_patch/Gun Nac (Korean).nes';ips=out/'stage_patch/gun_nac_ko.ips'
 actual=dict(target_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),ips_sha256=hashlib.sha256(ips.read_bytes()).hexdigest(),target_bytes=target.stat().st_size)
 expected=json.loads((ROOT/'config/reference_build.json').read_text());actual['matches_reference']=all(actual[k]==expected[k] for k in ('target_sha256','ips_sha256','target_bytes'))
 if args.check_reference and not actual['matches_reference']:raise SystemExit('Build differs from reference: '+json.dumps(actual))
 (out/'build_result.json').write_text(json.dumps(actual,indent=2)+'\n')
 print(json.dumps(actual,indent=2));print('Local IPS:',ips);print('Do not publish generated assets; read docs/RIGHTS.ko.md')
if __name__=='__main__':main()
