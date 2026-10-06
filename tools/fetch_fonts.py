#!/usr/bin/env python3
"""Fetch only pinned official font sources, never ROMs. Python standard library."""
from pathlib import Path
import argparse,hashlib,json,urllib.request
ROOT=Path(__file__).resolve().parents[1]
def fetch():
 config=json.loads((ROOT/'config/font_sources.json').read_text())
 for item in config['fonts']+config['notices']:
  dest=ROOT/item['destination'];expected=item.get('sha256')
  if dest.exists() and expected and hashlib.sha256(dest.read_bytes()).hexdigest()==expected:
   print('Verified local:',item['destination']);continue
  request=urllib.request.Request(item['url'],headers={'User-Agent':'gun-nac-ko-source-build'})
  with urllib.request.urlopen(request,timeout=45) as response:data=response.read(8*1024*1024+1)
  if len(data)>8*1024*1024:raise ValueError('Unexpectedly large font resource')
  if expected and hashlib.sha256(data).hexdigest()!=expected:raise ValueError('Upstream checksum mismatch: '+item['destination'])
  dest.parent.mkdir(parents=True,exist_ok=True);temporary=dest.with_suffix(dest.suffix+'.tmp');temporary.write_bytes(data);temporary.replace(dest)
  print('Downloaded and verified:',item['destination'])
 (ROOT/'assets/fonts/dos/provenance.json').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.parse_args();fetch()
