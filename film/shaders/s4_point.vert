#version 430
in vec3 aPos; in float aSize; in float aD; in float aA; in float aC; in float aB; in float aSeed;
uniform vec3 uCam;
uniform float uFocal;
uniform float uFocus;
uniform float uCoc;
uniform float uAspect;
uniform float uH;
out float vD; out float vA; out float vC; out float vB; out float vSeed; out float vE; out float vSoft;
void main(){
    vec3 p = aPos - uCam;
    float depth = -p.z;
    vec2 sp = p.xy / max(depth, 0.05) * uFocal;
    float coc = uCoc * abs(depth - uFocus) / max(depth, 0.1);
    float rs = aSize * uFocal / max(depth, 0.1);
    float re = sqrt(rs * rs + coc * coc);
    gl_PointSize = clamp(re * uH * 2.0 * 2.2, 2.0, 700.0);
    vE = (rs * rs) / (re * re);
    vSoft = clamp(coc / re, 0.0, 1.0);
    vD = aD; vA = aA; vC = aC; vB = aB; vSeed = aSeed;
    gl_Position = vec4(sp.x * 2.0 / uAspect, sp.y * 2.0, clamp(depth / 60.0, 0.0, 1.0), 1.0);
}
