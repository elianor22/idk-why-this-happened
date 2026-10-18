#version 430
uniform vec4 uSeg[160];
uniform vec2 uSegP[160];
uniform int uNSeg;
uniform float uBoltProg;
uniform float uBoltI;
uniform float uBoltX;
uniform float uSheet;
uniform vec2 uSheetC;
uniform float uYh;
uniform float uRingR;
uniform float uRingA;
uniform vec2 uStrikeW;
uniform vec2 uShake;
uniform float uFadeIn;
uniform float uThunder;   // 0..1 impact envelope
uniform float uWhite;
out vec4 o;

vec3 bolt(vec2 p){
    float core = 0.0, glow = 0.0, wide = 0.0;
    for (int i = 0; i < 160; i++){
        if (i >= uNSeg) break;
        vec2 pr = uSegP[i];
        if (pr.x > uBoltProg) continue;
        vec4 sg = uSeg[i];
        float d = sdSeg(p, sg.xy, sg.zw);
        float b = pr.y;
        core = max(core, b * smoothstep(0.0022 * (0.6 + 0.6 * b), 0.0, d));
        glow = max(glow, b * exp(-d / 0.009));
        wide = max(wide, b * exp(-d / 0.065));
    }
    return (vec3(0.90, 0.94, 1.0) * (core * 7.0 + glow * 1.4) + vec3(0.50, 0.55, 1.0) * wide * 0.32) * uBoltI;
}

vec3 sky(vec2 uv){
    float t = uTime;
    float h = uv.y - uYh;
    vec3 col = mix(vec3(0.014, 0.024, 0.040), vec3(0.002, 0.004, 0.010), smoothstep(0.0, 0.75, h));
    float hh = max(h, 0.0) + 0.055;
    vec2 cp = vec2(uv.x * 0.55, 0.62) / hh;
    float d1 = fbm(vec3(cp * 0.8 + vec2(t * 0.05, 0.0), t * 0.02), 6);
    vec2 toL = normalize(vec2(uBoltX, 0.3) - uv + 1e-4);
    float d1b = fbm(vec3((cp + toL * 0.10) * 0.8 + vec2(t * 0.05, 0.0), t * 0.02), 5);
    float d2 = fbm(vec3(cp * 2.1 + vec2(-t * 0.04, 0.0) + 7.0, t * 0.03), 5);
    float dens = smoothstep(-0.25, 0.45, d1 * 0.95 + d2 * 0.35 + 0.08);
    float edge = clamp((d1 - d1b) * 5.0, -1.0, 1.0);
    // lightning light
    float Ls = uSheet * exp(-length(uv - uSheetC) / 0.65);
    float Lb = uBoltI * exp(-abs(uv.x - uBoltX) / 0.30) * (0.4 + 0.6 * smoothstep(-0.1, 0.4, uv.y));
    float L = Ls * 0.9 + Lb * 0.20;
    vec3 lc = vec3(0.62, 0.72, 1.0);
    vec3 cl = vec3(0.016, 0.024, 0.040) * (0.15 + 1.35 * pow(dens, 1.4));
    cl += lc * L * (0.10 + 0.9 * pow(1.0 - dens * 0.85, 2.0)) * (0.5 + 0.5 * dens) * 1.4;
    cl += lc * L * max(edge, 0.0) * 0.5 * dens;
    col = mix(col, cl, smoothstep(-0.02, 0.10, h) * 0.97 + 0.02);
    // horizon glow
    col += vec3(0.03, 0.055, 0.085) * exp(-h * 14.0) * (0.35 + 1.2 * (Ls + Lb * 0.5)) ;
    col += bolt(uv);
    return col;
}

float Ls_(vec2 uv){ return uSheet * 0.7 + uBoltI * 0.5; }

vec3 sea(vec2 uv, float t){
    float dy = max(uYh - uv.y, 0.0008);
    float zw = 1.0 / dy;
    vec2 w = vec2(uv.x * zw, zw);
    vec2 sp = vec2(w.x * 0.30, w.y * 1.25);
    float e = 0.03;
    float h0 = fbm(vec3(sp, t * 0.20), 5) + 0.22 * fbm(vec3(sp * 3.1 + 5.0, t * 0.45), 3);
    float hx = fbm(vec3(sp + vec2(e, 0.0), t * 0.20), 5) + 0.22 * fbm(vec3((sp + vec2(e, 0.0)) * 3.1 + 5.0, t * 0.45), 3);
    float hz = fbm(vec3(sp + vec2(0.0, e), t * 0.20), 5) + 0.22 * fbm(vec3((sp + vec2(0.0, e)) * 3.1 + 5.0, t * 0.45), 3);
    vec2 g = vec2(hx - h0, hz - h0) / e * vec2(0.5, 1.0);
    // sound wave ripples on the water
    float dist = length(w - uStrikeW);
    float q = dist - uRingR;
    float rip = 0.0;
    if (uRingA > 0.0){
        float env = exp(min(q, 0.0) * 0.55) * smoothstep(0.6, -0.1, q) * smoothstep(0.0, 0.5, uRingR);
        rip = sin(q * 5.5) * env * uRingA;
        g += normalize(w - uStrikeW + 1e-4) * rip * 0.9;
    }
    vec2 duv = vec2(g.x * 0.05, g.y * 0.018) / (1.0 + 0.05 * zw);
    duv.x += g.x * 0.0;
    vec2 ruv = vec2(uv.x + duv.x, 2.0 * uYh - uv.y + duv.y);
    vec3 refl = sky(ruv);
    float cosv = clamp(dy * 2.2, 0.0, 1.0);
    float fres = 0.08 + 0.92 * pow(1.0 - cosv, 3.5);
    vec3 base = vec3(0.0012, 0.0045, 0.0090) * (0.5 + 1.2 * smoothstep(-0.3, 0.5, h0));
    vec3 col = base + refl * fres * 0.85;
    // crest sparkle
    float crest = smoothstep(0.25, 1.1, g.y) * (Ls_(uv)) / (1.0 + 0.1 * zw);
    col += vec3(0.55, 0.65, 0.9) * crest * 0.9;
    // wavefront
    float fw = 0.03 * (1.0 + 0.04 * dist);
    float front = exp(-abs(q) / fw) * uRingA * smoothstep(0.0, 0.4, uRingR);
    col += vec3(0.75, 0.85, 1.0) * front * (0.9 + 0.3 * rip) * 1.3;
    col += vec3(0.30, 0.45, 0.8) * exp(-abs(q) / (fw * 8.0)) * uRingA * 0.25 * smoothstep(0.0, 0.4, uRingR);
    // distance fog
    float fog = 1.0 - exp(-zw * 0.07);
    col = mix(col, vec3(0.020, 0.036, 0.055) * (0.5 + 1.6 * (uSheet + uBoltI * 0.2)), fog * 0.55);
    return col;
}

float rain(vec2 uv, float t, float scale, float speed, float slant, int seed){
    vec2 p = vec2(uv.x + uv.y * slant, uv.y) ;
    p.x *= scale;
    float id = floor(p.x);
    float r = h12(ivec2(int(id), seed));
    float y = fract(p.y * (0.7 + r) * 0.6 + t * speed * (0.6 + 0.8 * r) + r * 11.0);
    float streak = smoothstep(0.0, 0.03, y) * smoothstep(0.16, 0.03, y);
    float xc = abs(fract(p.x) - 0.5);
    float line = smoothstep(0.06, 0.0, xc) ;
    return streak * line * step(0.45, r) ;
}

void main(){
    vec2 uv = (gl_FragCoord.xy - 0.5 * uRes) / uRes.y;
    uv += uShake;
    float t = uTime;
    vec3 col;
    if (uv.y >= uYh) col = sky(uv);
    else col = sea(uv, t);
    // rain
    float L = uSheet * 0.7 + uBoltI * 0.35;
    float rn = rain(uv, t, 260.0, 1.6, 0.18, 3) * 0.6 + rain(uv, t, 520.0, 2.2, 0.22, 9) * 0.4 + rain(uv, t, 130.0, 1.2, 0.15, 5) * 0.8;
    col += vec3(0.5, 0.62, 0.85) * rn * (0.020 + 0.30 * L);
    // thunder pressure bloom at the bottom
    col += vec3(0.25, 0.35, 0.6) * uThunder * 0.05 * exp(-(uv.y + 0.5) * 3.0);
    col *= uFadeIn;
    col += vec3(0.75, 0.85, 1.0) * uWhite;
    o = vec4(col, 1.0);
}
