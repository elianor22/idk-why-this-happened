#version 430
in vec3 aPos; in vec3 aPrev; in vec3 aNext;
in float aSide; in float aD; in float aW; in float aA; in float aC; in float aB; in float aSeed;
uniform vec3 uCam;
uniform float uFocal;
uniform float uFocus;
uniform float uCoc;
uniform float uAspect;
out float vU; out float vD; out float vSoft; out float vFade; out float vA; out float vC; out float vB; out float vSeed;

vec3 projv(vec3 w, out float depth){
    vec3 p = w - uCam;
    depth = -p.z;
    return vec3(p.x / max(depth, 0.05) * uFocal, p.y / max(depth, 0.05) * uFocal, depth);
}
void main(){
    float d0, d1, d2;
    vec3 sp = projv(aPos, d0);
    vec3 sn = projv(aNext, d1);
    vec3 sv = projv(aPrev, d2);
    vec2 dir = sn.xy - sv.xy;
    if (length(dir) < 1e-7) dir = vec2(1.0, 0.0);
    dir = normalize(dir);
    vec2 nrm = vec2(-dir.y, dir.x);
    float coc = uCoc * abs(d0 - uFocus) / max(d0, 0.1);
    float ws = aW * uFocal / max(d0, 0.1);
    float we = min(sqrt(ws * ws + coc * coc), 0.05);
    we = max(we, ws);
    vec2 pos = sp.xy + nrm * aSide * we * 1.9;
    vSoft = clamp(coc / max(we, 1e-5), 0.0, 1.0) * clamp(coc * 20.0, 0.0, 1.0);
    vFade = clamp(ws / max(we, 1e-5), 0.0, 1.0);   // energy conservation
    vU = aSide; vD = aD; vA = aA; vC = aC; vB = aB; vSeed = aSeed;
    float zn = clamp(d0 / 60.0, 0.0, 1.0);
    gl_Position = vec4(pos.x * 2.0 / uAspect, pos.y * 2.0, zn, 1.0);
}
