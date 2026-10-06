#!/usr/bin/env python3
"""Minimal headless libretro runner for local Mesen. No GUI or global config writes."""
import os
import ctypes as C,sys,json,struct,zlib,hashlib,argparse
from pathlib import Path
def core_path():
 value=os.environ.get('MESEN_CORE')
 if value:
  path=Path(value).expanduser()
 else:
  path=Path.home()/'Library/Application Support/RetroArch/cores/mesen_libretro.dylib'
 if not path.is_file():raise FileNotFoundError('Set MESEN_CORE to your Mesen libretro .dylib/.so/.dll (same architecture as Python).')
 return path
class Game(C.Structure):_fields_=[('path',C.c_char_p),('data',C.c_void_p),('size',C.c_size_t),('meta',C.c_char_p)]
class Variable(C.Structure):_fields_=[('key',C.c_char_p),('value',C.c_char_p)]
class Info(C.Structure):_fields_=[('name',C.c_char_p),('version',C.c_char_p),('extensions',C.c_char_p),('fullpath',C.c_bool),('block_extract',C.c_bool)]
ENV=C.CFUNCTYPE(C.c_bool,C.c_uint,C.c_void_p)
VIDEO=C.CFUNCTYPE(None,C.c_void_p,C.c_uint,C.c_uint,C.c_size_t)
SAMPLE=C.CFUNCTYPE(None,C.c_int16,C.c_int16)
BATCH=C.CFUNCTYPE(C.c_size_t,C.c_void_p,C.c_size_t)
POLL=C.CFUNCTYPE(None)
INPUT=C.CFUNCTYPE(C.c_int16,C.c_uint,C.c_uint,C.c_uint,C.c_uint)
def png(path,w,h,rgb):
 def c(t,d):return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
 raw=b''.join(b'\0'+rgb[y*w*3:(y+1)*w*3] for y in range(h));path.write_bytes(b'\x89PNG\r\n\x1a\n'+c(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+c(b'IDAT',zlib.compress(raw))+c(b'IEND',b''))
class Runner:
 def __init__(self,core,out):
  self.lib=C.CDLL(str(core));self.out=out;out.mkdir(parents=True,exist_ok=True)
  self.directory=str(out.resolve()).encode();self.options={};self.frame=0;self.buttons=set();self.video=None;self.pixel=0;self.audio_frames=0;self.audio_hash=hashlib.sha256();self.video_count=0
  self.log=C.CFUNCTYPE(None,C.c_int,C.c_char_p)(lambda level,fmt:None)
  def env(cmd,data):
   if cmd==27:C.cast(data,C.POINTER(C.c_void_p))[0]=C.cast(self.log,C.c_void_p).value;return True
   if cmd in (9,30,31):C.cast(data,C.POINTER(C.c_char_p))[0]=self.directory;return True
   if cmd==10:self.pixel=C.cast(data,C.POINTER(C.c_int))[0];return self.pixel in (0,1,2)
   if cmd==15:
    v=C.cast(data,C.POINTER(Variable)).contents
    if v.key in self.options:v.value=self.options[v.key];return True
    return False
   if cmd==16:
    vs=C.cast(data,C.POINTER(Variable));i=0
    while vs[i].key:
     raw=vs[i].value or b'';self.options[vs[i].key]=raw.split(b'; ',1)[-1].split(b'|')[0];i+=1
    return True
   if cmd==17:C.cast(data,C.POINTER(C.c_bool))[0]=False;return True
   if cmd==3:C.cast(data,C.POINTER(C.c_bool))[0]=False;return True
   if cmd==47:C.cast(data,C.POINTER(C.c_uint))[0]=0;return True
   if cmd==39:C.cast(data,C.POINTER(C.c_uint))[0]=0;return True
   if cmd in (18,11):return True
   return False
  def video(data,w,h,pitch):
   if data and data!=C.c_void_p(-1).value:self.video=(C.string_at(data,h*pitch),w,h,pitch);self.video_count+=1
  def audio(data,n):self.audio_frames+=n;self.audio_hash.update(C.string_at(data,n*4));return n
  self.callbacks=[ENV(env),VIDEO(video),SAMPLE(lambda l,r:None),BATCH(audio),POLL(lambda:None),INPUT(lambda port,dev,index,key:int(port==0 and key in self.buttons))]
  for name,cb in zip(['environment','video_refresh','audio_sample','audio_sample_batch','input_poll','input_state'],self.callbacks):
   f=getattr(self.lib,'retro_set_'+name);f.argtypes=[type(cb)];f(cb)
   if name=='environment':self.lib.retro_init()
  self.lib.retro_get_system_info.argtypes=[C.POINTER(Info)];info=Info();self.lib.retro_get_system_info(C.byref(info));self.info={'name':info.name.decode(),'version':info.version.decode(),'fullpath':info.fullpath}
  self.lib.retro_load_game.argtypes=[C.POINTER(Game)];self.lib.retro_load_game.restype=C.c_bool
  self.lib.retro_get_memory_data.argtypes=[C.c_uint];self.lib.retro_get_memory_data.restype=C.c_void_p
  self.lib.retro_get_memory_size.argtypes=[C.c_uint];self.lib.retro_get_memory_size.restype=C.c_size_t
 def load(self,rom):
  self.rom=C.create_string_buffer(rom.read_bytes());self.path=str(rom.resolve()).encode();g=Game(self.path,C.cast(self.rom,C.c_void_p),len(self.rom)-1,None)
  if not self.lib.retro_load_game(C.byref(g)):raise RuntimeError('Core failed to load ROM')
 def ram(self):
  size=self.lib.retro_get_memory_size(2);ptr=self.lib.retro_get_memory_data(2)
  return (C.c_uint8*size).from_address(ptr) if ptr and size else None
 def run(self):self.lib.retro_run();self.frame+=1
 def capture(self,path):
  raw,w,h,pitch=self.video;rgb=bytearray(w*h*3)
  for y in range(h):
   for x in range(w):
    if self.pixel==1:
     off=y*pitch+x*4;b,g,r=raw[off:off+3]
    else:
     v=int.from_bytes(raw[y*pitch+x*2:y*pitch+x*2+2],'little');r=((v>>11)&31)*255//31 if self.pixel==2 else ((v>>10)&31)*255//31;g=((v>>5)&63)*255//63 if self.pixel==2 else ((v>>5)&31)*255//31;b=(v&31)*255//31
    off=(y*w+x)*3;rgb[off:off+3]=bytes([r,g,b])
  png(path,w,h,rgb)
 def close(self):self.lib.retro_unload_game();self.lib.retro_deinit()
def main():
 p=argparse.ArgumentParser();p.add_argument('rom',type=Path);p.add_argument('--core',type=Path,default=None);p.add_argument('--out',type=Path,required=True);p.add_argument('--frames',type=int,default=1200);p.add_argument('--every',type=int,default=120);p.add_argument('--start-at',type=int,default=-1);p.add_argument('--press',action='append',default=[],help='start_frame:libretro_button_id:duration');args=p.parse_args();presses=[tuple(map(int,x.split(':'))) for x in args.press]
 r=Runner(args.core or core_path(),args.out);r.load(args.rom);trace=[]
 for f in range(args.frames):
  r.buttons={3} if args.start_at<=f<args.start_at+2 and args.start_at>=0 else set()
  r.buttons.update(key for start,key,duration in presses if start<=f<start+duration);r.run()
  if f%args.every==args.every-1:
   if r.video:r.capture(args.out/f'frame_{f+1:05}.png')
   ram=r.ram();trace.append({'frame':f+1,'ram':bytes(ram).hex() if ram is not None else None,'audio_frames':r.audio_frames})
 report={'core':r.info,'rom_sha256':hashlib.sha256(args.rom.read_bytes()).hexdigest(),'frames':args.frames,'video_callbacks':r.video_count,'audio_frames':r.audio_frames,'audio_sha256':r.audio_hash.hexdigest(),'trace':trace};(args.out/'run.json').write_text(json.dumps(report,indent=2));r.close();print(json.dumps({k:v for k,v in report.items() if k!='trace'}))
if __name__=='__main__':main()
