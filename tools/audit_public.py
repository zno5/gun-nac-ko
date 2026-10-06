#!/usr/bin/env python3
"""Fail closed on unreviewed paths, non-text assets, secrets and copied source text."""
from pathlib import Path,PurePosixPath
import argparse,ast,csv,io,json,re,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1]
BLOCKED={'.nes','.fds','.unf','.rom','.bin','.chr','.nam','.ips','.bps','.xdelta','.bdf','.ttf','.otf','.woff','.woff2','.png','.jpg','.gif','.webp','.wav','.mp3','.mp4','.zip','.7z','.state','.sav','.so','.dylib','.dll','.pem','.key'}
MAGIC=[b'NES\x1a',b'PATCH',b'BPS1',b'\x89PNG',b'PK\x03\x04',b'OTTO',b'wOFF',b'STARTFONT ',b'\x00\x01\x00\x00']
SECRETS=[r'gh[pousr]_[A-Za-z0-9]{30,}',r'github_pat_[A-Za-z0-9_]{30,}',r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',r'AKIA[0-9A-Z]{16}']
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def check(name,data,allowed):
 p=PurePosixPath(name)
 assert p.parts[0] not in {'assets','jp','en','analysis','build','local','exports','dist'},'Local-only directory: '+name
 assert name in allowed, 'Not in publish_manifest.json: '+name
 assert not p.is_absolute() and '..' not in p.parts and '\\' not in name,'Unsafe path: '+name
 assert p.suffix.lower() not in BLOCKED,'Asset extension: '+name
 assert len(data)<300000,'Unexpected large public file: '+name
 assert not any(data.startswith(m) for m in MAGIC),'Asset signature: '+name
 assert b'\0' not in data,'Binary content: '+name
 text=data.decode('utf-8-sig')
 for pattern in SECRETS:assert not re.search(pattern,text),'Credential pattern: '+name
 assert not re.search(r'/(?:Users|Volumes)/[^\s\"\']+',text),'Personal absolute path: '+name
 if p.suffix=='.py':ast.parse(text,filename=name)
 if p.suffix=='.json':
  parsed=json.loads(text)
  if p.parts[0]=='templates':assert parsed=={},'Completed layout/display data must stay local: '+name
 if p.suffix=='.csv':
  r=csv.DictReader(io.StringIO(text));assert not {'jp_text','original_bytes','raw_text','bytes'}&set(r.fieldnames or []),'Original extracted text columns: '+name
  parsed_rows=list(r)
  if p.parts[0]=='templates':assert all(not row.get('ko_translation') for row in parsed_rows),'Completed translations must stay local: '+name
 return len(data)
def audit(staged=False,tracked=False):
 manifest=json.loads(git('show',':publish_manifest.json') if staged or tracked else (ROOT/'publish_manifest.json').read_text());allowed=set(manifest['files']);assert len(allowed)==len(manifest['files'])
 if staged or tracked:
  # Inspect the entire index, not just the last diff. Git index is what a commit records.
  names=[s.decode() for s in git('ls-files','-z').split(b'\0') if s]
  assert names,'Empty index; stage the public files first or omit --staged'
  assert set(names)==allowed,'Index and publish_manifest.json differ; review all staged paths'
 else:names=sorted(allowed)
 total=0
 for name in names:
  path=ROOT/name;assert not path.is_symlink(),'Symlink: '+name
  if staged or tracked:
   entry=git('ls-files','--stage','--',name).decode();assert entry.startswith(('100644 ','100755 ')),'Non-regular index entry: '+name
   data=git('show',':'+name)
  else:data=path.read_bytes()
  total+=check(name,data,allowed)
 # Read translation metadata from the same snapshot as the files being audited.
 def data_for(name):return git('show',':'+name) if staged or tracked else (ROOT/name).read_bytes()
 rows=list(csv.DictReader(io.StringIO(data_for('translation/text.csv').decode('utf-8-sig'))))
 assert len({r['jp_text_offset'] for r in rows})==len(rows)
 graphics=list(csv.DictReader(io.StringIO(data_for('translation/graphics.csv').decode('utf-8-sig'))))
 assert len({r['id'] for r in graphics})==len(graphics)
 print(f'PASS: {len(names)} public text files, {total} bytes. No ROM/font/image/patch assets in the inspected set.')
 return names
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--staged',action='store_true');p.add_argument('--tracked',action='store_true');a=p.parse_args()
 try:audit(a.staged,a.tracked)
 except (AssertionError,ValueError,UnicodeError,FileNotFoundError,subprocess.CalledProcessError) as e:raise SystemExit('PUBLIC AUDIT FAILED: '+str(e))
