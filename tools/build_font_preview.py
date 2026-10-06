#!/usr/bin/env python3
"""Compile reviewed strings and original BDF pixels to NES 2bpp and offline previews.
No ROM modification. All runtime fields use explicitly illustrative sample values.
"""
from pathlib import Path
import csv,json,re,hashlib,zlib,struct,html,collections,io
from font_policy import apply_font_policy, POLICY
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'build/font_preview';OUT.mkdir(parents=True,exist_ok=True)
BDF=ROOT/'assets/fonts/Galmuri11-Condensed.bdf'
source=(ROOT/'translation/text.csv').read_bytes()
rows=list(csv.DictReader(io.StringIO(source.decode('utf-8-sig'))))
overrides=json.loads((ROOT/'translation/display_overrides.json').read_text())
layout_overrides=json.loads((ROOT/'translation/layout_overrides.json').read_text())
font={};text=BDF.read_text();baseline=14
assert re.search(r'^FONT_ASCENT 14$',text,re.M) and re.search(r'^FONT_DESCENT 2$',text,re.M)
for block in text.split('STARTCHAR ')[1:]:
 cp=int(re.search(r'^ENCODING (-?\d+)',block,re.M)[1])
 if cp<0:continue
 w,h,x,y=map(int,re.search(r'^BBX (.*)',block,re.M)[1].split())
 bitmap=block.split('BITMAP\n',1)[1].split('ENDCHAR',1)[0].splitlines()
 font[chr(cp)]=(w,h,x,y,bitmap)
def mask(c):
 if c not in font:raise ValueError(f'Missing BDF glyph: {c!r}')
 w,h,ox,oy,bitmap=font[c];out=bytearray(16)
 assert len(bitmap)==h,(c,h,len(bitmap))
 for row,line in enumerate(bitmap):
  bits=int(line,16);size=len(line)*4
  for col in range(w):
   if bits&(1<<(size-col-1)):
    x,y=ox+col,baseline-oy-h+row
    if not (0<=x<8 and 0<=y<16):raise ValueError(f'Ink outside cell: {c!r} ({x},{y})')
    out[y]|=0x80>>x
 return apply_font_policy(c, bytes(out))
def patterns(m):return (m[:8]+bytes(8),m[8:]+bytes(8))
def decode_pattern(p):
 return [[((p[y]>>(7-x))&1)|(((p[y+8]>>(7-x))&1)<<1) for x in range(8)] for y in range(8)]
def png(path,w,h,pix):
 def chunk(t,d):return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
 raw=b''.join(b'\0'+bytes(pix[y*w*3:(y+1)*w*3]) for y in range(h))
 path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b''))
samples={'소지금':'999','무기번호':'5','폭탄번호':'4','폭탄종류':'F','폭탄수량':'20','무기레벨':'5','연사단계':'9','배송수량':'20'}
def expand(s):
 return re.sub(r'\{([^{}]+)\}',lambda m:samples[m[1]],s)
def wrap(s):
 result=[];line=''
 for word in s.split():
  if line and len(line)+1+len(word)>28:result.append(line);line=''
  while len(word)>28:
   if line:result.append(line);line=''
   result.append(word[:28]);word=word[28:]
  if word:line=(line+' '+word).strip()
 if line:result.append(line)
 return result
records=collections.OrderedDict()
for r in rows:records.setdefault(r['jp_record_offset'],[]).append(r)
if set(layout_overrides)-set(records):raise ValueError('Layout override refers to an unknown record')
characters=set(' 0123456789FBTW')
for r in rows:
 if r['review_status'] in ('배치용 공백','로고 유지'):continue
 s=overrides.get(r['jp_text_offset'],{}).get('text',r['ko_translation'])
 characters.update(expand(s))
masks={c:mask(c) for c in sorted(characters)}
for c,m in masks.items():
 rebuilt=decode_pattern(patterns(m)[0])+decode_pattern(patterns(m)[1])
 assert all(rebuilt[y][x]==((m[y]>>(7-x))&1) for y in range(16) for x in range(8)),c
pool=[];ids={};glyph_table={}
for c,m in masks.items():
 pair=[]
 for pattern in patterns(m):
  if pattern not in ids:ids[pattern]=len(pool);pool.append(pattern)
  pair.append(ids[pattern])
 glyph_table[c]=pair
(OUT/'glyphs_8x16.1bpp').write_bytes(b''.join(masks.values()))
(OUT/'global_patterns.2bpp').write_bytes(b''.join(pool))
(OUT/'glyph_index.json').write_text(json.dumps({'characters':list(masks),'tile_ids':glyph_table,'id_scope':'Global build IDs, not directly writable PPU tile numbers'},ensure_ascii=False,indent=2))
page_records=[];record_metrics=[];group_patterns=collections.defaultdict(set)
for address,rr in records.items():
 group=rr[0]['group'];active=[r for r in rr if r['review_status'] not in ('배치용 공백','로고 유지')]
 if not active:continue
 sentences=[expand(overrides.get(r['jp_text_offset'],{}).get('text',r['ko_translation'])) for r in active]
 lines=[]
 if address in layout_overrides:
  lines=layout_overrides[address]
  # User-approved whitespace/line breaks must not silently replace later CSV edits.
  if re.sub(r'\s+','',''.join(lines))!=re.sub(r'\s+','',''.join(sentences)):
   raise ValueError(f'Stale layout override: {address}; reconcile with current translation')
  if not lines or any(not line or '\n' in line or '\r' in line or len(line)>28 for line in lines):
   raise ValueError(f'Invalid or over-wide explicit layout: {address}')
 elif group in ('opening','ending'):
  paragraphs=[];paragraph=''
  for s in sentences:
   if s.startswith('“') and paragraph:paragraphs.append(paragraph);paragraph=''
   paragraph=(paragraph+' '+s).strip()
  if paragraph:paragraphs.append(paragraph)
  for paragraph in paragraphs:lines+=wrap(paragraph)
 else:
  for s in sentences:lines+=wrap(s)
 used={t for line in lines for c in line for t in patterns(masks[c])}|{bytes(16)}
 group_patterns[group].update(used)
 record_metrics.append({'record':address,'group':group,'lines':len(lines),'unique_8x8_patterns':len(used),'isolated_4k_bank_fits':len(used)<=256})
 for page_start in range(0,len(lines),5):
  page=lines[page_start:page_start+5];pats=[bytes(16)];mapping={bytes(16):0};nt=bytearray(32*30)
  for row,line in enumerate(page):
   for col,c in enumerate(line):
    for half,pattern in enumerate(patterns(masks[c])):
     if pattern not in mapping:mapping[pattern]=len(pats);pats.append(pattern)
     assert len(pats)<=256,'Pattern table overflow'
     nt[(17+row*2+half)*32+2+col]=mapping[pattern]
  bank=b''.join(pats).ljust(4096,b'\0')
  name=f'{group}_{address[2:]}_{page_start//5+1}'
  (OUT/f'{name}.chr').write_bytes(bank);(OUT/f'{name}.nam').write_bytes(nt+bytes(64))
  pix=bytearray(bytes([16,20,28])*256*240)
  for cell,tile in enumerate(nt):
   bits=decode_pattern(bank[tile*16:tile*16+16])
   for yy in range(8):
    for xx in range(8):
     if bits[yy][xx]:
      at=(((cell//32)*8+yy)*256+(cell%32)*8+xx)*3;pix[at:at+3]=b'\xff\xff\xff'
  png(OUT/f'{name}.png',256,240,pix)
  page_records.append({'name':name,'record':address,'group':group,'lines':page,'unique_patterns':len(pats),'remaining_tiles_before_other_assets':256-len(pats)})
# Full glyph sheet for baseline and batch visual checks.
cols=24;w=cols*8;h=((len(masks)+cols-1)//cols)*16;pix=bytearray(bytes([16,20,28])*w*h)
for i,(c,m) in enumerate(masks.items()):
 for yy in range(16):
  for xx in range(8):
   if m[yy]&(0x80>>xx):
    at=(((i//cols)*16+yy)*w+(i%cols)*8+xx)*3;pix[at:at+3]=b'\xff\xff\xff'
png(OUT/'glyph_sheet.png',w,h,pix)
# Candidate 4 KiB banks per screen family. No claim about non-text assets fitting.
for group,used in group_patterns.items():
 ordered=[bytes(16)]+sorted(used-{bytes(16)})
 if len(ordered)>256:raise ValueError(f'Group {group} needs more than 256 tiles')
 local={p:i for i,p in enumerate(ordered)}
 (OUT/f'group_{group}.chr').write_bytes(b''.join(ordered).ljust(4096,b'\0'))
 table={c:[local[p] for p in patterns(m)] for c,m in masks.items() if all(p in local for p in patterns(m))}
 (OUT/f'group_{group}_glyphs.json').write_text(json.dumps(table,ensure_ascii=False,indent=2))
manifest={'source_csv_sha256':hashlib.sha256(source).hexdigest(),'font_sha256':hashlib.sha256(BDF.read_bytes()).hexdigest(),'font':'Galmuri11-Condensed','baseline':baseline,'cell':[8,16],'advance_all_characters':8,'space_advance':8,'ppu_plane_policy':'plane0=ink, plane1=0; grayscale proof only','sample_tokens':samples,'dynamic_limits_verified':False,'glyph_count':len(masks),'hangul_count':sum('\uac00'<=c<='\ud7a3' for c in masks),'global_unique_8x8_patterns':len(pool),'global_chr_bytes':len(pool)*16,'group_pattern_unions':{g:len(v) for g,v in group_patterns.items()},'records':record_metrics,'pages':page_records,'validation':{'missing_glyphs':0,'clipped_ink_pixels':0,'all_glyphs_roundtrip_2bpp':True,'isolated_page_banks_fit':all(p['unique_patterns']<=256 for p in page_records),'ROM_patched':False,'emulator_tested':False},'limitations':['Offline text-only render; no original graphics, palette, IRQ, sprites or runtime numbers.','Menu pagination is a proof of text layout, not an implemented menu flow.','Per-page fits exclude other simultaneously visible assets and retained previous text.']}
manifest['layout_overrides_sha256']=hashlib.sha256((ROOT/'translation/layout_overrides.json').read_bytes()).hexdigest()
manifest['font_policy']=POLICY
manifest['display_overrides_sha256']=hashlib.sha256((ROOT/'translation/display_overrides.json').read_bytes()).hexdigest()
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
parts=['<!doctype html><meta charset="utf-8"><title>건낙 한글 글꼴 시안</title><style>body{background:#17202b;color:#eee;font:16px system-ui;margin:32px}a{color:#9cf}img{image-rendering:pixelated}.screen{width:512px;max-width:100%}section{border-top:1px solid #567;padding:20px 0}button,select{font:inherit}pre{white-space:pre-wrap}.hidden{display:none}</style><h1>Galmuri11-Condensed · 8×16 한글 시안</h1><p>B2 적용: 한글은 갈무리, 영문·숫자·확인된 기호는 원본 글꼴을 y=5–12에 배치했습니다. 실제 BDF·CHR 픽셀로 만든 오프라인 시안입니다. 실행 중인 ROM 화면이 아닙니다. 위쪽 그림 영역은 비워 두었습니다. 메뉴 줄바꿈·페이지와 숫자는 시연용입니다.</p><p>CSV의 영어 유지 메모 7건은 별도 출력 규칙으로 반영했습니다.</p><label>배율 <select id="scale"><option value="1">1×</option><option value="2" selected>2×</option><option value="3">3×</option></select></label> <label>화면 <select id="group"><option value="all">전체</option><option>opening</option><option>ending</option><option>shop</option><option>settings</option><option>credits</option></select></label><p><a href="manifest.json">실제 패턴 수·검증 정보</a> · <a href="../../translation/ko_review.md">검토 번역</a></p><h2>전체 사용 글자</h2><img src="glyph_sheet.png" style="width:384px">']
for p in page_records:
 parts.append(f'<section data-group="{p["group"]}"><h2>{p["group"]} · {p["record"]} · {p["unique_patterns"]} tiles</h2><img class="screen" src="{p["name"]}.png"><pre>{html.escape(chr(10).join(p["lines"]))}</pre></section>')
parts.append('<script>document.querySelector("#scale").onchange=e=>document.querySelectorAll(".screen").forEach(i=>i.style.width=(256*Number(e.target.value))+"px");document.querySelector("#group").onchange=e=>document.querySelectorAll("section").forEach(s=>s.hidden=e.target.value!=="all"&&s.dataset.group!==e.target.value);</script>')
(OUT/'index.html').write_text('\n'.join(parts))
print(json.dumps({k:manifest[k] for k in ['glyph_count','hangul_count','global_unique_8x8_patterns','global_chr_bytes','group_pattern_unions','validation']},ensure_ascii=False,indent=2));print('Preview pages:',len(page_records))
