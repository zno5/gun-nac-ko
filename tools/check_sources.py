#!/usr/bin/env python3
"""Asset-free checks: syntax, unique translation keys, layouts and source addresses."""
from pathlib import Path
import ast,csv,json,re
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT/'tools').glob('*.py'):ast.parse(p.read_text(),filename=p.name)
rows=list(csv.DictReader((ROOT/'translation/text.csv').open(encoding='utf-8-sig')));by_record={}
for row in rows:
 assert row['group'] in ('opening','ending','settings','shop','credits')
 int(row['jp_record_offset'],16);int(row['jp_text_offset'],16)
 if row['review_status'] not in ('배치용 공백','로고 유지'):by_record.setdefault(row['jp_record_offset'],[]).append(row['ko_translation'])
for record,lines in json.loads((ROOT/'translation/layout_overrides.json').read_text()).items():
 assert record in by_record and lines and all(0<len(line)<=28 for line in lines),record
 assert re.sub(r'\s+','',''.join(lines))==re.sub(r'\s+','',''.join(by_record[record])),('Stale line layout',record)
by_offset={r['jp_text_offset']:r for r in rows};assert len(by_offset)==len(rows)
for offset,item in json.loads((ROOT/'translation/display_overrides.json').read_text()).items():assert by_offset[offset]['ko_translation']==item['reviewed_ko_text'],('Stale display override',offset)
graphics=list(csv.DictReader((ROOT/'translation/graphics.csv').open(encoding='utf-8-sig')));assert len({r['id'] for r in graphics})==len(graphics)
assert all(r['ko_translation'] for r in graphics if r['id'].startswith(('stage_','opening_','ending_')))
print(f'PASS: source syntax, {len(rows)} text rows, {len(graphics)} graphic decisions and explicit layouts.')
