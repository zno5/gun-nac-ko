"""Text decoding rules; extracted game strings stay local and untracked."""
import unicodedata
def decode(bs):
 kata=False;s='';raw='';width=0
 for b in bs:
  if b==0x5e:kata=not kata;raw+='<KANA>';continue
  if 0xa1<=b<=0xdf:
   c=bytes([b]).decode('shift_jis');raw+=c
   c=unicodedata.normalize('NFKC',c)
   if b in (0xde,0xdf):s+=chr(0x3099 if b==0xde else 0x309a);continue
   if not kata:c=''.join(chr(ord(x)-0x60) if 0x30a1<=ord(x)<=0x30f6 else x for x in c)
  elif 32<=b<=0x5d:c=chr(b);raw+=c
  else:c=f'<TILE:{b:02X}>';raw+=c
  s+=c;width+=1
 return unicodedata.normalize('NFC',s),raw,width
regions=[('settings',0x1471,0x14cd),('settings',0x14d5,0x156e),('shop',0x1fb1,0x237c),('opening',0x298d,0x2cea),('ending',0x2cea,0x2ec1)]
# Each screen record is PPU address LE + payload, FE + PPU address LE + payload, FF.
def records(d,group,lo,hi):
 p=lo;out=[]
 while p<hi:
  if d[p:p+2]==b'\0\0':p+=2;continue
  start=p;lines=[]
  while True:
   assert p+2<=hi,(group,hex(p));addr=int.from_bytes(d[p:p+2],'little');assert 0x2000<=addr<0x3000,(group,hex(p),hex(addr));p+=2;q=p
   while p<hi and d[p] not in (254,255):p+=1
   assert p<hi,(group,hex(q));bs=d[q:p];txt,raw,width=decode(bs)
   lines.append({'file_offset':f'0x{q:06X}','ppu':f'0x{addr:04X}','x':addr%32,'y':(addr%1024)//32,'bytes':bs.hex(' '),'text':txt,'raw_text':raw,'display_cells':width})
   end=d[p];p+=1
   if end==255:break
  out.append({'group':group,'start':f'0x{start:06X}','end_exclusive':f'0x{p:06X}','cpu_address':f'0x{start+0x7ff0:04X}','byte_length':p-start,'lines':lines})
 return out
def credits(d):
 p=0x1801;out=[]
 while p<0x1a4b:
  if d[p]==255:break
  if d[p]==254:p+=1;continue
  start=p;pos=d[p];p+=1;q=p
  while d[p] not in (254,255):p+=1
  bs=d[q:p];txt,raw,width=decode(bs)
  out.append({'group':'credits','start':f'0x{start:06X}','end_exclusive':f'0x{p+1:06X}','cpu_address':f'0x{start+0x7ff0:04X}','byte_length':p+1-start,'lines':[{'file_offset':f'0x{q:06X}','ppu':'scroll','x':pos&31,'y':'','position_byte':f'{pos:02X}','bytes':bs.hex(' '),'text':txt,'raw_text':raw,'display_cells':width}]});p+=1
 return out
