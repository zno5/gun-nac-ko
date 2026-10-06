#!/usr/bin/env python3
"""Export only reviewed text sources. Never archive the whole working directory."""
from pathlib import Path
import argparse,hashlib,json,zipfile
from audit_public import ROOT,audit
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'dist/gun-nac-ko-source.zip');a=p.parse_args();
 names=audit();a.out.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(a.out,'w',zipfile.ZIP_DEFLATED) as z:
  for name in names:
   info=zipfile.ZipInfo('gun-nac-ko/'+name,date_time=(2026,10,6,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=(0o100755 if name.startswith('.githooks/') else 0o100644)<<16;z.writestr(info,(ROOT/name).read_bytes())
 with zipfile.ZipFile(a.out) as z:assert z.testzip() is None;assert len(z.namelist())==len(names)
 print(a.out);print('SHA-256:',hashlib.sha256(a.out.read_bytes()).hexdigest())
