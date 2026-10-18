import sys; sys.path.insert(0,'film')
import numpy as np, render, scenes as S, moderngl
from PIL import Image
r=render.Renderer(); eng=r.eng
n=S.SCENE_OBJS['neuro']; n.build(eng)
fbo=eng.hdr['A'][1]; ctx=eng.ctx; mgl=moderngl
t=float(sys.argv[1]); which=sys.argv[2]
fbo.use(); fbo.clear(0,0,0,1)
ctx.enable(mgl.BLEND); ctx.blend_func=mgl.ONE,mgl.ONE; ctx.enable(mgl.PROGRAM_POINT_SIZE)
cam=n.cam(t)
for prog in (n.rprog,n.pprog):
    for k,v in dict(uCam=tuple(cam),uFocal=2.0,uFocus=9.0,uCoc=0.075,uAspect=1920/1080,uFront=float(n.front(t)),uTime=t,uIdle=0.5,uH=1080.0).items():
        if k in prog: prog[k].value=v
if which in('r','a'): n.rvao.render(mgl.TRIANGLES)
if which in('p','a'): n.pvao.render(mgl.POINTS, vertices=n.npts)
a=np.frombuffer(fbo.read(components=4,dtype='f2'),dtype=np.float16).reshape(1080,1920,4).astype(np.float32)[...,:3][::-1]
img=(np.clip(a*2.0,0,1)**(1/2.2)*255).astype(np.uint8)
Image.fromarray(img).save('out/dbg_n.png')
