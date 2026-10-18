import sys; sys.path.insert(0,'film')
import numpy as np, render, scenes as S
src=open('film/shaders/s1_stars.frag').read().replace("col += starLayer","//col += starLayer")
open('film/shaders/s1_dbg.frag','w').write(src)
r=render.Renderer()
class D(S.Stars):
    def render(self,eng,fbo,t,frame):
        hero=np.zeros((8,4),'f4'); hud=np.zeros(8,'f4'); dim=np.ones(8,'f4')
        eng.pass_("s1_dbg.frag",fbo,uTime=t,uFrame=0,uHero=hero,uHud=hud,uHudDim=dim,uRing=(0,0,0,0),uZoom=1.0,uWhite=0.0,uFadeIn=1.0,uNHero=0)
    def text(self,t,m,h): pass
r.objs[0]=D()
render.to_png(r.frame(float(sys.argv[1]),90),'out/neb.png')
